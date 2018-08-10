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

if __name__=='__main__':
    print(describe('motorcycles'))
