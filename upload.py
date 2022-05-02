from datetime import datetime
from bs4 import BeautifulSoup as bs
import re

urlify = lambda text: text.strip().lower().replace(' ', '%20').replace(',', '%2C').replace(":","%3A")

actual_day = datetime.now().timetuple().tm_yday
difference = 17
reading_day = actual_day - difference
show_diff = 59
show_day = actual_day - show_diff
if reading_day < 1:
    reading_day += 365

with open('reads.html') as f:
    soup = bs(f.read(),'html.parser')
sauce = soup.find_all({"tr":{"class":"not-active"}})
tar = sauce[reading_day-1].text
passage = ",".join(re.split(r", |\n",tar)[2:-1])
processed_passage = f"https://www.biblegateway.com/passage/?search={urlify(passage)}&version=NLT"
cgs = ["Campfire","Arise"]
date = datetime.strftime(datetime.now(),r"%Y-%m-%d")
for cg in cgs:
    details = {
        "created_at" : date,
        "title": f"Day {show_day}",
        "urls": processed_passage,
        "cell_group": cg,
        "author": 591107669180284928,
        'prompt': 'No Questions Set'
    }
    print(details)