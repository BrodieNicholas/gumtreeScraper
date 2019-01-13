from bs4 import BeautifulSoup
import requests
from requests.packages.urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
import urllib
import os

#Set Retries within Requests
s = requests.Session()
retries = Retry(total=5, backoff_factor=0.1, status_forcelist=[ 500, 502, 503, 504])
s.mount('http://', HTTPAdapter(max_retries=retries))


#Request the page from the internet
page = s.get("https://www.gumtree.com.au/s-ad/thornlands/motorcycles/kawasaki-ninja-250/1205781734")

#Check if page is working
if page.status_code != 200:
    print(page.status_code)
#Load page contents into soup
soup = BeautifulSoup(page.content, 'html.parser')

#Find images and download if available
#imgurl = soup.find_all(class_="vip-ad-image__main-image vip-ad-image__main-image--is-visible")
#imgurl = soup.find('img', {'class': "vip-ad-image__main-image vip-ad-image__main-image--is-visible"})['src']
#imgurl = soup.find_all('img')['src']
imgurl = soup.find('img', {'class': "vip-ad-image__main-image-wrapper"})#['src']

print(imgurl)



