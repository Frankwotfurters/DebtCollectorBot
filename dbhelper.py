import sqlite3

class DBHelper:
    def __init__(self, dbname="debt.sqlite"):
        self.dbname = dbname
        self.conn = sqlite3.connect(dbname, check_same_thread=False)

    def setup(self):
        print("Creating Tables")
        
        stmt = "CREATE TABLE IF NOT EXISTS records (`id` INTEGER PRIMARY KEY AUTOINCREMENT, `owner` INT NOT NULL, `amount` FLOAT UNSIGNED NOT NULL, `friend` VARCHAR(45) NOT NULL, `desc` VARCHAR(45) NULL, CONSTRAINT `userID` FOREIGN KEY (`owner`) REFERENCES `pref` (`userID`) ON DELETE NO ACTION ON UPDATE CASCADE)"
        self.conn.execute(stmt)
        
        # stmt = "CREATE TABLE IF NOT EXISTS friends (`userID` INT NOT NULL, `friend` VARCHAR(45) NOT NULL, PRIMARY KEY (`userID`), CONSTRAINT `userID` FOREIGN KEY (`userID`) REFERENCES `pref` (`userID`) ON DELETE NO ACTION ON UPDATE CASCADE)"
        # self.conn.execute(stmt)
        
        stmt = "CREATE TABLE IF NOT EXISTS pref (`userID` INT NOT NULL, `defaultFriend` VARCHAR(45) NULL, PRIMARY KEY (`userID`))"
        self.conn.execute(stmt)
        
        self.conn.commit()

    def add_record(self, owner, friend, amount, desc=""):
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

    def clear_record(self, owner, friend):
        """Clear all records between the user and a specific friend"""
        # Prepare statement
        stmt = "DELETE FROM records WHERE owner = (?) AND friend = (?)"
        args = (owner, friend)

        # Execute statement
        self.conn.execute(stmt, args)

        # Commit to database
        self.conn.commit()

    def delete_record(self, owner, id):
        """Delete a single record by owner and ID"""
        # Prepare statement
        stmt = "DELETE FROM records WHERE owner = (?) AND id = (?)"
        args = (owner, id)

        # Execute statement
        res = self.conn.execute(stmt, args)

        # Commit to database
        self.conn.commit()

        return [x for x in res]

    def check_recent(self, owner):
        """Returns all records of user in reverse order"""
        # Prepare statement
        stmt = "SELECT id, owner, amount, friend, desc FROM records WHERE owner = (?)"
        args = (owner,)

        return reversed([x for x in self.conn.execute(stmt, args)])

    def check_records(self, owner, friend):
        """Returns records between the user and a friend"""
        # Prepare statement
        stmt = "SELECT amount, desc FROM records WHERE owner = (?) AND friend like (?)"
        args = (owner, friend,)

        return [x for x in self.conn.execute(stmt, args)]

    def get_record_by_ID(self, owner, id):
        """Returns single record by owner and ID"""
        # Prepare statement
        stmt = "SELECT id, owner, amount, friend, desc FROM records WHERE owner = (?) AND id = (?)"
        args = (owner, id)

        return [x for x in self.conn.execute(stmt, args)]

    def check_friends(self, owner):
        """Returns a list of all (unique) previously tabulated friends"""
        stmt = "SELECT friend FROM records WHERE owner = (?)"
        args = (owner,)
        
        # Create a set to keep track of seen names and result list to return
        seen, result = set(), []
        
        # For every entry,
        for friend in self.conn.execute(stmt, args):
            # If new unique name
            if friend[0].lower() not in seen:
                # Add to seen set and append to results
                seen.add(friend[0].lower())
                result.append(friend[0])
                
        # Returns only unique names regardless of capitalization
        return result
    
    def check_default(self, owner):
        """Returns the default friend defined by the user"""
        # Prepare statement
        stmt = "SELECT defaultFriend FROM pref WHERE userID = (?)"
        args = (owner,)
        return [x for x in self.conn.execute(stmt, args)]
    
    def set_default(self, owner, friend):
        """Sets default friend of user"""
        # Prepare statement
        stmt = "INSERT OR REPLACE INTO `pref` (userID, defaultFriend) VALUES (?, ?)"
        args = (owner, friend)

        # Execute statement
        self.conn.execute(stmt, args)

        # Commit to database
        self.conn.commit()

    def delete_default(self, owner):
        """Deletes default friend of user"""
        # Prepare statement
        stmt = "DELETE FROM `pref` WHERE userID = (?)"
        args = (owner,)

        # Execute statement
        self.conn.execute(stmt, args)

        # Commit to database
        self.conn.commit()
    
    def test(self):
        stmt = "INSERT INTO pref (userID, defaultFriend) VALUES (?, ?)"
        args = ('1264592652', 'bruh')
        print([x for x in self.conn.execute(stmt, args)])
        self.conn.commit()
        
    
# db = DBHelper()
# db.setup()
# print(db.set_default('1264592652', 'asd'))