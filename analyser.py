#Analyser of mySQL db info

import pandas as pd
import pymysql


#Set up connection to db
db = pymysql.connect(host="localhost", user="testUser", passwd="BorrisBulletDodger", db="allItems", charset='utf8')
cursor = db.cursor()

try:
    sql = "SELECT * FROM motorcycles"
    df = pd.read_sql(sql, db)
    print(df)
finally:
    db.close()

