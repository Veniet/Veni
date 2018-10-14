USE Veni;


DROP TABLE IF EXISTS User;
DROP TABLE IF EXISTS Friend;
DROP TABLE IF EXISTS FreeLog;
DROP TABLE IF EXISTS ContactLog;


CREATE TABLE User (
    userId INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    deviceNotificationToken VARCHAR(256) NOT NULL,
    phoneNumber VARCHAR(32) NOT NULL,
    name VARCHAR(256) NOT NULL,
    email VARCHAR(64) NOT NULL,       /* for research survey purposes */
    birthYear INT,
    gender VARCHAR(16),
    relationshipStatus VARCHAR(16),
    thumbnail BLOB,                   /* TAI: consider storing in filesystem instead. */
    UNIQUE INDEX index_User_phoneNumber (phoneNumber)
);


CREATE TABLE Friend (
    userId1 INT NOT NULL,
    userId2 INT NOT NULL,
    timeStarted DATETIME NOT NULL,
    timeEnded DATETIME,
    PRIMARY KEY (userId1, userId2, timeStarted),
    INDEX index_Friend_userId1 (userId1),
    INDEX index_Friend_userId2 (userId2),
    FOREIGN KEY (userId1) REFERENCES User(userId) ON UPDATE CASCADE,
    FOREIGN KEY (userId2) REFERENCES User(userId) ON UPDATE CASCADE
);


CREATE TABLE FreeLog (
    userId INT NOT NULL,
    timestamp DATETIME NOT NULL,
    PRIMARY KEY (userId, timestamp),
    FOREIGN KEY (userId) REFERENCES User(userId) ON UPDATE CASCADE
);


CREATE TABLE ContactLog (
    sourceUserId INT NOT NULL,
    targetUserId INT NOT NULL,
    timestamp DATETIME NOT NULL,
    PRIMARY KEY (sourceUserId, targetUserId, timestamp),
    INDEX index_ContactLog_sourceUserId (sourceUserId),
    INDEX index_ContactLog_targetUserId (targetuserId),
    FOREIGN KEY (sourceUserId) REFERENCES User(userId) ON UPDATE CASCADE,
    FOREIGN KEY (targetUserId) REFERENCES User(userId) ON UPDATE CASCADE
);

