from bs4 import BeautifulSoup
from datetime import datetime
import requests
import re
import pymysql


class Item:
    def __init__(self, url):
        #URL split on "/" gives ['', 's-ad', location, category, name, randomNumber]
        self.time = datetime.now().time()
        self.url = url
        self.location = url.split("/")[2]
        self.category = url.split("/")[3]
        self.name = url.split("/")[4]

        #self.price, self.listDate = self.scrape()

    def timeSinceQuery(self):
        """ Find time between object creation and now"""
        return self.time - datetime.now().time()

    def scrape(self):
        """ Scrape the items URL for price and date listed
        Returns itemPrice, itemListDate
        """
        page = requests.get("https://www.gumtree.com.au"+self.url)
        print("https://www.gumtree.com.au"+self.url)

        if page.status_code != 200:
            print(page.status_code)
        soup = BeautifulSoup(page.content, 'html.parser')

        

        price = soup.find_all(class_="user-ad-price__price")[0].contents[0]

        adAttrVals = soup.find_all(class_="vip-ad-attributes__value")
        adAttrName = soup.find_all(class_="vip-ad-attributes__name")
        
        for i in range(0,len(adAttrName)):
            #print("contents: ", adAttrVals[i].contents, adAttrName[i].contents)
            #print(adAttrVals[i].contents[0])
            #print(adAttrVals[i].contents[0]=="Date Listed")
            #print("")
            if adAttrVals[i].contents[0] == "Date Listed":
                listDate = adAttrName[i].contents[0]
        
        return price, listDate
        #print(listDate)

class Motorcycle(Item):
    def __init__(self, url):
        super().__init__(url)
        self.price, self.listDate, self.displacement, self.make, self.model, \
            self.year, self.kms, self.registered = self.scrape()
    


    def scrape(self):
        """Pull Information about the motorcycle"""
        #Request the page from the internet
        page = requests.get("https://www.gumtree.com.au"+self.url)
        print("https://www.gumtree.com.au"+self.url)

        #Check if page is working
        if page.status_code != 200:
            print(page.status_code)
        #Load page contents into soup
        soup = BeautifulSoup(page.content, 'html.parser')

        
        #Find price
        price = soup.find_all(class_="j-ad-price")[0]['content']
        #Find attributes names/values
        adAttrName = soup.find_all(class_="ad-details__ad-attribute-name")
        adAttrVals = soup.find_all(class_="ad-details__ad-attribute-value")

        #Set defaults 
        #----------------------------------------------------------------------
        listDate = "NA"
        displacement = "NA"
        make = "NA"
        model = "NA"
        year = "NA"
        kms = "NA"
        registered = "NA"
        #----------------------------------------------------------------------
        
        #Check all attributes for important information
        for i in range(0,len(adAttrName)):
            #print(adAttrName[i].contents[0], "Date Listed:" in adAttrName[i].contents[0])
            tempName = adAttrName[i].contents[0]
            if "Date Listed:" in tempName:
                listDateLst = adAttrVals[i].contents[0].lstrip().split('/')
                listDate = listDateLst[2]+'-'+listDateLst[1]+'-'+listDateLst[0]
            elif "Displacement (cc):" in tempName:
                displacement = adAttrVals[i].contents[0].lstrip()
            elif "Make:" in tempName:
                make = adAttrVals[i].contents[0].lstrip()
            elif "Model:" in tempName:
                model = adAttrVals[i].contents[0].lstrip()
            elif "Year:" in tempName:
                year = adAttrVals[i].contents[0].lstrip()
            elif "KMs:" in tempName:
                kms = adAttrVals[i].contents[0].lstrip()
            elif "Registered:" in tempName:
                if adAttrVals[i].contents[0].lstrip() == "Yes":
                    registered = "Y"
                elif  adAttrVals[i].contents[0].lstrip() == "No":
                    registered = "N"
        

        return price, listDate, displacement, make, model, year, kms, registered

    def dbInsert(self, password):
        db = pymysql.connect(host="localhost", user="testUser", passwd=password, db="gumtreeItems")
        cursor = db.cursor()
	
        # Insert to table
        sql = "INSERT INTO motorcycles VALUES (NULL, '%s', '%s', '%s', '%s', %d, %d, '%s', '%s', '%s', '%s', '%s');" % (self.url, self.make, self.model, self.name, float(self.price), float(self.kms), self.location, self.listDate, self.year, self.displacement, self.registered)

        print(sql)

        testing =(self.url, self.make, self.model, self.name, float(self.price), float(self.kms), self.location, self.listDate, self.year, self.displacement, self.registered)
        for i in range(0, len(testing)):
            print(testing[i], type(testing[i]))
            if isinstance(testing[i], str):
                print(len(testing[i]))


        try:
            cursor.execute(sql)
            db.commit()
        except:
            print("Didn't work")
            db.rollback()

        db.close()




def findURLs(item, category, allPages):
    """ Finds all listing urls on first page"""
    page = requests.get("http://www.gumtree.com.au/s-%s/%s/k0c18626" % (category, item))
    soup = BeautifulSoup(page.content, 'html.parser')

    itemListing = soup.find_all(class_="user-ad-row link link--base-color-inherit \
        link--hover-color-none link--no-underline")
    for i in soup.find_all(class_="user-ad-row user-ad-row--featured-or-premium link \
        link--base-color-inherit link--hover-color-none link--no-underline"):
        itemListing.append(i)

    for i in soup.find_all(class_="user-ad-row user-ad-row--premium user-ad-row--featured-or-premium \
        link link--base-color-inherit link--hover-color-none link--no-underline"):
        itemListing.append(i)

    urlList = []
    for i in range(0, len(itemListing)):
        urlList.append(itemListing[i]['href'])
    
    #Loop for all pages
    if allPages:
        #Find last page number
        lastPageURL = soup.find(class_="page-number-navigation__link page-number-navigation__link-last \
            link link--base-color-primary link--hover-color-none link--no-underline")['href']
        lastPage = int(re.search('page-(\d+)', lastPageURL).group(1))
        #Ask user if they wish to proceed
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
        
        

        #Scrape listing URLs from each page
        for i in range(2, searchPage+1):
            #Tell user what is happening
            print("Scraping Listings on page %d of %d" % (i, searchPage))
            #Find page
            page = requests.get("http://www.gumtree.com.au/s-%s/%s/page-%d/k0c18626" % (category, item, i))
            soup = BeautifulSoup(page.content, 'html.parser')

            #Scrape page
            itemListing = soup.find_all(class_="user-ad-row link link--base-color-inherit \
                link--hover-color-none link--no-underline")
            for i in soup.find_all(class_="user-ad-row user-ad-row--featured-or-premium link \
                link--base-color-inherit link--hover-color-none link--no-underline"):
                itemListing.append(i)

            for i in soup.find_all(class_="user-ad-row user-ad-row--premium user-ad-row--featured-or-premium \
                link link--base-color-inherit link--hover-color-none link--no-underline"):
                itemListing.append(i)

            for i in range(0, len(itemListing)):
                urlList.append(itemListing[i]['href'])


    return urlList
    





if __name__ == "__main__":
    #test = Motorcycle("/s-ad/hendon/motorcycles/2008-honda-cb1000r-naked-with-rego/1158160487")
    #test2 = Item("/s-ad/hastings/laptops/13-macbook-pro-with-touch-bar/1181721019")
    #print(test2.price)
    #print(test.price, test.listDate)

    
    curTime = datetime.now()
    urls = findURLs("kawasaki+ninja", "motorcycles", True)
    print(len(urls))
    perfTime = datetime.now() - curTime
    print("Process took: ", perfTime.total_seconds(), "Seconds")
    test = Motorcycle(urls[0])
    #print(test.listDate)
    password = "BorrisBulletDodger"
    #password = input("Please Enter Your Password: ")
    test.dbInsert(password)

    #data = []
    #for i in range(0, 1):
    #    temp = Motorcycle(urls[i])
    #    data.append(vars(temp))
    
    #print(data)
