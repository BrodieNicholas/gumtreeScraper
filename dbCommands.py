import pymysql


def describe(table):
    #Create connection 
    db = pymysql.connect(host="localhost", user="testUser", passwd="BorrisBulletDodger", db="allItems", charset='utf8')
    cursor = db.cursor()

    #SQL Query
    sql = "DESCRIBE " + table + ";"

    #Find data
    try: 
        cursor.execute(sql)
        data = cursor.fetchall()
        db.commit()
    except Exception as e:
        db.rollback()
        print("Exception occured: {}".format(e))
    finally:
        db.close()
    data = [i[0] for i in data]
    return data

    
def createTable():
    """ Creates a predefined mySQL Table for motorbikes"""
    #Create connection
    db = pymysql.connect(host="localhost", user="testUser", passwd="BorrisBulletDodger", db="allItems", charset='utf8')
    cursor = db.cursor()

    try:
        sql = "CREATE TABLE IF NOT EXISTS motorcycles(" \
            +"url VARCHAR(255) NOT NULL PRIMARY KEY, " \
            +"make VARCHAR(150) DEFAULT NULL, "\
            +"model VARCHAR(150) DEFAULT NULL, "\
            +"name VARCHAR(150) DEFAULT NULL, "\
            +"price FLOAT DEFAULT NULL, "\
            +"kms DOUBLE DEFAULT NULL, "\
            +"location VARCHAR(150) DEFAULT NULL, "\
            +"listDate DATE DEFAULT NULL, "\
            +"year YEAR(4) DEFAULT NULL, "\
            +"displacement VARCHAR(15) DEFAULT NULL, "\
            +"registered CHAR(1) DEFAULT NULL, "\
            +"regExpiry DATE DEFAULT NULL, "\
            +"colour VARCHAR(30) DEFAULT NULL, "\
            +"description TEXT DEFAULT NULL, "\
            +"learner CHAR(1) DEFAULT NULL, "\
            +"listType VARCHAR(40) DEFAULT NULL, "\
            +"adExpiry DATE DEFAULT NULL)"
        
        # Create table
        cursor.execute(sql)
        db.commit()

    except Exception as e:
        db.rollback()
        print("Exception occured: {}".format(e))


    # Close database
    db.close()

if __name__=='__main__':
    print(describe('motorcycles'))
