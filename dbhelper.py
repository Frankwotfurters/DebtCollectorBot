import sqlite3

class DBHelper:
    def __init__(self, dbname="debt.sqlite"):
        self.dbname = dbname
        self.conn = sqlite3.connect(dbname, check_same_thread=False)

    def setup(self):
        print("Creating Tables")
        
        stmt = "CREATE TABLE IF NOT EXISTS records (`id` INTEGER PRIMARY KEY, `owner` INT NOT NULL, `amount` INT UNSIGNED NOT NULL, `friend` VARCHAR(45) NOT NULL, `desc` VARCHAR(45) NULL, CONSTRAINT `userID` FOREIGN KEY (`owner`) REFERENCES `pref` (`userID`) ON DELETE NO ACTION ON UPDATE CASCADE)"
        self.conn.execute(stmt)
        
        stmt = "CREATE TABLE IF NOT EXISTS friends (`userID` INT NOT NULL, `friend` VARCHAR(45) NOT NULL, PRIMARY KEY (`userID`), CONSTRAINT `userID` FOREIGN KEY (`userID`) REFERENCES `pref` (`userID`) ON DELETE NO ACTION ON UPDATE CASCADE)"
        self.conn.execute(stmt)
        
        stmt = "CREATE TABLE IF NOT EXISTS pref (`userID` INT NOT NULL, `default` VARCHAR(45) NULL, `number` INT NULL, PRIMARY KEY (`userID`))"
        self.conn.execute(stmt)
        
        self.conn.commit()

    def add_record(self, owner, amount, friend=None, desc=""):
        """Add new record to database"""
        if not friend:
            # get default
            pass
        
        # Prepare statement
        stmt = "INSERT INTO records (owner, amount, friend, desc) VALUES (?, ?, ?, ?)"
        args = (owner, amount, friend, desc,)

        # Execute statement
        self.conn.execute(stmt, args)

        # Commit to database
        self.conn.commit()

    def delete_record(self, item_text, owner):
        # Prepare statement
        stmt = "DELETE FROM items WHERE description = (?) AND owner = (?)"
        args = (item_text, owner )

        # Execute statement
        self.conn.execute(stmt, args)

        # Commit to database
        self.conn.commit()

    def check_records(self, owner, friend):
        """Returns records belonging to the user"""
        # Prepare statement
        stmt = "SELECT amount, desc FROM records WHERE owner = (?) AND friend = (?)"
        args = (owner, friend,)

        return [x for x in self.conn.execute(stmt, args)]

    def check_friends(self, owner):
        """Returns all previously tabulated friends"""
        stmt = "SELECT friend FROM records WHERE owner = (?)"
        args = (owner,)
        return list(set([x[0] for x in self.conn.execute(stmt, args)]))