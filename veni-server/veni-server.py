#!/usr/bin/env python2

import datetime
import MySQLdb
import json
from flask import Flask
from flask import request, abort
from flask.json import jsonify
import gcm
import apns
import logging
from logging import Formatter
from logging import FileHandler


app = Flask(__name__)


_g_configFile = "./veni.cfg"


class APICall:
    def __init__(self, app, request, handler, requiredParams = []):
        self._uid = None
        self._config = {}
        self.params = {}
        self._handler = handler
        self._app = app
        self._request = request
        self._readConfigFile()
        self._enableLogging()
        self._checkAuth()
        if not self._uid:
            abort(401)
        if not self._getRequestParams(requiredParams):
            abort(400)
        if not self._connectDB():
            abort(500)


    def __del__(self):
        self._closeDB()


    def handle(self):
        try:
            return self._handler(self)
        except Exception as e:
            self._app.logger.error("Caught exception in api handler:  {}".format(e))
            self_closeDB()
            abort(500)


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
        requestParams = request.form if (self._request.method == "POST") else request.args
        for param in requiredParams:
            if param not in requestParams:
                return False
        for param in requestParams:
            self.params[param] = requestParams[param]
        return True


    def _checkAuth(self):
        self._uid = TODO(self._request)
        # TODO:  use JWTs?  https://realpython.com/token-based-authentication-with-flask/


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



def _checkUID(params, db):
    uid = params.get("uid", None)
    if not uid  or  not uid.isdigit():
        abort(400)
        return None
    cursor = db.cursor()
    if cursor.execute("SELECT phoneNumber FROM User WHERE userId = %s", (uid, )).fetchone():
        return uid
    return None


def _pushNotification(deviceToken, payload):
    pass # TODO:  is it possible to tell from the token which type of notification


def _pushToAPNS(messageDict):
    pass  # TODO


def _pushToGCM(messageDict):
    pass # TODO



##############
## Handlers ##
##############

_g_userColumns = [ "deviceNotificationToken", "phoneNumber", "name", "email", "birthYear", "gender", "relationshipStatus", "thumbnail" ]

def _setUserInfo(apicall):
    global _g_userColumns
    queryParams = []
    if "uid" in apicall.params:
        uid = _checkUID(params, db)
        sql = "UPDATE User SET "
        for paramKey, paramVal in apicall.params.items():
            if paramKey in _g_userColumns:
                if queryParams:
                    sql += ", "
                sql += "{} = %s".format(paramKey)
                queryParams.append(paramVal)
        if not queryParams:
            abort(400)
        sql += " WHERE userId = %s"
        queryParams.append(uid)
    else:
        requiredColumns = [ "deviceNotificationToken", "phoneNum", "name", "email" ]  
        sql = "INSERT INTO User ({}) VALUES(%s{})".format(",".join(_g_userColumns), ", %s" * (len(_g_userColumns) - 1))
        for col in _g_userColumns:
            paramVal = Aapicall.params.get(col, None)
            if paramVal  and  col in requiredColumns:
                requiredColumns.remove(col)
            queryParams.append(paramVal)
        if len(requiredColumns) > 0:
            app.logger.error("adding new user missing required field(s): {}".format(requiredColumns))
            abort(400)
    cursor = apicall.db.cursor()
    try:
        cusor.execute(sql, queryParams)
        apicall.db.commit()
    except Exception as e:
        apicall.db.rollback()
        raise


def _setStatus(apicall):
    uid = _checkUID(apicall.params, apicall.db)
    free = apicall.params.get("free", False)
    if not free:
        abort(400)
    insertCursor = apicall.db.cursor()
    try:
        nowstr = datetime.datetime.now().strftime("%Y-%m-%d %H-%M-%S")
        insertCursor.execute("INSERT INTO FreeLog (userId, timestamp) VALUES(%s, %s)", (uid, nowstr))
        apicall.db.commit()
    except Exception as e:
        apicall.db.rollback()
        raise
    friendCursor = apicall.db.cursor() 
    sql = """SELECT FL.userId FROM FreeLog AS FL
             INNER JOIN Friend AS FF1 ON FL.userId = FF1.userId1 
             INNER JOIN Friend AS FF2 ON FL.userId = FF2.userId2 
             WHERE FF1.userId2 = %s AND FF2.userId1 = %s
             AND FL.timestamp > %s"""
    timestr = (datetime.datetime.now() + datetime.timedelta(hours=-12)).strftime("%Y-%m-%d %H-%M-%S")
    friendCursor.execute(sql, (uid, uid, timestr))
    friends = []
    for friend in friendCursor.fetchall():
        friends.append(friend[0])
    # TODO:  include thumbnail and phoneNumber if they changed
    return jsonify(friends)


_g_maxFriends = 20

# TODO:  auto-expiring friends requires push notification --> use a separate script
def _addFriend(apicall):
    global _g_maxFriends
    uid = _checkUID(apicall.params, apicall.db)
    cursor = apicall.db.cursor()
    cursor.execute("SELECT COUNT(*) FROM Friend WHERE userId1 = %s OR userId2= %s", (uid, uid))
    if cursor.fetchone()[0] >= _g_maxFriends:
        abort(403)
    cursor = apicall.db.cursor()
    cursor.execute("SELECT userId, deviceNotificationToken, phoneNumber, name, thumbnail FROM User WHERE phoneNumber = %s", apicall.params["friendPhoneNumber"])
    friendUser = cursor.fetchone()
    if not friendUser:
        abort(404)
    nowstr = datetime.datetime.now().strftime("%Y-%m-%d %H-%M-%S")
    if "remove" in apicall.params:
        try:
            cursor = apicall.db.cursor()
            cursor.execute("UPDATE Friend SET timeEnded = %s WHERE timeEnded IS NOT NULL AND ((userId1 = %s AND userId2 = %s) OR (userId1 = %s AND userId2 = %s))", (nowstr, uid, friendUser[0], friendUser[0], uid)) 
            apicall.db.commit()
        except Exception as e:
            apicall.db.rollback()
            raise
        return
    cursor = apicall.db.cursor()
    cursor.execute("SELECT timestamp FROM FriendRequest WHERE sourceUserId = %s AND targetUserId = %s", (friendUid, uid))
    friendReq = cursor.fetchone()
    if friendReq:
        try:
            cursor = apicall.db.cursor()
            cursor.execute("INSERT INTO Friend (userId1, userId2, timeStarted, timeEnded) VALUES(?, ?, ?, ?)", (friendUid, uid, nowstr, None))
            cursor.execute("DELETE FROM FriendRequest WHERE sourceUserId = %s AND targetUserId = %s", (friendUid, uid))
            apicall.db.commit()
            _pushNotification(friendUser[1], { "type": "removeFriend", "userId": uid })
        except Exception as e:
            apicall.db.rollback()
            raise
        friendPayload["type"] = "friendAccepted"
        friendPayload["message"] = "accepted friend request"
        friendPayload["userId"] = friendUser[0]
        friendPayload["phoneNumber"] = friendUser[2]
        friendPayload["name"] = friendUser[3]
        friendPayload["thumbnail"] = friendUser[4]
        friendPayload["requestTimestamp"] = friendReq[0]
        cursor = apicall.db.cursor()
        myDeviceToken = cursor.execute("SELECT deviceNotificationToken FROM User WHERE uid = %s", uid).fetchone()[0]
        _pushNotification(myDeviceToken, friendPayload)
    else:
        cursor = apicall.db.cursor()
        cursor.execute("SELECT phoneNumber, name, thumbnail FROM User WHERE userId = %s", uid)
        user = cursor.fetchone()
        assert(user)
        friendPayload["type"] = "friendRequest"
        friendPayload["message"] = apicall.params.get("message", "{} suggested you become Veni friends.".format(name))
        friendPayload["type"] = "friendAccepted"
        friendPayload["message"] = "accepted friend request"
        friendPayload["userId"] = uid
        friendPayload["phoneNumber"] = user[0]
        friendPayload["name"] = user[1]
        friendPayload["thumbnail"] = user[2]
        friendPayload["requestTimestamp"] = None
        _pushNotification(friendUser[1], friendPayload)
        try:
            cursor = apicall.db.cursor()
            cursor.execute("INSERT INTO FriendRequest (sourceUserId1, targetUserId2, timestamp) VALUES(?, ?, ?)", (uid, friendUid, nowstr))
            apicall.db.commit()
        except Exception as e:
            apicall.db.rollback()
            raise


def _contactFriend(apicall):
    uid = _checkUID(apicall.params, apicall.db)
    sql = "INSERT INTO ContactLog (sourceUserId, targetUserId, timestamp) VALUES (%s, %s, %s)"
    cursor = apicall.db.cursor()
    try:
        nowstr = datetime.datetime.now().strftime("%Y-%m-%d %H-%M-%S")
        cursor.execute(sql, (uid, apicall.param["friendUid"], nowstr))
        apicall.db.commit()
    except Exception as e:
        apicall.db.rollback()
        raise



############
## ROUTES ##
############

@app.route("/userInfo", methods=['POST'])
def userInfo():
    global app
    requiredParams = [ ] 
    handler = _setUserInfo
    APICall(app, request, handler, requiredParams).handle()


@app.route("/status", methods=['POST'])
def status():
    global app
    requiredParams = [ "uid", "free" ]
    APICall(app, request, _setStatus, requiredParams).handle()


@app.route("/friend", methods=['POST'])
def friend():
    global app
    requiredParams = [ "uid", "friendPhoneNumber" ]
    APICall(app, request, _addFriend, requiredParams).handle()


@app.route("/contact", methods=['POST'])
def contact():
    global app
    requiredParams = [ "uid", "friendUid" ]
    APICall(app, request, _contactFriend, requiredParams).handle()



######################
## MAIN ENTRY POINT ##
######################

if __name__ == "__main__":
    app.run()

