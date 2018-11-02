#!/usr/bin/env python2

import datetime
import MySQLdb
import MySQLdb.cursors
import json
from flask import Flask
from flask import request, abort, make_response
from werkzeug.exceptions import HTTPException
from flask.json import jsonify
import jwt
from pyfcm import FCMNotification
import logging
from logging import Formatter
from logging import FileHandler
from functools import wraps


app = Flask(__name__)


_g_configFile = "./veni.cfg"


class APICall:
    def __init__(self, app, request, requiredParams = []):
        self._uid = None
        self._config = {}
        self.params = {}
        self._app = app
        self._request = request
        self._readConfigFile()
        self._enableLogging()
        self._pushService = FCMNotification(api_key="AAAAJcqwb2M:APA91bFixpCKO1fE6kObLma1upi1RBPWHNMufAFhz2CzycG2oqfELoh7vLZ8ceGCpYxiDuClCnsD9eJp1BgMkl2FI97996JC4vAqZMuO_HF7VHBEYFIPUuhvlRQ2KuKlMsrSYwgdjZ1Y")
        self._userColumns = [ "deviceNotificationToken", "phoneNumber", "name", "email", "birthYear", "gender", "relationshipStatus", "thumbnail" ]
        self._maxFriends = 20
        if not self._getRequestParams(requiredParams):
            abort(400)
        if not self._connectDB():
            abort(500)
        self._checkAuth()


    def __del__(self):
        self._closeDB()


    def _readConfigFile(self):
        global _g_configFile
        try:
            with open(_g_configFile) as inpf:
                self._config = json.load(inpf)
        except Exception as e:
            self._app.logger.error("Caught exception reading the config file '{}':  {}".format(_g_configFile, e))
            abort(500)
        if ("logging" not in self._config  or  "database" not in self._config):
            self._app.logger.error("Config file '{}' missing required section.".format(_g_configFile))
            abort(500)


    def _enableLogging(self):
        if (("started" in self._config["logging"]  and  self._config["logging"]["started"])  or  self._app.debug):
            return
        handler = FileHandler(self._config["logging"]["logfile"])
        handler.setFormatter(Formatter('%(asctime)s %(levelname)s line=%(lineno)d - %(message)s'))
        handler.setLevel(self._config["logging"]["level"])
        self._app.logger.addHandler(handler)
        self._config["logging"]["started"] = True


    def _getRequestParams(self, requiredParams):
        requestParams = self._request.values if len(self._request.values) > 0 else self._request.get_json()
        for param in requiredParams:
            if param not in requestParams:
                return False
        for param in requestParams:
            self.params[param] = requestParams[param]
        return True


    def _encodeAuthToken(self):
        assert(self._uid)
        payload = {
            'iat': datetime.datetime.utcnow(),
            'exp': datetime.datetime.utcnow() + datetime.timedelta(days=self._config.get("auth-token-expiration-days", 365.25)),
            'sub': self._uid
        }
        return jwt.encode(payload, self._config['token-key'], algorithm='HS256')


    def _decodeAuthToken(self):
        authHeader = self._request.headers.get('Authorization')
        if not authHeader:
            abort(403)
        try:
            return jwt.decode(authHeader.split()[1], self._config['token-key'])['sub']
        except jwt.ExpiredSignatureError:
            abort(401)    # TODO:  response should use WWW-Authenticate header field
        except jwt.InvalidTokenError:
            abort(403)
        

    def _checkAuth(self):
        if "Authorization" not in self._request.headers:
            if self._request.path != "/userInfo":
                abort(401)
            # TAI:  check app key here?
            return
        self._uid = self._decodeAuthToken()
        if not self._uid  or  not (isinstance(self._uid, int)  or  self._uid.isdigit()):
            abort(401)


    def _connectDB(self):
        if "optionalSocket" in self._config["database"]:
            self._db = MySQLdb.connect(self._config["database"]["server"], \
                                       self._config["database"]["user"], \
                                       self._config["database"]["password"], \
                                       self._config["database"]["name"], \
                                       unix_socket=self._config["database"]["optionalSocket"])
        else:
            self._db = MySQLdb.connect(self._config["database"]["server"], \
                                       self._config["database"]["user"], \
                                       self._config["database"]["password"], \
                                       self._config["database"]["name"])
        return self._db is not None


    def _closeDB(self):
        if self._db:
            self._db.close()
            self._db = None


    def _pushNotification(self, deviceToken, payload):
        return self._pushService.single_device_data_message(registration_id=deviceToken, data_message=payload)


    def apihandler(fn):
        @wraps(fn)
        def decorated(*args, **kwargs):
            try:
                return fn(*args, **kwargs)
            except HTTPException as he:
                raise
            except Exception as e:
                args[0]._app.logger.error("Caught unexpected exception in api handler:  {}".format(e))
                abort(500)
            finally:
                args[0]._closeDB()
        return decorated


    def _uidFromPhoneNum(self, phoneNum):
        cursor = self._db.cursor()
        cursor.execute("SELECT userId FROM User WHERE phoneNumber = %s", (phoneNum,))
        ur = cursor.fetchone()
        return ur[0] if ur else None


    @apihandler
    def getUserInfo(self):
        cursor = self._db.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT phoneNumber, name, email, birthYear, gender, relationshipStatus, thumbnail FROM User WHERE userId = %s", (self._uid,))
        user = cursor.fetchone()
        if not user:
            abort(500)
        return make_response(jsonify(user), 200)


    @apihandler
    def setUserInfo(self):
        queryParams = []
        if self._uid:
            sql = "UPDATE User SET "
            for paramKey, paramVal in self.params.items():
                if paramKey in self._userColumns:
                    if queryParams:
                        sql += ", "
                    sql += "{} = %s".format(paramKey)
                    queryParams.append(paramVal)
            if not queryParams:
                abort(400)
            sql += " WHERE userId = %s"
            queryParams.append(self._uid)
            resultMsg = "successfully updated user info"
            self._app.logger.info("updating user {} with: {}".format(self._uid, queryParams))
            # TODO:  notify friends if thumbnail and/or phoneNumber changed
        else:
            requiredColumns = [ "deviceNotificationToken", "phoneNumber", "name", "email" ]  
            sql = "INSERT INTO User ({}) VALUES(%s{})".format(",".join(self._userColumns), ", %s" * (len(self._userColumns) - 1))
            for col in self._userColumns:
                paramVal = self.params.get(col, None)
                if paramVal  and  col in requiredColumns:
                    requiredColumns.remove(col)
                queryParams.append(paramVal)
            if len(requiredColumns) > 0:
                self._app.logger.error("adding new user missing required field(s): {}".format(requiredColumns))
                abort(400)
            if self._uidFromPhoneNum(self.params["phoneNumber"]):
                self._app.logger.warning("tried to add duplicate phoneNumber: {}".format(self.params["phoneNumber"]))
                return make_response(jsonify({ "message": "duplicate" }), 403)
            resultMsg = "successfully registered new user"
            self._app.logger.info("adding new user with: {}".format(queryParams))
        cursor = self._db.cursor()
        try:
            cursor.execute(sql, queryParams)
            self._db.commit()
        except Exception as e:
            self._db.rollback()
            raise
        if self._uid:
            return make_response(jsonify({ "message": resultMsg, "userId": self._uid }), 200)
        self._uid = self._uidFromPhoneNum(self.params["phoneNumber"])
        authToken = self._encodeAuthToken()
        return make_response(jsonify({ "message": resultMsg, "userId": self._uid, "authToken": authToken.decode() }), 200)


    @apihandler
    def setStatus(self):
        free = self.params.get("free", False)
        if not free:
            abort(400)
        self._app.logger.info("user {} set free status".format(self._uid))
        insertCursor = self._db.cursor()
        try:
            nowstr = datetime.datetime.utcnow().strftime("%Y-%m-%d %H-%M-%S")
            insertCursor.execute("INSERT INTO FreeLog (userId, timestamp) VALUES(%s, %s)", (self._uid, nowstr))
            self._db.commit()
        except Exception as e:
            self._db.rollback()
            raise
        friendCursor = self._db.cursor() 
        sql = """SELECT FL.userId, U.deviceNotificationToken 
                 FROM FreeLog AS FL
                 INNER JOIN User AS U ON FL.userId = U.userId 
                 INNER JOIN Friend AS FF1 ON FL.userId = FF1.userId1 
                 INNER JOIN Friend AS FF2 ON FL.userId = FF2.userId2 
                 WHERE FF1.userId2 = %s AND FF2.userId1 = %s
                 AND FL.timestamp > %s"""
        timestr = (datetime.datetime.utcnow() + datetime.timedelta(hours=-12)).strftime("%Y-%m-%d %H-%M-%S")
        friendCursor.execute(sql, (self._uid, self._uid, timestr))
        friends = []
        for friend in friendCursor.fetchall():
            friends.append(friend[0])
            self._pushNotification(friend[1], { "type" : "friendFree", "userId": self._uid })
        return make_response(jsonify(friends), 200)


    def _friendCount(self):
        cursor = self._db.cursor()
        cursor.execute("SELECT COUNT(*) FROM Friend WHERE userId1 = %s OR userId2= %s", (self._uid, self._uid))
        return cursor.fetchone()[0]


    def _removeFriend(self, friendUid, friendDeviceToken):
        nowstr = datetime.datetime.utcnow().strftime("%Y-%m-%d %H-%M-%S")
        cursor = self._db.cursor()
        try:
            cursor.execute("UPDATE Friend SET timeEnded = %s WHERE timeEnded IS NULL AND ((userId1 = %s AND userId2 = %s) OR (userId1 = %s AND userId2 = %s))", (nowstr, self._uid, friendUid, friendUid, self._uid)) 
            self._db.commit()
            self._pushNotification(friendDeviceToken, { "type": "removeFriend", "userId": self._uid })
        except Exception as e:
            self._db.rollback()
            raise


    def _promoteFriendReq(self, friendUid):
        nowstr = datetime.datetime.utcnow().strftime("%Y-%m-%d %H-%M-%S")
        try:
            cursor = self._db.cursor()
            cursor.execute("INSERT INTO Friend (userId1, userId2, timeStarted, timeEnded) VALUES(%s, %s, %s, %s)", (friendUid, self._uid, nowstr, None))
            cursor.execute("DELETE FROM FriendRequest WHERE sourceUserId = %s AND targetUserId = %s", (friendUid, self._uid))
            self._db.commit()
        except Exception as e:
            self._db.rollback()
            raise


    def _addFriendReq(self, friendUid):
        cursor = self._db.cursor()
        cursor.execute("SELECT * FROM FriendRequest WHERE sourceUserId = %s AND targetUserId = %s", (self._uid, friendUid))
        existingFriendReq = cursor.fetchone()
        nowstr = datetime.datetime.utcnow().strftime("%Y-%m-%d %H-%M-%S")
        if existingFriendReq:
            sql = "UPDATE FriendRequest SET timestamp = %s WHERE sourceUserId = %s AND targetUserId = %s"
            queryParams = (nowstr, self._uid, friendUid)
        else:
            sql = "INSERT INTO FriendRequest (sourceUserId, targetUserId, timestamp) VALUES(%s, %s, %s)"
            queryParams = (self._uid, friendUid, nowstr)
        cursor = self._db.cursor()
        try:
            cursor.execute(sql, queryParams)
            self._db.commit()
        except Exception as e:
            self._db.rollback()
            raise
        return (nowstr, existingFriendReq is None)


    def _notifyFriendRequest(self, reqType, friendDeviceToken, requestedTimestamp, repeat = False):
        cursor = self._db.cursor()
        cursor.execute("SELECT phoneNumber, name, thumbnail FROM User WHERE userId = %s", (self._uid,))
        user = cursor.fetchone()
        assert(user)
        if reqType == "friendRequest":
            msg = self.params.get("message", "{} suggested you become Veni friends.".format(user[1]))
        else:
            msg = "{} accepted friend request.".format(user[1])
        friendPayload = {
            "type": reqType,
            "message": msg, 
            "userId": self._uid,
            "phoneNumber": user[0],
            "name": user[1],
            "thumbnail": user[2]
        }
        if requestedTimestamp  and  isinstance(requestedTimestamp, datetime.datetime):
            friendPayload["requestedTimestamp"] = requestedTimestamp.strftime("%Y-%m-%d %H-%M-S")
        else:
            friendPayload["requestedTimestamp"] = requestedTimestamp
        if repeat:
            friendPayload["repeat"] = True
        self._pushNotification(friendDeviceToken, friendPayload)


    # TODO:  auto-expiring friends requires push notification --> use a separate script
    @apihandler
    def addFriend(self):
        if self._friendCount() >= self._maxFriends:
            self._app.logger.info("user {} tried to add too many friends".format(self._uid))
            abort(403)
        cursor = self._db.cursor()
        cursor.execute("SELECT userId, deviceNotificationToken, phoneNumber, name, thumbnail FROM User WHERE phoneNumber = %s", (self.params["friendPhoneNumber"],))
        friendUser = cursor.fetchone()
        if not friendUser:
            self._app.logger.warning("user {} tried to add friend with unknown phoneNumber={}".format(self._uid, self.params["friendPhoneNumber"]))
            abort(404)
        if "remove" in self.params:
            self._app.logger.info("user {} removing friend {}".format(self._uid, friendUser[0]))
            self._removeFriend(friendUser[0], friendUser[1])
            return make_response(jsonify({ "message": "successfully removed friend" }), 200)
        cursor = self._db.cursor()
        cursor.execute("SELECT timestamp FROM FriendRequest WHERE sourceUserId = %s AND targetUserId = %s", (friendUser[0], self._uid))
        friendReq = cursor.fetchone()
        if friendReq:
            self._app.logger.info("user {} accepted friend request from {}".format(self._uid, friendUser[0]))
            self._promoteFriendReq(friendUser[0])
            self._notifyFriendRequest("friendAccepted", friendUser[1], friendReq[0])
            return make_response(jsonify({ "friend": { "userId": friendUser[0], "phoneNumber": friendUser[2], "name": friendUser[3], "thumbnail": friendUser[4] } }), 200)
        else:
            self._app.logger.info("user {} friend request to {}".format(self._uid, friendUser[0]))
            requestedTimestamp, newReq = self._addFriendReq(friendUser[0])
            self._notifyFriendRequest("friendRequest", friendUser[1], requestedTimestamp, not newReq)
            return make_response(jsonify({ "message": "sent friend request" }), 202)


    @apihandler
    def contactFriend(self):
        self._app.logger.info("user {} contacting {}".format(self._uid, self.params["friendUserId"]))
        sql = "INSERT INTO ContactLog (sourceUserId, targetUserId, timestamp) VALUES (%s, %s, %s)"
        cursor = self._db.cursor()
        try:
            nowstr = datetime.datetime.utcnow().strftime("%Y-%m-%d %H-%M-%S")
            cursor.execute(sql, (self._uid, self.params["friendUserId"], nowstr))
            self._db.commit()
        except Exception as e:
            self._db.rollback()
            raise
        return make_response(jsonify({ "message": "contact attempt logged" }), 200)



############
## ROUTES ##
############

@app.route("/userInfo", methods=['POST', 'GET'])
def userInfo():
    global app
    if request.method == 'GET':
        return APICall(app, request).getUserInfo()
    else:
        return APICall(app, request).setUserInfo()


@app.route("/status", methods=['POST'])
def status():
    global app
    requiredParams = [ "free" ]
    return APICall(app, request, requiredParams).setStatus()


@app.route("/friend", methods=['POST'])
def friend():
    global app
    requiredParams = [ "friendPhoneNumber" ]
    return APICall(app, request, requiredParams).addFriend()


@app.route("/contact", methods=['POST'])
def contact():
    global app
    requiredParams = [ "friendUserId" ]
    return APICall(app, request, requiredParams).contactFriend()


@app.route("/ping", methods=['GET'])
def ping():
    global app
    # Note:  no auth required for this.
    return make_response(jsonify({ "message": "pong" }), 200)



######################
## MAIN ENTRY POINT ##
######################

if __name__ == "__main__":
    app.run()

