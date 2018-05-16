import requests
from bs4 import BeautifulSoup
from itertools import cycle

url = 'https://httpbin.org/ip'
url2 = 'https://gumtree.com.au'
proxies = {
    "http": 'http://163.172.86.64:3128', 
    "https": 'http://163.172.86.64:3128'

}


def getPrelimProxies(n):
    """ Returns n proxies in a list """
    page = requests.get("https://free-proxy-list.net/")

    if page.status_code != 200:
        print(page.status_code)
    soup = BeautifulSoup(page.content, 'html.parser')

    #test = soup.find(id="proxylisttable")
    #test2 = soup.find_all('tr')
    #test3 = test2[1].find_all('td')[0].contents[0] + ":" + test2[1].find_all('td')[1].contents[0]
    

    proxyLst = []
    for i in range(1, n+1):
        proxyLst.append(soup.find_all('tr')[i].find_all('td')[0].contents[0] + ":" + soup.find_all('tr')[i].find_all('td')[1].contents[0])

    return proxyLst

def getProxies(n):
    newUrlLst = []
    count = 0
    while count < 5:
        proxies = getPrelimProxies(20)
        proxyPool = cycle(proxies)
        failed = []
        for i in range(1, len(proxies)+1):
            #Get proxy from pool
            proxy = next(proxyPool)
            print("Request #%d"%i)
            try:
                response = requests.get(url, proxies={"http": proxy, "https": proxy}, timeout=10)
                print(response.json())
            except:
                print("Connection Error - skipped")
                failed.append(proxy)
    
        if len(failed) > 15:
            #Too many failures, try again
            count += 1
            continue
        else:
            #Found enough working proxies
            newUrlLst = list(set(proxies) - set(failed))
            count = 10
            


    return newUrlLst



if __name__ == "__main__":
    proxies = getProxies(8)
    print(proxies)