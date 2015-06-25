import sqlite3
import variables

__author__ = 'Willem'

# This script creates an empty database that can be used in the project.

conn = sqlite3.connect(variables.database)
c = conn.cursor()

# Create al necessary tables
c.execute('''CREATE TABLE `tests` (
	`id`	INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
	`token`	TEXT NOT NULL UNIQUE,
	`finished`	INTEGER NOT NULL DEFAULT 0,
	`repository`	TEXT NOT NULL,
	`branch`	TEXT NOT NULL,
	`commit_hash`	TEXT NOT NULL
);''')
c.execute('''CREATE TABLE `queue` (
	`test_id`	INTEGER NOT NULL,
	PRIMARY KEY(test_id),
	FOREIGN KEY(`test_id`) REFERENCES tests(id)
);''')
c.execute('''CREATE TABLE `messages` (
	`id`	INTEGER NOT NULL,
	`test_id`	INTEGER NOT NULL,
	`time`	TEXT NOT NULL,
	`status`	TEXT NOT NULL,
	`message`	TEXT,
	PRIMARY KEY(id,test_id),
	FOREIGN KEY(`test_id`) REFERENCES test(id)
);''')

c.close()
conn.close()