import hashlib, requests, time
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from pushbullet import Pushbullet
from config import *

pb = Pushbullet(PUSHBULLET_TOKEN)
lastCityMMNews = []
lastCityBIPChanges = []
lastCityZIMHashes = [""] * len(CITY_ZIM_LINKS)
lastCityZIMBIPChanges = []
BIPOnlyNewArticles = False

def checkCityMM():
    print("Checking CityMM")
    global lastCityMMNews
    r = requests.get(CITY_MM)
    if r.status_code != 200:
        print(f"Error {r.status_code} while fetching MM", r.text)
        pb.push_note(f"Error {r.status_code} while fetching MM", r.text)
        return
    xml = r.content
    root = ET.fromstring(xml)
    lastNews = []
    for news in root.findall(".//item"):
        title = news.find("title").text
        link = news.find("link").text
        pubDate = news.find("pubDate").text
        desc = news.find("description").text
        lastNews.append({"title": title, "link": link, "date": pubDate, "desc": desc})
        if not any(item["link"] == link for item in lastCityMMNews):
            print(f"New news on {CITY_NAME}MM! {title}")
            pb.push_note(title, f"{pubDate}\n{link}\n{desc[:150]}")
    lastCityMMNews = lastNews
    return    

def checkCityBIP():
    print("Checking CityBIP")
    global lastCityBIPChanges
    r = requests.get(f"{CITY_BIP}api/contexts/default/registries?limit=40&offset=0&timeperiod=2")
    if r.status_code != 200:
        print(f"Error {r.status_code} while fetching BIP", r.text)
        pb.push_note(f"Error {r.status_code} while fetching BIP", r.text)
        return
    data = r.json()
    lastChanges = []
    for change in data["elements"]:
        if change["info"] == "Publikacja artykułu" or (not BIPOnlyNewArticles):
            title = change["article"]["title"]
            link = f"{CITY_BIP}{change["article"]["link"]}"
            pubDate = change["date"]
            desc = change["info"]
            lastChanges.append({"title": title, "link": link, "date": pubDate, "desc": desc})
            if not any(item["link"] == link for item in lastCityBIPChanges):
                print(f"New change on {CITY_NAME}BIP! {title}")
                pb.push_note(title, f"{pubDate}\n{link}\n{desc[:150]}")
    lastCityBIPChanges = lastChanges
    return

def checkCityZIM():
    print("Checking CityZIM")
    global lastCityZIMHashes
    for i, link in enumerate(CITY_ZIM_LINKS):
        r = requests.get(link)
        if r.status_code != 200:
            print(f"Error {r.status_code} while fetching ZIM", r.text)
            pb.push_note(f"Error {r.status_code} while fetching ZIM", r.text)
            continue
        current_hash = hashlib.sha256(r.text.encode('utf-8')).hexdigest()

        if lastCityZIMHashes[i] == "": 
            lastCityZIMHashes[i] = current_hash
            continue
        elif current_hash == lastCityZIMHashes[i]:
            continue
        lastCityZIMHashes[i] = current_hash

        params = {
            "access_key": APIFLASH_TOKEN,
            "url": f"{link}"
        }
        response = requests.get("https://api.apiflash.com/v1/urltoimage", params=params)
        if response.status_code != 200:
            pb.push_note("Content changed but Error happened during screenshotting", response.text)
            continue
        with open("screenshot.jpeg", "wb") as file:
            file.write(response.content)
        with open("screenshot.jpeg", "rb") as pic:
            file_data = pb.upload_file(pic, "screenshot.jpeg")
            
        print(f"New change on {CITY_NAME}ZIM! {link}")
        pb.push_note("Update on ZIM", f"{link}")
        pb.push_file(**file_data)
    return

def checkCityZIMBIP():
    print("Checking CityZIMBIP")
    global lastCityZIMBIPChanges
    r = requests.get(f"{CITY_ZIM_BIP}ostatnie-modyfikacje.html")
    if r.status_code != 200:
        print(f"Error {r.status_code} while fetching ZIM BIP", r.text)
        pb.push_note(f"Error {r.status_code} while fetching ZIM BIP", r.text)
        return
    soup = BeautifulSoup(r.content, "html.parser")
    lastChanges = []
    changes = soup.select(".s.effect1")
    for change in changes:
        title = change.select(".s2")[0].get_text()
        link = f"{CITY_ZIM_BIP}{change.select("a")[1].get("href")}"
        pubDate = change.select(".s.effect1 div.pull-left.nobcg span")[1].get_text()
        desc = change.select("p.s3")[0].get_text()
        lastChanges.append({"title": title, "link": link, "date": pubDate, "desc": desc})
        if not any(item["link"] == link for item in lastCityZIMBIPChanges):
            print(f"New change on {CITY_NAME}ZIMBIP! {title}")
            pb.push_note(title, f"{pubDate}\n{link}\n{desc[:150]}")
    lastCityZIMBIPChanges = lastChanges
    return


def main():
    while True:
        try:
            checkCityMM()
        except Exception as e:
            print(f"Error in checkCityMM: {e}")

        try:
            checkCityBIP()
        except Exception as e:
            print(f"Error in checkCityBIP: {e}")

        try:
            checkCityZIM()
        except Exception as e:
            print(f"Error in checkCityZIM: {e}")

        try:
            checkCityZIMBIP()
        except Exception as e:
            print(f"Error in checkCityZIMBIP: {e}")

        print("Checks completed. Waiting for 5 minutes before next cycle...")
        time.sleep(300)

if __name__ == "__main__":
    main()