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


# Set Retries within Requests
s = requests.Session()
retries = Retry(total=10, backoff_factor=0.1, status_forcelist=[ 500, 502, 503, 504])
s.mount('http://', HTTPAdapter(max_retries=retries))

# Threading
maxThreads = 6
lock = Lock()

# Logging
logger = logging.getLogger('myapp')
hdlr = logging.FileHandler('myapp.log')
formatter = logging.Formatter('%(asctime)s %(threadName)-9s %(levelname)s %(message)s')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr) 
logger.setLevel(logging.INFO)
logger.info("Starting Script")

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
        self.price = None
        self.listDate = None
        self.na = False

    def timeSinceQuery(self):
        """ Find time between object creation and now"""
        return self.time - datetime.now().time()

    def scrape(self):
        """ 
        Scrape the items URL for price and date listed
        Returns itemPrice, itemListDate
        """
        # Get page
        soup, _ = getPage(self.url)

        # Check if page available
        if soup is None:
            # Not available, skip iteration
            self.na = True
            return

        # Get Price
        self.price = soup.find(class_="user-ad-price__price").get_text()
        # Get list of attr names and values
        adAttrVals = soup.find_all(class_="vip-ad-attributes__value")
        adAttrName = soup.find_all(class_="vip-ad-attributes__name")
        # Search attrs for date listed
        for i in range(0,len(adAttrName)):
            if adAttrVals[i].contents[0] == "Date Listed":
                self.listDate = adAttrName[i].contents[0]
                break
        

class Motorcycle(Item):
    def __init__(self, url):
        super().__init__(url)
        # Set default values to NULL for mysql
        self.displacement = None
        self.make = None
        self.model = None
        self.year = None
        self.bikeType = None
        self.bikeSubType = None
        self.kms = None
        self.registered = None
        self.regExpiry = None
        self.colour = None
        self.description = None
        self.learner = None
        self.listType = None
        self.wanted = None
        self.na = False
        # Scrape values where available
        self.scrape()

    def scrape(self):
        """
        Pull Information about the motorcycle
        No return, holds info in self variables
        """

        # Get page
        soup, _ = getPage(self.url)

        # Check page was found
        if soup is None:
            self.na = True
            return

        # Find price
        try:
            self.price = soup.find(class_="user-ad-price__price").get_text()
        except:
            pass
        
        # Find if wanted ad
        try:
            if "Wanted:" in soup.find(class_="vip-ad-title__header").text:
                self.wanted = True
            else:
                self.wanted = False
        except:
            pass

        # Find attributes names/values
        adAttrVals = soup.find_all(class_="vip-ad-attributes__name")
        adAttrName = soup.find_all(class_="vip-ad-attributes__value")
        # Find description
        try:
            self.description = soup.find(class_="vip-ad-description__content--wrapped").get_text()
        except:
            pass

        # Check all attributes for important information
        for i in range(0,len(adAttrName)):
            tempName = adAttrName[i].get_text()
            tempVal = adAttrVals[i].get_text()
            if "Date Listed:" in tempName:
                # Can be date or words (eg 16 minutes ago, yesterday)
                try:
                    # Will work if date
                    listDateLst = tempVal.lstrip().split('/')
                    self.listDate = listDateLst[2]+'-'+listDateLst[1]+'-'+listDateLst[0]
                except:
                    # Check not empty
                    if tempVal is not None:
                        if tempVal == "Yesterday":
                            # Yesterday
                            self.listDate = (datetime.today() - timedelta(days=1)).strftime('%Y-%m-%d')
                        else:
                            # Either hours or minutes
                            self.listDate = datetime.today().strftime('%Y-%m-%d')
                    
            elif "Displacement (cc):" in tempName:
                self.displacement = tempVal.lstrip()
            elif "Make:" in tempName:
                self.make = tempVal.lstrip()
            elif "Model:" in tempName:
                self.model = tempVal.lstrip()
            elif "Year:" in tempName:
                self.year = tempVal.lstrip()
            elif "Bike Type:" in tempName:
                self.bikeType = tempVal.lstrip()
            elif "Bike Sub-Type:" in tempName:
                self.bikeSubType = tempVal.lstrip()
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
	
        # SQL Query
        sql = "INSERT IGNORE INTO motorcycles(" \
            +"url, make, model, name, price, kms, location, listDate, year, bikeType, " \
            +"bikeSubType, displacement, registered, " \
            +"regExpiry, colour, description, learner, listType, wanted) " \
            +"VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);"

        # Convert strings into floats
        if self.price == "":
            self.price = None
        if self.kms == "":
            self.kms = None
        if self.price != None:
            self.price = float(self.price.replace("$", "").replace(",",""))
        if self.kms != None:
            self.kms = float(self.kms)

        # Insert into database
        try:
            cursor.execute(sql, (self.url, self.make, self.model, self.name, \
                self.price, self.kms, self.location, \
                self.listDate, self.year, self.bikeType, self.bikeSubType, \
                self.displacement, self.registered, \
                self.regExpiry, self.colour, self.description, \
                self.learner, self.listType, self.wanted))

            db.commit()
        except Exception as e:
            print("Didn't work")
            print("Exception occured: {}".format(e))
            db.rollback()

        db.close()

class Car(Item):
    def __init__(self, url):
        super().__init__(url)
        # Set default values to NULL for mysql
        self.sellerType = None
        self.make = None
        self.model = None
        self.variant = None
        self.year = None
        self.kms = None
        self.transmission = None
        self.driveTrain = None
        self.fuelType = None
        self.colour = None
        self.ac = None
        self.vin = None
        self.registered = None
        self.regExpiry = None
        self.description = None
        self.wanted = None
        self.na = False
        # Scrape values where available
        self.scrape()

    def scrape(self):
        """
        Pull Information about the motorcycle
        No return, holds info in self variables
        """

        # Get page
        soup, _ = getPage(self.url)

        # Check page was found
        if soup is None:
            self.na = True
            return

        # Find price
        try:
            self.price = soup.find(class_="user-ad-price__price").get_text()
        except:
            pass

        # Find description
        try:
            self.description = soup.find(class_="vip-ad-description__content--wrapped").get_text()
        except:
            pass

        # Find if wanted ad
        try:
            if "Wanted:" in soup.find(class_="vip-ad-title__header").text:
                self.wanted = True
            else:
                self.wanted = False
        except:
            pass

        try:
            # Find attributes names/values
            adAttrs = [a.parent.contents for a in soup.find_all(class_="vip-ad-attributes__name")]

            # Check all attributes for important information
            for i in adAttrs:
                tempName = i[0].text
                tempVal = i[1].text
                if "Date Listed:" in tempName:
                    # Can be date or words (eg 16 minutes ago, yesterday)
                    try:
                        # Will work if date
                        listDateLst = tempVal.lstrip().split('/')
                        self.listDate = listDateLst[2]+'-'+listDateLst[1]+'-'+listDateLst[0]
                    except:
                        # Check not empty
                        if tempVal is not None:
                            if tempVal == "Yesterday":
                                # Yesterday
                                self.listDate = (datetime.today() - timedelta(days=1)).strftime('%Y-%m-%d')
                            else:
                                # Either hours or minutes
                                self.listDate = datetime.today().strftime('%Y-%m-%d')
                        
                elif "Seller Type:" in tempName:
                    self.sellerType = tempVal.lstrip()
                elif "Make:" in tempName:
                    self.make = tempVal.lstrip()
                elif "Model:" in tempName:
                    self.model = tempVal.lstrip()
                elif "Variant:" in tempName:
                    self.variant = tempVal.lstrip()
                elif "Body Type:" in tempName:
                    self.bodyType = tempVal.lstrip()
                elif "Year:" in tempName:
                    self.year = tempVal.lstrip()
                elif "Kilometres:" in tempName:
                    self.kms = tempVal.lstrip()
                elif "Transmission:" in tempName:
                    self.transmission = tempVal.lstrip()
                elif "Drive Train:" in tempName:
                    self.driveTrain = tempVal.lstrip()
                elif "Fuel Type:" in tempName:
                    self.fuelType = tempVal.lstrip()
                elif "Colour:" in tempName:
                    self.colour = tempVal.lstrip()
                elif "Air Conditioning:" in tempName:
                    self.ac = tempVal.lstrip()
                elif "VIN:" in tempName:
                    self.vin = tempVal.lstrip()
                elif "Registered:" in tempName:
                    if tempVal.lstrip() == "Yes":
                        self.registered = "Y"
                    elif tempVal.lstrip() == "No":
                        self.registered = "N"
                elif "Registration Expiry:" in tempName:
                    regExpLst = tempVal.lstrip().split('/')
                    self.regExpiry = regExpLst[2]+'-'+regExpLst[1]+'-'+regExpLst[0]
        except:
            pass

    def dbInsert(self):
        db = pymysql.connect(host="localhost", user="testUser", passwd="BorrisBulletDodger", db="scraperdb", charset='utf8')
        cursor = db.cursor()
	
        # SQL Query
        sql = "INSERT IGNORE INTO cars(" \
            +"url, sellerType, make, model, variant, name, year, price, kms, transmission, " \
            +"driveTrain, fuelType, colour, ac, location, listDate, registered, regExpiry, " \
            +"description, wanted) " \
            +"VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);"

        # Convert strings into floats
        if self.price == "":
            self.price = None
        if self.kms == "":
            self.kms = None
        if self.price != None:
            self.price = float(self.price.replace("$", "").replace(",",""))
        if self.kms != None:
            self.kms = float(self.kms)

        # Insert into database
        try:
            cursor.execute(sql, (self.url, self.sellerType, self.make, self.model, \
                self.variant, self.name, self.year, self.price, self.kms, \
                self.transmission, self.driveTrain, self.fuelType, self.colour, \
                self.ac, self.location, self.listDate, self.registered, \
                self.regExpiry, self.description, self.wanted))

            db.commit()
        except Exception as e:
            print("Didn't work")
            print("Exception occured: {}".format(e))
            db.rollback()

        db.close()


def getMakes(category):
    """
    Finds all available makes from main category page
    Returns list of Make page URLs
    """

    # Get category page as Soup - split url for use later
    if category == "motorcycles":
        url1 = "/s-motorcycles/"
        url2 = "c18626"
    elif category == "cars":
        url1 = "/s-cars-vans-utes/"
        url2 = "c18320"
    else:
        print("Incorrect category name - getMakes")
    
    soup, _ = getPage(url1 + url2)

    # Check if page available
    if soup is None:
        # Not available
        print(f"Can't get {category} category page")
        quit()

    # Find all makes from main category page
    if category == "motorcycles":
        # Find span with text "Make"
        span = soup.find(class_="srp-filter-group__filter-name", text="Make")
        # Move up two parents
        a = span.parent.parent
        # Find all filter names
        b = a.find_all(class_="srp-list-filter__item-link link link--no-underline")
        makes = [i['href'] for i in b]
    elif category == "cars":
        # Find drop bar
        a = soup.find(class_="select__select", id="srp-range-filter-make")
        # Filter out contents
        b = a.contents
        # Get names
        makeNames = [i.attrs.get("value") for i in b]
        # Create list of urls
        makes = [f"{url1}carmake-{i}/{url2}" for i in makeNames][1:]

    return makes


def getModels(makeURL, category):
    """
    Finds all available models from Make page
    Returns list of Make-Model page URLs
    """

    # Get make page as Soup
    soup, _ = getPage(makeURL)

    # Check if page available
    if soup is None:
        # Not available - break
        print("Can't find Make URL")
        quit()

    # Try to find models list
    try:
        if category == "motorcycles":
            # Find span with text "Make"
            span = soup.find(class_="srp-filter-group__filter-name", text="Make")
            # Move up two parents
            a = span.parent.parent
            # Find all filter names
            b = a.find_all(class_="srp-list-filter__item-link link link--no-underline")
            models = [i['href'] for i in b]
            models = models[1:]
        elif category == "cars":
            # Find drop bar
            a = soup.find(class_="select__select", id="srp-range-filter-model")
            # Filter out contents
            b = a.contents
            # Get names
            modelNames = [i.attrs.get("value") for i in b]
            # Split current url
            make = makeURL.split("/")[2]
            # Create list of urls
            models = [f"/s-cars-vans-utes/{make}/carmodel-{i}/c18320" for i in modelNames][1:]
    except:
        print(makeURL)
        models=[]
    
    logger.debug(f"Models include: {models}")
    return models

def getURLs(modelURL, category):
    """
    Finds all listing URLs across model pages
    Returns list of URLs
    """
    # Wrap function in try 
    try:
        # Get model page as soup
        soup, _ = getPage(modelURL)

        # Check if page available
        if soup is None:
            # Not available - Break and return no urls
            print("Can't find Model URL")
            return []

        # Get number of listings for model
        count = int(soup.find(class_="breadcrumbs__summary--enhanced").text.split(" ")[0])
        
        urlList = []
        # Check if No. listings > gumtree max
        if count > 24*50:
            # Too many listings - split by another category
            if category == "cars":
                if "variant-" in modelURL:
                    # Don't loop again - find first pages urls and continue to find first 50 pages
                    urlList += listingURLs(soup)
                else:
                    # Get list of variants
                    variants = getVariants(modelURL, soup)
                    # Loop through variants using function recursively
                    for variantUrl in tqdm(variants):
                        urlList += getURLs(variantUrl, category)
                    
                    return urlList
        else:
            # Get URLs on first page
            urlList = listingURLs(soup)

        # Find last page number if available
        try:
            lastPageURL = soup.find(class_="page-number-navigation__link page-number-navigation__link-last link link--base-color-primary link--hover-color-none link--no-underline")['href']
            lastPage = int(re.search('page-(\d+)', lastPageURL).group(1))
        except:
            # No Last page button - Only one page of results
            lastPage = None

        # Loop for all pages if available
        results = {}
        if lastPage is not None:
            # Use threading to check if urls have expired
            # maxThreads = 3
            urlsQ = Queue(maxsize=0)
            # Set number of threads
            numThreads = min(maxThreads, lastPage)
            # Get page url parts
            urlParts = modelURL.split("/")
            for i in range(2, lastPage + 1):
                urlParts = urlParts[:-1] + ["page-" + str(i)] + urlParts[-1:]
                pageURL = "/".join(urlParts)
                urlsQ.put(pageURL)
                results[pageURL] = []

            # Create threads to check pages
            for _ in range(numThreads):
                worker = Thread(target=getPageURLsThread, args=(urlsQ, results))
                worker.setDaemon(True)
                worker.start()
            # Wait until the queue has been processed - All URLs checked
            urlsQ.join()

        if len(results.values()) != 0:
            for val in results.values():
                urlList += val

        return urlList
    except:
        print("getURLs failed for model: " + modelURL)
        logger.error("getURLs failed for model: " + modelURL)
        return []

def getPageURLsThread(q, results):
    """
    Threaded function to get urls off page
    """
    while not q.empty():
        pageURL = q.get()
        # Get Page
        soup, _ = getPage(pageURL)
        # Check if page available
        if soup is not None:
            # Get Pages URLs
            results[pageURL] = listingURLs(soup)
        q.task_done()

def getVariants(modelURL, soup):
    """
    Returns list of urls from variants - only cars
    """
    # Split by variant - recursive function to find all urls
    a = soup.find(class_="select__select", id="srp-range-filter-variant")
    # Filter out contents
    b = a.contents
    # Get names
    variantNames = [i.attrs.get("value") for i in b]
    # Split current url
    make = modelURL.split("/")[2]
    model = modelURL.split("/")[3]
    # Create list of urls
    return [f"/s-cars-vans-utes/{make}/{model}/variant-{i}/c18320" for i in variantNames][1:]


def listingURLs(soup):
    """
    Returns all listing URLs from a page soup
    """

    # Get URLs
    itemListing = soup.find_all(class_="user-ad-row link link--base-color-inherit link--hover-color-none link--no-underline")
    itemListing += soup.find_all(class_="user-ad-row user-ad-row--featured-or-premium link link--base-color-inherit link--hover-color-none link--no-underline")
    itemListing += soup.find_all(class_="user-ad-row user-ad-row--premium user-ad-row--featured-or-premium link link--base-color-inherit link--hover-color-none link--no-underline")
    # Create list
    urlList = [i['href'] for i in itemListing]
    return urlList


def getPage(suffix):
    """
    Requests url and handles errors
    Returns beautifulSoup.soup, adExpiredBool
    """
    # Set User Agent
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.3"}
    # Request the page from the internet
    try:
        logger.debug(f"Requesting Page: {suffix}")
        page = s.get(f"https://www.gumtree.com.au{suffix}", headers=headers, timeout=60)
    except requests.exceptions.ConnectionError:
        logger.error(f"Network Connection Error: {suffix}")
        return None, None
    except Exception as e:
        logger.error(f"{e}, {suffix}")
        return None, None
    

    # Check if page is working - quit otherwise
    if page.status_code != 200:
        # If checking and page isn't available - ad expired 
        if page.status_code == 404:
            logger.debug(f"Found 404 at {suffix}")
            return None, True
        else:
            logger.warning(f"Page not available - status code {page.status_code}")
            return None, None
    else:
        logger.debug(f"Found Page: {suffix}")

    # Load page content into soup
    soup = BeautifulSoup(page.content, 'html.parser')
    
    # Check if sold
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
    """
    Returns list of urls not already stored in db
    """
    # Create connection 
    db = pymysql.connect(host="localhost", user="testUser", passwd="BorrisBulletDodger", db="scraperdb", charset='utf8')
    cursor = db.cursor()

    # SQL Query
    sql = "SELECT url FROM " + table + ";"

    # Find data
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
    
    # Remove old urls
    try:
        newURLs = list(set(allURLs) - set(oldURLs))
    except Exception:
        newURLs = allURLs

    return newURLs

def newURLs2(storedUrls, foundUrls):
    """
    Returns list of stored urls not in foundurls
    """

    # Remove found urls from stored urls list
    newURLs = []
    try:
        for i in range(len(storedUrls)):
            if not storedUrls[i][1] in foundUrls:
                newURLs += [storedUrls[i]]
        #newURLs = list(set(storedUrls) - set(foundUrls))
    except Exception:
        newURLs = storedUrls

    return newURLs


def checkSold2(category, foundUrls):
    """
    Check all urls in db that haven't got an expiry date against found urls
    """

    # Set Category
    if category == "motorcycles":
        id_tag = "bike_id"
    elif category == "cars":
        id_tag = "car_id"

    # Create connection 
    db = pymysql.connect(host="localhost", user="testUser", passwd="BorrisBulletDodger", db="scraperdb", charset='utf8')
    cursor = db.cursor()

    # SQL Query
    sql = f"SELECT {id_tag}, url FROM {category} WHERE adExpiry IS NULL"

    # Find data
    try: 
        cursor.execute(sql)
        storedUrls = cursor.fetchall()
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Exception occured: {e}")

    # Remove urls still listed
    urls = newURLs2(storedUrls, foundUrls)

    # Debug
    for i in range(len(storedUrls)):
        logger.info(["Checksold2 stored urls", storedUrls[i]])

    for i in range(len(foundUrls)):
        logger.info(["Checksold2 found urls", foundUrls[i]])

    for i in range(len(urls)):
        logger.info(["Checksold2 new urls", urls[i]])

    print("New check urls method found: " + str(len(urls)))
    
    # Use threading to check if urls have expired
    urlsQ =  Queue(maxsize=0)
    # Set number of threads
    numThreads = min(maxThreads, len(urls))
    # Create progress bar
    pbar = tqdm(total=len(urls))

    def checkExpiredThread(q, results, db, cursor):
        """
        Checks whether input url has expired
        Input: ["url"], {} - Keys=urls, vals=False
        """

        while not q.empty():
            id, url = q.get()
            logger.debug(f"{url} started - Tasks left: {q.unfinished_tasks}")
            pbar.update(1)
            expired = None

            # Check if expired
            _, expired = getPage(url)
            results[url] = expired

            # Insert result into db
            if expired:
                logger.debug(f"expired url: {url}")
                # Record todays date
                curTime = datetime.now().strftime("%Y-%m-%d")
                # Prepare sql string
                sql = f"""UPDATE {category}
                SET adExpiry=%s
                WHERE url=%s AND {id_tag}=%s"""
                # Get Lock - Prevent multiple db inserts simulataneously
                logger.debug(f"{url} wants the lock")
                with lock:
                    logger.debug(f"{url} has the lock")
                    try:
                        cursor.execute(sql, (curTime, url, id))
                        db.commit()
                    except Exception as e:
                        db.rollback()
                        print("Exception occured: {}".format(e))
                    logger.debug(f"{url} is finished with the lock")

            q.task_done()
            logger.debug(f"{url} finished")

    # Load queue with urls, results dict keys = urls, vals = False - Ad default not expired
    results = {}
    for url in urls:
        urlsQ.put(url)
        results[url[1]] = False

    # Create threads that execute checkExpiredThread function, updates data
    for _ in range(numThreads):
        worker = Thread(target=checkExpiredThread, args=(urlsQ, results, db, cursor))
        worker.setDaemon(True)
        worker.start()
    # Wait until the queue has been processed - All URLs checked
    urlsQ.join()
    pbar.close()

    # Remember to close database at the end            
    db.close()

    # Debug
    for key, val in results.items():
        logger.info(["Checksold2 Results dict", key, val])
    
    # Count number of expired urls
    count = sum(1 for value in results.values() if value)
    logger.info(f"{count}/{len(urls)} tracked {category} listings have been sold since last processed")
    print(f"{count}/{len(urls)} tracked {category} listings have been sold since last processed")
    

def checkSold(category, auto=False):
    """
    Check all urls in db that havent got an expiry date
    """
    # Set Category
    if category == "motorcycles":
        id_tag = "bike_id"
    elif category == "cars":
        id_tag = "car_id"

    # Create connection 
    db = pymysql.connect(host="localhost", user="testUser", passwd="BorrisBulletDodger", db="scraperdb", charset='utf8')
    cursor = db.cursor()

    # SQL Query
    sql = f"SELECT {id_tag}, url FROM {category} WHERE adExpiry IS NULL"

    # Find data
    try: 
        cursor.execute(sql)
        urls = cursor.fetchall()
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Exception occured: {e}")

    # User input to proceed if not auto
    while not auto:
        cont = input(f"{len(urls)} stored listings found - Do you wish to check if sold?: ")
        if cont.lower() == 'y' or cont.lower() == 'yes':
            break
        elif cont.lower() == 'n' or cont.lower() == 'no':
            return
        else:
            print("Please enter y/n")
            continue
    
    # Use threading to check if urls have expired
    urlsQ =  Queue(maxsize=0)
    # Set number of threads
    numThreads = min(maxThreads, len(urls))
    # Create lock
    lock = Lock()
    # Create progress bar
    pbar = tqdm(total=len(urls))
    
    def checkExpiredThread(q, results, db, cursor):
        """
        Checks whether input url has expired
        Input: ["url"], {} - Keys=urls, vals=False
        """

        while not q.empty():
            id, url = q.get()
            logger.debug(f"{url} started - Tasks left: {q.unfinished_tasks}")
            pbar.update(1)
            expired = None

            # Check if expired
            _, expired = getPage(url)
            results[url] = expired

            # Insert result into db
            if expired:
                logger.debug(f"expired url: {url}")
                # Record todays date
                curTime = datetime.now().strftime("%Y-%m-%d")
                # Prepare sql string
                sql = f"""UPDATE {category}
                SET adExpiry=%s
                WHERE url=%s AND {id_tag}=%s"""
                # Get Lock - Prevent multiple db inserts simulataneously
                logger.debug(f"{url} wants the lock")
                with lock:
                    logger.debug(f"{url} has the lock")
                    try:
                        cursor.execute(sql, (curTime, url, id))
                        db.commit()
                    except Exception as e:
                        db.rollback()
                        print("Exception occured: {}".format(e))
                    logger.debug(f"{url} is finished with the lock")

            q.task_done()
            logger.debug(f"{url} finished")

    # Load queue with urls, results dict keys = urls, vals = False - Ad default not expired
    results = {}
    for url in urls:
        urlsQ.put(url)
        results[url[1]] = False

    # Create threads that execute checkExpiredThread function, updates data
    for _ in range(numThreads):
        worker = Thread(target=checkExpiredThread, args=(urlsQ, results, db, cursor))
        worker.setDaemon(True)
        worker.start()
    # Wait until the queue has been processed - All URLs checked
    urlsQ.join()
    pbar.close()

    # Remember to close database at the end            
    db.close()

    # Debug
    for key, val in results.items():
        logger.info(["Checksold 1 results dict", key, val])

    for key, val in results.items():
        if val:
            logger.info(["Checksold 1 results dict - sold bikes", key, val])
    
    # Count number of expired urls
    count = sum(1 for value in results.values() if value)
    logger.info(f"{count}/{len(urls)} tracked {category} listings have been sold since last processed")
    print(f"{count}/{len(urls)} tracked {category} listings have been sold since last processed")


def getListings(category, model):
    """
    Finds urls, scrapes data and inserts into db
    """

    # Get urls for each model - Threaded function
    urls = getURLs(model, category)

    # Remove duplicates
    urls = removeDups(urls)

    return urls

def insertListings(category, model, urls):
    """
    Function uses threading to insert new listings into db
    """
    # Remove listings already found
    urlsTemp = newURLs(category, urls)

    # Get model description
    try:
        if category == "motorcycles":
            modelDesc = model.split("/")[2].replace("model-", "")
        elif category == "cars":
            modelDesc = model.split("/")[3].replace("carmodel-", "")
    except:
        modelDesc = "Listings"
    
    # Use threading to scrape new urls and insert into db
    urlsQ = Queue(maxsize=0)
    # Set number of threads
    numThreads = min(maxThreads, len(urlsTemp))
    # Create lock
    lock = Lock()
    # Create progress bar
    pbar = tqdm(total=len(urlsTemp), desc=modelDesc, leave=False)
    
    # Scrape new URL data and insert
    def scrapeInsert(q, category, results):
        """
        Creates new listing object which scrapes data on initialisation
        Inserts object data into db
        """

        while not q.empty():
            # Set up and log
            url = q.get()
            logger.debug(f"{url} scraping - Tasks left: {q.unfinished_tasks}")

            # Create listing object depending on category
            if category == "motorcycles":
                temp = Motorcycle(url)
            elif category == "cars":
                temp = Car(url)

            # If listing object created successfully - insert into db
            # Use lock to prevent multiple insert attempts simultaneously
            logging.debug(f"Scrape Success - {url} wants the lock")
            with lock:
                logger.debug(url + " has the lock")
                if not temp.na:
                    # Scrape successful - insert into db
                    temp.dbInsert()
                    try:
                        results[url] = 1
                    except:
                        print("Error: results[url] unable to = 1")
                        print("results[url] = ", results[url])
                        print("url = " + url + "\n")
                else:
                    # Scrape unsuccessful - record url in errlog
                    results = url + "|"
                logger.debug(url + " is finished with the lock")

            q.task_done()
            pbar.update(1)
            logger.debug(url + " finished scraping")


    # Load queue with urls
    results = {}
    for url in urlsTemp:
        urlsQ.put(url)
        results[url] = None

    # Create threads that execute scrapeInsert function, updates count and errlog
    for _ in range(numThreads):
        worker = Thread(target=scrapeInsert, args=(urlsQ, category, results))
        worker.setDaemon(True)
        worker.start()
    # Wait until the queue has been processed - All URLs checked
    urlsQ.join()
    pbar.close()

    # Split results into count and errlog
    count = 0
    errlog = ""
    for val in results.values():
        if isinstance(val, str):
            errlog += val
        elif isinstance(val, int):
            count += 1

    return count, errlog


def findAttrs():
    """
    Block of code used during testing to find listings attributes
    """
    # Set Category
    # category = "cars"
    category = "motorcycles"

    # Select model and get corresponding URLs
    model = "/s-motorcycles/model-cbr1000rrfireblade/motorcyclesmake-honda/c18626"
    urls = getURLs(model, category)

    temp = {}
    for url in tqdm(urls):
        try:
            # Get page
            soup, _ = getPage(url)

            # Find price
            try:
                price = soup.find(class_="user-ad-price__price").get_text()
            except:
                pass

            # Find attributes names/values
            adAttrVals = soup.find_all(class_="vip-ad-attributes__name")
            adAttrs = [a.parent.contents for a in adAttrVals]
            
            # Add to dict to see unique
            for i in adAttrs:
                adAttrName = i[0].text
                adAttrVal = i[1].text
                temp[adAttrName] = adAttrVal

        except:
            print(url)

    print(temp.items())

def run_main(category, auto=True):
    """
    Main running code - Motorcycles or Cars
    1. Check existing database to see if any have sold - update expiry date
    2. Find All available Urls on Gumtree
    3. Check Urls are new
    4. Scrape data for each new url
    5. Store in db
    """

    # Tell user which category is running
    print(f"Running {category} scraper")

    # Check for sold listings
    # checkSold(category, auto) # Change Auto to True to prevent user input

    # Find all available URLs split by Make & Model - Find Make
    print(f"Getting {category} makes...")
    makes = getMakes(category)
    
    # Find all Models for each Make
    print(f"Getting {category} models...")
    models = []
    for make in tqdm(makes, desc="Makes"):
        models += getModels(make, category)

    # Find all URLs for each Model - Scrape listings on each model
    urls = []
    errlog = ""
    count = 0
    print(f"Scraping {category}...")
    for model in tqdm(models, desc="Models"):
        # Get temp list of urls for each model - split by model to prevent 
        # changes during long runtimes
        urlsTemp = getListings(category, model)
        # Add urls to total list for checking sold later
        urls += urlsTemp
        # Insert into db if new
        countTemp, errlogTemp = insertListings(category, model, urlsTemp)
        count += countTemp
        errlog += errlogTemp

    # Finish adding data to db
    if not errlog:
        print("Errors Found: ", errlog)
    print(f"{count} {category} listings added to database")
    logger.info(f"{count} {category} listings added to database")

    # Test new checksold2 function
    checkSold2(category, urls)
    # Test old to see how many urls replaced. 
    checkSold(category, True)

    print("Done!")
    

if __name__=="__main__":
    
    # Announce Time
    print(datetime.now())

    # Run
    run_main("motorcycles")
    # run_main("cars", False)

    #checkSold2("motorcycles", [])
