# Main script for running automatically, no inputs

from scraperV1 import *


if __name__ == "__main__":
    #Print out current date/time
    print(datetime.now().strftime("%Y-%m-%d %H:%M"))
    #Check existing listings whether they have been sold
    print("Checking whether stored listings have been sold")
    adExpired(True)

    #Find URLs
    print("Finding Listing Pages")
    urls = findURLs("kawasaki+ninja", "motorcycles", True)
    print(str(len(urls)) + " URLs have been found")
    #Check if already in db
    urls = checkURLs("motorcycles", urls)
    print(str(len(urls)) + " URLs are new")

    #Insert new url records into the database    
    password = "BorrisBulletDodger"
    for i in tqdm(range(len(urls))):
        temp = Motorcycle(urls[i])
        temp.dbInsert(password)