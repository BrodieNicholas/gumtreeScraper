import pymysql


IPList = [
    "130.102.12.140"
]


#SQL String
sql = "SELECT * FROM motorcycles"

#Open db connection
db = pymysql.connect(host="localhost", user="testUser", passwd=password, db="allItems")
cursor = db.cursor()

data = cursor.execute(sql)

for i in data:
    

def urlCheck(urls):
    """ 
    Checks whether the url has already been found
    input: list of urls
    output: list of urls (with already logged urls removed)
    """
    #Open db connection
    db = pymysql.connect(host="localhost", user="testUser", passwd=password, db="allItems")
    cursor = db.cursor()
    
    #SQL String
    sql = "SELECT url FROM motorcycles"
    
    #Pull data
    try:
        data = cursor.execute(sql)
    except Exception as e:
        print("Error occurred: {}".format(e))
        db.rollback()
    
    #Process 
    newUrlList = [i for i in urls if i not in data]

    #Close db
    db.Close()

    return newUrlList



#Close db