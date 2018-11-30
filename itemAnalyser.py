import pymysql
import pandas as pd
import numpy as np 
import matplotlib.pyplot as plt

#SQL String
sql = "SELECT * FROM motorcycles"

#Open db connection
db = pymysql.connect(host="localhost", user="testUser", passwd=password, db="allItems")

#Pull db data
df = pd.read_sql(sql, db)

#Close db
db.close()

print(df)

#def analyse(data):