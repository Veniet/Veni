#!/usr/bin/env python2

import datetime
import MySQLdb
import json
from flask import Flask
from flask import request, abort, make_response
from werkzeug.exceptions import HTTPException
from flask.json import jsonify
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
        if (("started" in self._config["logging"]  and self._config["logging"]["started"])  or  self._app.debug):
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


    def _checkUID(self):
        uid = self.params.get("userId", None)
        if not uid  or  (not isinstance(uid, int)  and  not uid.isdigit()):
            abort(400)
        cursor = self._db.cursor()
        cursor.execute("SELECT phoneNumber FROM User WHERE userId = %s", (uid, ))
        return uid if cursor.fetchone() else None


    def _checkAuth(self):
        # HACK FOR NOW.
        # TODO:  use JWTs?  https://realpython.com/token-based-authentication-with-flask/
        if self._request.method != "POST"  or  self._request.path != "/userInfo"  or  "userId" in self.params:
            self._uid = self._checkUID()
            if not self._uid:
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


    @apihandler
    def setUserInfo(self):
        queryParams = []
        if "userId" in self.params:
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
        else:
            # TODO:  handle attempt to insert duplicate phoneNumber
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
            resultMsg = "successfully registered new user"
        cursor = self._db.cursor()
        try:
            cursor.execute(sql, queryParams)
            self._db.commit()
        except Exception as e:
            self._db.rollback()
            raise
        if not self._uid:
            cursor = self._db.cursor()
            cursor.execute("SELECT userId FROM User WHERE phoneNumber = %s", (self.params["phoneNumber"], ))
            self._uid = cursor.fetchone()[0]
        return make_response(jsonify({ "message": resultMsg, "userId": self._uid }), 200)


    @apihandler
    def setStatus(self):
        free = self.params.get("free", False)
        if not free:
            abort(400)
        insertCursor = self._db.cursor()
        try:
            nowstr = datetime.datetime.now().strftime("%Y-%m-%d %H-%M-%S")
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
        timestr = (datetime.datetime.now() + datetime.timedelta(hours=-12)).strftime("%Y-%m-%d %H-%M-%S")
        friendCursor.execute(sql, (self._uid, self._uid, timestr))
        friends = []
        for friend in friendCursor.fetchall():
            friends.append(friend[0])
            self._pushNotification(friend[1], { "type" : "friendFree", "userId": self._uid })
        # TODO:  include thumbnail and phoneNumber if they changed
        return make_response(jsonify(friends), 200)


    def _friendCount(self):
        cursor = self._db.cursor()
        cursor.execute("SELECT COUNT(*) FROM Friend WHERE userId1 = %s OR userId2= %s", (self._uid, self._uid))
        return cursor.fetchone()[0]


    def _removeFriend(self, friendUid, friendDeviceToken):
        nowstr = datetime.datetime.now().strftime("%Y-%m-%d %H-%M-%S")
        cursor = self._db.cursor()
        try:
            self.cursor.execute("UPDATE Friend SET timeEnded = %s WHERE timeEnded IS NOT NULL AND ((userId1 = %s AND userId2 = %s) OR (userId1 = %s AND userId2 = %s))", (nowstr, self._uid, friendUid, friendUid, self._uid)) 
            self._db.commit()
            self._pushNotification(friendDeviceToken, { "type": "removeFriend", "userId": self._uid })
        except Exception as e:
            self._db.rollback()
            raise


    def _promoteFriendReq(self, friendUid):
        nowstr = datetime.datetime.now().strftime("%Y-%m-%d %H-%M-%S")
        try:
            cursor = self._db.cursor()
            cursor.execute("INSERT INTO Friend (userId1, userId2, timeStarted, timeEnded) VALUES(?, ?, ?, ?)", (friendUid, self._uid, nowstr, None))
            cursor.execute("DELETE FROM FriendRequest WHERE sourceUserId = %s AND targetUserId = %s", (friendUid, self._uid))
            self._db.commit()
        except Exception as e:
            self._db.rollback()
            raise


    def _addFriendReq(self, friendUid):
        nowstr = datetime.datetime.now().strftime("%Y-%m-%d %H-%M-%S")
        try:
            cursor = self._db.cursor()
            cursor.execute("INSERT INTO FriendRequest (sourceUserId1, targetUserId2, timestamp) VALUES(?, ?, ?)", (self._uid, friendUid, nowstr))
            self._db.commit()
        except Exception as e:
            self._db.rollback()
            raise
        return nowstr


    def _notifyFriendRequest(self, reqType, friendDeviceToken, requestedTimestamp):
        cursor = self._db.cursor()
        cursor.execute("SELECT phoneNumber, name, thumbnail FROM User WHERE userId = %s", self._uid)
        user = cursor.fetchone()
        assert(user)
        if reqType == "friendRequest":
            msg = self.params.get("message", "{} suggested you become Veni friends.".format(user[1]))
        else:
            msg = "{} accepted friend request.".format(user[1])
        friendPayload = {
            "type": reqType,
            "message": msg, 
            "userId": self_uid,
            "phoneNumber": user[0],
            "name": user[1],
            "thumbnail": user[2],
            "requestedTimestamp": requestedTimestamp
        }
        self._pushNotification(friendDeviceToken, friendPayload)


    # TODO:  auto-expiring friends requires push notification --> use a separate script
    @apihandler
    def addFriend(self):
        if self._friendCount() >= _g_maxFriends:
            abort(403)
        cursor = self._db.cursor()
        cursor.execute("SELECT userId, deviceNotificationToken, phoneNumber, name, thumbnail FROM User WHERE phoneNumber = %s", self.params["friendPhoneNumber"])
        friendUser = cursor.fetchone()
        if not friendUser:
            abort(404)
        if "remove" in self.params:
            _removeFriend(friendUser[0], friendUser[1])
            return make_response(jsonify({ "message": "successfully removed friend" }), 200)
        cursor = self._db.cursor()
        cursor.execute("SELECT timestamp FROM FriendRequest WHERE sourceUserId = %s AND targetUserId = %s", (friendUser[0], self._uid))
        friendReq = cursor.fetchone()
        if friendReq:
            self._promoteFriendReq(friendUser[0])
            self._notifyFriendReq("friendAccepted", friendUser[1], friendReq[0])
            return make_response(jsonify({ "friend": { "userId": friendUser[0], "phoneNumber": friendUser[2], "name": friendUser[3], "thumbnail": friendUser[4] } }), 200)
        else:
            requestedTimestamp = self._addFriendReq(friendUser[0])
            self._notifyFriendReq("friendRequest", friendUser[1], requestedTimestamp)
            return make_response(jsonify({ "message": "sent friend request" }), 202)


    @apihandler
    def contactFriend(self):
        sql = "INSERT INTO ContactLog (sourceUserId, targetUserId, timestamp) VALUES (%s, %s, %s)"
        cursor = self._db.cursor()
        try:
            nowstr = datetime.datetime.now().strftime("%Y-%m-%d %H-%M-%S")
            cursor.execute(sql, (self._uid, self.param["friendUserId"], nowstr))
            self._db.commit()
        except Exception as e:
            self._db.rollback()
            raise
        return make_reponse(jsonify({ "message": "contact attempt logged" }), 200)



############
## ROUTES ##
############

@app.route("/userInfo", methods=['POST'])
def userInfo():
    global app
    return APICall(app, request).setUserInfo()


@app.route("/status", methods=['POST'])
def status():
    global app
    requiredParams = [ "userId", "free" ]
    return APICall(app, request, requiredParams).setStatus()


@app.route("/friend", methods=['POST'])
def friend():
    global app
    requiredParams = [ "userId", "friendPhoneNumber" ]
    return APICall(app, request, requiredParams).addFriend()


@app.route("/contact", methods=['POST'])
def contact():
    global app
    requiredParams = [ "userId", "friendUserId" ]
    return APICall(app, request, requiredParams).contactFriend()



######################
## MAIN ENTRY POINT ##
######################

if __name__ == "__main__":
    app.run()

