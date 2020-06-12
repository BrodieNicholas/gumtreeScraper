from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import time
import requests
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
import pymysql
import re
import logging
from tqdm import tqdm
from warnings import filterwarnings
from threading import Thread, Lock
from queue import Queue
from sys import stdout
tqdm.monitor_interval = 0
filterwarnings('ignore', category = pymysql.Warning)


#Set Retries within Requests
s = requests.Session()
retries = Retry(total=500, backoff_factor=0.1, status_forcelist=[ 500, 502, 503, 504])
s.mount('http://', HTTPAdapter(max_retries=retries))


"""
Sample Gumtree URL's
Motorbikes -
https://www.gumtree.com.au/s-motorcycles/model-ag200/motorcyclesmake-yamha/c18626 
https://www.gumtree.com.au/s-ad/ringwood/motorcycles/2018-yamaha-ag200-off-road-bike-196cc/1241008373
Cars - 
https://www.gumtree.com.au/s-cars-vans-utes/carmake-bmw/carmodel-bmw_28/c18320
https://www.gumtree.com.au/s-ad/bowen-hills/cars-vans-utes/2006-bmw-x3-e83-my06-steptronic-black-5-speed-sports-automatic-wagon/1241069626
"""

logger = logging.getLogger('myapp')
hdlr = logging.FileHandler('myapp.log')
formatter = logging.Formatter('%(asctime)s %(threadName)-9s %(levelname)s %(message)s')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr) 
logger.setLevel(logging.INFO)
logger.info("Starting Script")
printlog = ""

class Item:
    def __init__(self, url):
        """
        URL split on "/" gives ['', 's-ad', location, category, name, randomNumber]
        """
        self.time = datetime.now().time()
        self.url = url
        self.location = url.split("/")[2]
        self.category = url.split("/")[3]
        self.name = url.split("/")[4]
        self.price = "NULL"
        self.listDate = "NULL"
        self.na = False

    def timeSinceQuery(self):
        """ Find time between object creation and now"""
        return self.time - datetime.now().time()

    def scrape(self):
        """ 
        Scrape the items URL for price and date listed
        Returns itemPrice, itemListDate
        """
        #Get page
        soup, _ = getPage(self.url)

        #Check if page available
        if soup is None:
            #Not available, skip iteration
            self.na = True
            return

        #Get Price
        self.price = soup.find(class_="user-ad-price__price").get_text()
        #Get list of attr names and values
        adAttrVals = soup.find_all(class_="vip-ad-attributes__value")
        adAttrName = soup.find_all(class_="vip-ad-attributes__name")
        #Search attrs for date listed
        for i in range(0,len(adAttrName)):
            if adAttrVals[i].contents[0] == "Date Listed":
                self.listDate = adAttrName[i].contents[0]
                break
        

class Motorcycle(Item):
    def __init__(self, url):
        super().__init__(url)
        #Set default values to NULL for mysql
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
        self.na = False
        #Scrape values where available
        self.scrape()

    def scrape(self):
        """
        Pull Information about the motorcycle
        No return, holds info in self variables
        """

        #Get page
        soup, _ = getPage(self.url)

        #Check page was found
        if soup is None:
            self.na = True
            return

        #Find price
        try:
            self.price = soup.find(class_="user-ad-price__price").get_text()
        except:
            pass

        #Find attributes names/values
        adAttrVals = soup.find_all(class_="vip-ad-attributes__name")
        adAttrName = soup.find_all(class_="vip-ad-attributes__value")
        #Find description
        try:
            self.description = soup.find(class_="vip-ad-description__content--wrapped").get_text()
        except:
            pass

        #Check all attributes for important information
        for i in range(0,len(adAttrName)):
            tempName = adAttrName[i].get_text()
            tempVal = adAttrVals[i].get_text()
            if "Date Listed:" in tempName:
                #Can be date or words (eg 16 minutes ago, yesterday)
                try:
                    #Will work if date
                    listDateLst = tempVal.lstrip().split('/')
                    self.listDate = listDateLst[2]+'-'+listDateLst[1]+'-'+listDateLst[0]
                except:
                    #Check not empty
                    if tempVal is not None:
                        if tempVal == "Yesterday":
                            #Yesterday
                            self.listDate = (datetime.today() - timedelta(days=1)).strftime('%Y-%m-%d')
                        else:
                            #Either hours or minutes
                            self.listDate = datetime.today().strftime('%Y-%m-%d')
                    
            elif "Displacement (cc):" in tempName:
                self.displacement = tempVal.lstrip()
            elif "Make:" in tempName:
                self.make = tempVal.lstrip()
            elif "Model:" in tempName:
                self.model = tempVal.lstrip()
            elif "Year:" in tempName:
                self.year = tempVal.lstrip()
            elif "KMs:" in tempName:
                self.kms = tempVal.lstrip()
            elif "Registered:" in tempName:
                if tempVal.lstrip() == "Yes":
                    self.registered = "Y"
                elif tempVal.lstrip() == "No":
                    self.registered = "N"
            elif "Registration Expiry:" in tempName:
                regExpLst = tempVal.lstrip().split('/')
                self.regExpiry = regExpLst[2]+'-'+regExpLst[1]+'-'+regExpLst[0]
            elif "Colour:" in tempName:
                self.colour = tempVal.lstrip()
            elif "Learner Approved:" in tempName:
                if tempVal.lstrip() == "Yes":
                    self.learner = "Y"
                elif tempVal.lstrip() == "No":
                    self.learner = "N"
            elif "Listing Type:" in tempName:
                self.listType = tempVal.lstrip()

    def dbInsert(self):
        db = pymysql.connect(host="localhost", user="testUser", passwd="BorrisBulletDodger", db="scraperdb", charset='utf8')
        cursor = db.cursor()
	
        #SQL Query
        sql = "INSERT IGNORE INTO motorcycles VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NULL);"

        #Convert strings into floats
        if self.price == "":
            self.price = "NULL"
        if self.kms == "":
            self.kms = "NULL"
        if self.price != "NULL":
            self.price = float(self.price.replace("$", "").replace(",",""))
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


def getMakes():
    """
    Finds all available makes from main category page
    Returns list of Make page URLs
    """

    #Get category page as Soup
    soup, _ = getPage("/s-motorcycles/c18626")

    #Check if page available
    if soup is None:
        #Not available
        print("Can't get motorcycle category page")
        quit()


    #Find all makes from main category page
    #Find span with text "Make"
    span = soup.find(class_="srp-filter-group__filter-name", text="Make")
    #Move up two parents
    a = span.parent.parent
    #Find all filter names
    b = a.find_all(class_="srp-list-filter__item-link link link--no-underline")
    makes = [i['href'] for i in b]
    return makes


def getModels(makeURL):
    """
    Finds all available models from Make page
    Returns list of Make-Model page URLs
    """

    #Get make page as Soup
    soup, _ = getPage(makeURL)

    #Check if page available
    if soup is None:
        #Not available - break
        print("Can't find Make URL")
        quit()

    #Try to find models list
    try:
        #Find span with text "Make"
        span = soup.find(class_="srp-filter-group__filter-name", text="Make")
        #Move up two parents
        a = span.parent.parent
        #Find all filter names
        b = a.find_all(class_="srp-list-filter__item-link link link--no-underline")
        models = [i['href'] for i in b]
        models = models[1:]
    except:
        print(makeURL)
        models=[]
    
    logger.debug(f"Models include: {models}")
    return models

def getURLs(modelURL):
    """
    Finds all listing URLs across model pages
    Returns list of URLs
    """

    #Get model page as soup
    soup, _ = getPage(modelURL)

    #Check if page available
    if soup is None:
        #Not available - Break
        print("Can't find Model URL")
        quit()
    
    #Get URLs on first page
    urlList = listingURLs(soup)

    #Find last page number if available
    try:
        lastPageURL = soup.find(class_="page-number-navigation__link page-number-navigation__link-last link link--base-color-primary link--hover-color-none link--no-underline")['href']
        lastPage = int(re.search('page-(\d+)', lastPageURL).group(1))
    except:
        #No Last page button - Only one page of results
        lastPage = None

    #Loop for all pages if available
    if lastPage is not None:
        for i in range(2, lastPage + 1):
            #Create Page URL
            urlParts = modelURL.split("/")
            urlParts = urlParts[:-1] + [f"page-{i}"] + urlParts[-1:]
            pageURL = "/".join(urlParts)
            #Get Page
            soup, _ = getPage(pageURL)
            #Check if page available
            if soup is None:
                #Not available, skip iteration
                continue
            #Get Pages URLs
            urlList += listingURLs(soup)

    return urlList

def listingURLs(soup):
    """
    Returns all listing URLs from a page soup
    """

    #Get URLs
    itemListing = soup.find_all(class_="user-ad-row link link--base-color-inherit link--hover-color-none link--no-underline")
    itemListing += soup.find_all(class_="user-ad-row user-ad-row--featured-or-premium link link--base-color-inherit link--hover-color-none link--no-underline")
    itemListing += soup.find_all(class_="user-ad-row user-ad-row--premium user-ad-row--featured-or-premium link link--base-color-inherit link--hover-color-none link--no-underline")
    #Create list
    urlList = [i['href'] for i in itemListing]
    return urlList


def getPage(suffix):
    """
    Requests url and handles errors
    Returns beautifulSoup.soup, adExpiredBool
    """
    #Set User Agent
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.3"}
    #Request the page from the internet
    try:
        logger.debug(f"Requesting Page: {suffix}")
        page = s.get(f"https://www.gumtree.com.au{suffix}", headers=headers, timeout=600)
    except requests.exceptions.ConnectionError:
        logger.error("Network Connection Error")
        return None, None
    except Exception as e:
        logger.error(e)
        return None, None

    #Check if page is working - quit otherwise
    if page.status_code != 200:
        #If checking and page isn't available - ad expired 
        if page.status_code == 404:
            logger.debug(f"Found 404 at {suffix}")
            return None, True
        else:
            logger.warning(f"Page not available - status code {page.status_code}")
            return None, None
    else:
        logger.debug(f"Found Page: {suffix}")

    #Load page content into soup
    soup = BeautifulSoup(page.content, 'html.parser')
    
    #Check if sold
    sold = soup.find(class_="expired-ad__flag--sold")
    if sold:
        return None, True
    else:
        return soup, None

def removeDups(lst):
    """
    Function removes duplicates from a list
    Returns list without duplicates
    """

    return list(dict.fromkeys(lst) )

def newURLs(table, allURLs):
    #Create connection 
    db = pymysql.connect(host="localhost", user="testUser", passwd="BorrisBulletDodger", db="scraperdb", charset='utf8')
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
    
    #Remove old urls
    try:
        newURLs = list(set(allURLs) - set(oldURLs))
    except Exception:
        newURLs = allURLs

    return newURLs

def checkSold(auto=False):
    """
    Check all urls in db that havent got an expiry date
    """

    #Create connection 
    db = pymysql.connect(host="localhost", user="testUser", passwd="BorrisBulletDodger", db="scraperdb", charset='utf8')
    cursor = db.cursor()

    #SQL Query
    sql = "SELECT url FROM motorcycles WHERE adExpiry IS NULL"

    #Find data
    try: 
        cursor.execute(sql)
        sqlResult = cursor.fetchall()
        urls = [i[0] for i in sqlResult]
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Exception occured: {e}")

    #User input to proceed if not auto
    while not auto:
        cont = input(f"{len(urls)} stored listings found - Do you wish to check if sold?: ")
        if cont.lower() == 'y' or cont.lower() == 'yes':
            break
        elif cont.lower() == 'n' or cont.lower() == 'no':
            return
        else:
            print("Please enter y/n")
            continue
    
    #Use threading to check if urls have expired
    maxThreads = 5
    urlsQ =  Queue(maxsize=0)
    #Set number of threads
    numThreads = min(maxThreads, len(urls))
    #Create lock
    lock = Lock()
    #Create progress bar
    pbar = tqdm(total=len(urls))
    
    #Expired test
    def checkExpiredThread(q, results, db, cursor):
        """
        Checks whether input url has expired
        Input: ["url"], {} - Keys=urls, vals=False
        """

        while not q.empty():
            url = q.get()
            logger.debug(f"{url} started - Tasks left: {q.unfinished_tasks}")
            pbar.update(1)
            expired = None

            #Check if expired
            _, expired = getPage(url)
            results[url] = expired

            #Insert result into db
            if expired:
                logger.debug(f"expired url: {url}")
                #Record todays date
                curTime = datetime.now().strftime("%Y-%m-%d")
                #Prepare sql string
                sql = """UPDATE motorcycles
                SET adExpiry=%s
                WHERE url=%s"""
                #Get Lock - Prevent multiple db inserts simulataneously
                logger.debug(f"{url} wants the lock")
                with lock:
                    logger.debug(f"{url} has the lock")
                    try:
                        cursor.execute(sql, (curTime, url))
                        db.commit()
                    except Exception as e:
                        db.rollback()
                        print("Exception occured: {}".format(e))
                    logger.debug(f"{url} is finished with the lock")

            q.task_done()
            logger.debug(f"{url} finished")


    #Load queue with urls, results dict keys = urls, vals = False - Ad default not expired
    results = {}
    for url in urls:
        urlsQ.put(url)
        results[url] = False

    #Create threads that execute checkExpiredThread function, updates data
    for _ in range(numThreads):
        worker = Thread(target=checkExpiredThread, args=(urlsQ, results, db, cursor))
        worker.setDaemon(True)
        worker.start()
    #Wait until the queue has been processed - All URLs checked
    urlsQ.join()
    pbar.close()

    #Remember to close database at the end            
    db.close()
    
    #Count number of expired urls
    count = sum(1 for value in results.values() if value)
    logger.info(f"{count}/{len(urls)} tracked listings have been sold since last processed")
    print(f"{count}/{len(urls)} tracked listings have been sold since last processed")

def run_main():
    """
    Main running code
    1. Check existing database to see if any have sold - update expiry date
    2. Find All available Urls on Gumtree
    3. Check Urls are new
    4. Scrape data for each new url
    5. Store in db
    """

    #Check for sold bikes
    checkSold(auto=True) #Change Auto to True to prevent user input

    #Find all available URLs split by Make & Model - Find Make
    print("Getting Makes...")
    makes = getMakes()
    
    #Find all Models for each Make
    print("Getting Models...")
    models = []
    for make in tqdm(makes, desc="Makes"):
        models += getModels(make)


    #Find all URLs for each Model - Scrape bikes on each model
    errlog = ""
    print("Scraping Bikes...")
    for model in tqdm(models, desc="Models"):
        #Get urls for each model
        urlsTemp = getURLs(model)

        #Remove duplicates
        urlsTemp = removeDups(urlsTemp)

        #Remove listings already found
        urlsTemp = newURLs("motorcycles", urlsTemp)

        #Get model description
        try:
            modelDesc = model.split("/")[2].replace("model-", "")
        except:
            modelDesc = "Listings"

        #Find motorbike details on all urls for this model
        #Split by model to prevent large datasets changing during code runtime
        for url in tqdm(urlsTemp, desc=modelDesc, leave=False):
            temp = Motorcycle(url)
            if not temp.na:
                temp.dbInsert()
            else:
                errlog += url + "|"
        
    #Finish
    if not errlog:
        print("Errors Found: ", errlog)
    if not printlog:
        print(printlog)
    
    print("Done!")



if __name__=="__main__":
    
    #Announce Time
    print(datetime.now())

    #Run
    run_main()

    #expPage = "/s-ad/ringwood/motorcycles/2018-yamaha-ag200-off-road-bike-196cc/1241008373"
    