#Analyser of mySQL db info

import pandas as pd
import pymysql
import matplotlib.pyplot as plt
#import seaborn as sns

#Set up connection to db
db = pymysql.connect(host="localhost", user="testUser", passwd="BorrisBulletDodger", db="allItems", charset='utf8')
cursor = db.cursor()

try:
    sql = "SELECT * FROM motorcycles WHERE adExpiry IS NOT NULL AND displacement = 300"
    df = pd.read_sql(sql, db)
    print(df)
finally:
    db.close()

df.plot('kms', 'price', 'scatter', ylim=(0,25000), xlim=(0,100000))
#sns.lmplot(x='kms', y='price', data=df, fit_reg=True)
plt.show()