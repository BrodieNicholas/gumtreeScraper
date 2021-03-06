from bs4 import BeautifulSoup
from datetime import datetime
import requests
from requests.packages.urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
import re
import pymysql
from tqdm import tqdm
from warnings import filterwarnings
tqdm.monitor_interval = 0
filterwarnings('ignore', category = pymysql.Warning)

#Set Retries within Requests
s = requests.Session()
retries = Retry(total=5, backoff_factor=0.1, status_forcelist=[ 500, 502, 503, 504])
s.mount('http://', HTTPAdapter(max_retries=retries))


class Item:
    def __init__(self, url):
        #URL split on "/" gives ['', 's-ad', location, category, name, randomNumber]
        self.time = datetime.now().time()
        self.url = url
        self.location = url.split("/")[4]
        self.category = url.split("/")[5]
        self.name = url.split("/")[6]
        #######################################Fix This(url changed, extra /'s)##########################

    def timeSinceQuery(self):
        """ Find time between object creation and now"""
        return self.time - datetime.now().time()

    def scrape(self):
        
        """ Scrape the items URL for price and date listed
        Returns itemPrice, itemListDate
        """
        page = s.get("https://www.gumtree.com.au"+self.url)
        print("https://www.gumtree.com.au"+self.url)

        if page.status_code != 200:
            print(page.status_code)
        soup = BeautifulSoup(page.content, 'html.parser')


        price = soup.find_all(class_="user-ad-price__price")[0].contents[0]

        adAttrVals = soup.find_all(class_="vip-ad-attributes__value")
        adAttrName = soup.find_all(class_="vip-ad-attributes__name")
        
        for i in range(0,len(adAttrName)):
            if adAttrVals[i].contents[0] == "Date Listed":
                listDate = adAttrName[i].contents[0]
        
        return price, listDate

class Motorcycle(Item):
    def __init__(self, url):
        super().__init__(url)
        #self.price, self.listDate, self.displacement, self.make, self.model, \
        #    self.year, self.kms, self.registered, self.regExpiry, self.colour, \
        #    self.description, self.learner, self.listType = 
        
        self.price = "NULL"
        self.listDate = "NULL"
        self.displacement = "NULL"
        self.make = "NULL"
        self.model = "NULL"
        self.year = "NULL"
        self.kms = "NULL"
        self.registered = "NULL"
        self.regExpiry = "NULL"
        self.colour = "NULL"
        self.description = "NULL"
        self.learner = "NULL"
        self.listType = "NULL"
        self.scrape()
    


    def scrape(self):
        """Pull Information about the motorcycle"""
        #Request the page from the internet
        page = s.get(self.url)

        #Check if page is working
        if page.status_code != 200:
            print(page.status_code)
        #Load page contents into soup
        soup = BeautifulSoup(page.content, 'html.parser')

        
        #Find price
        try:
            self.price = soup.find_all(class_="j-ad-price")[0]['content']
        except:
            self.price = "NULL"
        #Find attributes names/values
        adAttrName = soup.find_all(class_="ad-details__ad-attribute-name")
        adAttrVals = soup.find_all(class_="ad-details__ad-attribute-value")
        #Find description
        try:
            self.description = ""
            descriptionLst = soup.find_all(id="ad_description_details_content")[0].contents
            for i in range(len(descriptionLst)):
                if isinstance(descriptionLst[i], str):
                    self.description = self.description + descriptionLst[i].lstrip() + " "
        except:
            self.description = "NULL"

        #Set defaults 
        #----------------------------------------------------------------------
        listDate = "NULL"
        displacement = "NULL"
        make = "NULL"
        model = "NULL"
        year = "NULL"
        kms = "NULL"
        registered = "NULL"
        regExpiry = "NULL"
        colour = "NULL"
        learner = "NULL"
        listType = "NULL"
        #----------------------------------------------------------------------
        
        #Check all attributes for important information
        for i in range(0,len(adAttrName)):
            tempName = adAttrName[i].contents[0]
            if "Date Listed:" in tempName:
                listDateLst = adAttrVals[i].contents[0].lstrip().split('/')
                self.listDate = listDateLst[2]+'-'+listDateLst[1]+'-'+listDateLst[0]
            elif "Displacement (cc):" in tempName:
                self.displacement = adAttrVals[i].contents[0].lstrip()
            elif "Make:" in tempName:
                self.make = adAttrVals[i].contents[0].lstrip()
            elif "Model:" in tempName:
                self.model = adAttrVals[i].contents[0].lstrip()
            elif "Year:" in tempName:
                self.year = adAttrVals[i].contents[0].lstrip()
            elif "KMs:" in tempName:
                self.kms = adAttrVals[i].contents[0].lstrip()
            elif "Registered:" in tempName:
                if adAttrVals[i].contents[0].lstrip() == "Yes":
                    self.registered = "Y"
                elif  adAttrVals[i].contents[0].lstrip() == "No":
                    self.registered = "N"
            elif "Registration Expiry:" in tempName:
                regExpLst = adAttrVals[i].contents[0].lstrip().split('/')
                self.regExpiry = regExpLst[2]+'-'+regExpLst[1]+'-'+regExpLst[0]
            elif "Colour:" in tempName:
                self.colour = adAttrVals[i].contents[0].lstrip()
            elif "Learner Approved:" in tempName:
                if adAttrVals[i].contents[0].lstrip() == "Yes":
                    self.learner = "Y"
                elif  adAttrVals[i].contents[0].lstrip() == "No":
                    self.learner = "N"
            elif "Listing Type:" in tempName:
                self.listType = adAttrVals[i].contents[0].lstrip()


        #return price, listDate, displacement, make, model, year, kms, registered, regExpiry, colour, description, learner, listType

    def dbInsert(self, password):
        db = pymysql.connect(host="localhost", user="testUser", passwd=password, db="allItems", charset='utf8')
        cursor = db.cursor()
	
        #SQL Query
        sql = "INSERT IGNORE INTO motorcycles VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NULL);"

        #Convert strings into floats
        if self.price == "":
            self.price = "NULL"
        if self.kms == "":
            self.kms = "NULL"
        if self.price != "NULL":
            self.price = float(self.price)
        if self.kms != "NULL":
            self.kms = float(self.kms)

        #Insert into database
        try:
            cursor.execute(sql, (self.url, self.make, self.model, self.name, \
                self.price, self.kms, self.location, \
                self.listDate, self.year, self.displacement, self.registered, \
                self.regExpiry, self.colour, self.description, \
                self.learner, self.listType))

            db.commit()
        except Exception as e:
            print("Didn't work")
            print("Exception occured: {}".format(e))
            db.rollback()

        db.close()


def findMakes(category):
    """
    Finds all available makes from main category page
    Returns list of Make page URLs
    """



    pass

def findModels(make):
    """
    Finds all available models from Make page
    Returns list of Make-Model page URLs
    """

    pass

def findURLs(item, category, auto=False):
    """ Finds all listing urls on first page"""
    if item == "NULL":
        page = s.get("http://www.gumtree.com.au/s-%s/c18626" % (category))
    else:
        page = s.get("http://www.gumtree.com.au/s-%s/%s/k0c18626" % (category, item))
    
    soup = BeautifulSoup(page.content, 'html.parser')

    curTime1 = datetime.now()

    itemListing = soup.find_all(class_="user-ad-row link link--base-color-inherit link--hover-color-none link--no-underline")
    for i in soup.find_all(class_="user-ad-row user-ad-row--featured-or-premium link link--base-color-inherit link--hover-color-none link--no-underline"):
        itemListing.append(i)

    for i in soup.find_all(class_="user-ad-row user-ad-row--premium user-ad-row--featured-or-premium link link--base-color-inherit link--hover-color-none link--no-underline"):
        itemListing.append(i)

    urlList = []
    for i in range(0, len(itemListing)):
        urlList.append("https://www.gumtree.com.au" + itemListing[i]['href'])
    
    #Loop for all pages
    #Find last page number
    lastPageURL = soup.find(class_="page-number-navigation__link page-number-navigation__link-last link link--base-color-primary link--hover-color-none link--no-underline")['href']
    lastPage = int(re.search('page-(\d+)', lastPageURL).group(1))

    curTime2 = datetime.now()
    
    #Ask user if they wish to proceed
    if auto:
        #Automatically want to search all pages
        searchPage = lastPage
    else:
        #User input for number of pages to search
        while True:
            userCheck = input("%d pages have been found. How many do you wish to search?(1, 2, ..., all or quit): " % lastPage)
            try:
                searchPage = int(userCheck)
            except ValueError:
                if userCheck.lower() == "all":
                    searchPage = lastPage 
                    break
                elif userCheck.lower() == "quit":
                    quit()
                else:
                    print("Please enter a number, all or quit")
                    continue
            else:
                break
    
    #Store current time for performance indicator later
    curTime3 = datetime.now()

    #Scrape listing URLs from each page
    for i in tqdm(range(2, searchPage+1)):
        #Find page
        if item == "NULL":
            page = s.get("http://www.gumtree.com.au/s-%s/page-%d/c18626" % (category, i))
        else:
            page = s.get("http://www.gumtree.com.au/s-%s/%s/page-%d/k0c18626" % (category, item, i))
        
        soup = BeautifulSoup(page.content, 'html.parser')

        #Scrape page
        itemListing = soup.find_all(class_="user-ad-row link link--base-color-inherit link--hover-color-none link--no-underline")
        for i in soup.find_all(class_="user-ad-row user-ad-row--featured-or-premium link link--base-color-inherit link--hover-color-none link--no-underline"):
            itemListing.append(i)

        for i in soup.find_all(class_="user-ad-row user-ad-row--premium user-ad-row--featured-or-premium link link--base-color-inherit link--hover-color-none link--no-underline"):
            itemListing.append(i)

        for i in range(0, len(itemListing)):
            urlList.append("https://www.gumtree.com.au" + itemListing[i]['href'])

    #Display process time
    perfTime = datetime.now() - curTime3 + (curTime2 - curTime1)
    print("Process took: ", perfTime.total_seconds(), "Seconds")


    return urlList


def adExpired(auto=False):
    """ Checks all listings to see if still available. Best results if run daily. """
    #Create connection 
    db = pymysql.connect(host="localhost", user="testUser", passwd="BorrisBulletDodger", db="allItems", charset='utf8')
    cursor = db.cursor()

    #Record todays date
    curTime = datetime.now().strftime("%Y-%m-%d")
    
    #SQL Query
    sql = "SELECT url, adExpiry FROM motorcycles WHERE adExpiry IS NULL"

    #Find data
    try: 
        cursor.execute(sql)
        result = cursor.fetchall()
        data = [ [i[0], i[1]] for i in result]
        db.commit()
    except Exception as e:
        db.rollback()
        print("Exception occured: {}".format(e))

    #continue check
    while not auto:
        cont = input("%d listings found - Do you wish to continue?: " % (len(data)))
        if cont.lower() == 'y' or cont.lower() == 'yes':
            break
        elif cont.lower() == 'n' or cont.lower() == 'no':
            quit()
        else:
            print("Please enter y/n")
            continue
    
    count = 0
    for i in tqdm(range(0, len(data))):
        #Request the page from the internet
        page = s.get(data[i][0])

        #Check if page is working
        if page.status_code != 200:
            print(page.status_code, data[i][0])
        #Load page contents into soup
        soup = BeautifulSoup(page.content, 'html.parser')

        #Try find ad-expired id
        if soup.find(id="ad-expired"):
            #Returns true if list not empty
            sql = """UPDATE motorcycles
            SET adExpiry=%s
            WHERE url=%s"""
            try:
                cursor.execute(sql, (curTime, data[i][0]))
                db.commit()
                count += 1
            except Exception as e:
                db.rollback()
                print("Exception occured: {}".format(e))
        

    #Remember to close database at the end            
    db.close()
        
    print("%d/%d tracked listings have been sold since last processed" % (count, len(data)))

def checkURLs(table, allURLs):
    #Create connection 
    db = pymysql.connect(host="localhost", user="testUser", passwd="BorrisBulletDodger", db="bikedb", charset='utf8')
    cursor = db.cursor()

    #SQL Query
    sql = "SELECT url FROM " + table + ";"

    #Find data
    try: 
        cursor.execute(sql)
        result = cursor.fetchall()
        oldURLs = [ link[0] for link in result]
        db.commit()
    except Exception as e:
        db.rollback()
        print("Exception occured: {}".format(e))
    finally:
        db.close()
    
    try:
        newURLs = list(set(allURLs) - set(oldURLs))
    except Exception:
        newURLs = allURLs

    return newURLs


if __name__ == "__main__":

    #Check sold?
    while True:
        checkSold = input("Would you like to check db for sold listings?")
        if checkSold.lower() == 'y' or checkSold.lower() == 'yes':
            adExpired(True)
            break
        elif checkSold.lower() == 'n' or checkSold.lower() == 'no':
            break
        else:
            print("Please enter y/n")
            continue

    #Find URLs
    print("Finding Listing Pages")
    urls = findURLs("NULL", "motorcycles")
    print(str(len(urls)) + " URLs have been found")
    #Check if already in db
    urls = checkURLs("motorcycles", urls)
    print(str(len(urls)) + " URLs are new")

    #Check if user wishes to proceed
    while True:
        cont = input("Do you wish to proceed?")
        if cont.lower() == 'y' or cont.lower() == 'yes':
            break
        elif cont.lower() == 'n' or cont.lower() == 'no':
            quit()
        else:
            print("Please enter y/n")
            continue
    
    password = "BorrisBulletDodger"

    for i in tqdm(range(len(urls))):
        temp = Motorcycle(urls[i])
        temp.dbInsert(password)
    

    """
    test = Motorcycle(urls[0])
    password = "BorrisBulletDodger"
    #password = input("Please Enter Your Password: ")
    test.dbInsert(password)

    """


# Possible errors in listings not being sold but ad expiring
"""Bunch of old urls for later testing
https://www.gumtree.com.au/s-ad/regents-park/motorcycles/2010-ninja-kawasaki-250-/1073867602
https://www.gumtree.com.au/s-ad/hocking/motorcycles/great-buy/1112608894
https://www.gumtree.com.au/s-ad/parkes/motorcycles/1992-zzr-250-ninja/1115904602
https://www.gumtree.com.au/s-ad/innaloo/motorcycles/2011-kawasaki-ninja-250cc-red-black-motorbike-ideal-for-learner/1122083797

"""
