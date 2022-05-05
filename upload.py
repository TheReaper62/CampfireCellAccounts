import os, json
import subapy
from datetime import datetime
from zoneinfo import ZoneInfo

def getenv(key: str) -> str:
    return os.getenv(key) if os.getenv(key) != None else json.loads(open('config.json').read())[key]

def datetime_now(): return datetime.now(tz=ZoneInfo("Asia/Singapore"))

DB = subapy.Client(
    db_url=getenv('supabase_url'),
    api_key=getenv('supabase_api_key')
)

def get_posted_tdy():
    DB.table = 'History'
    result = DB.read('*')
    DB.table = "Tasks"
    for i in result:
        # Example Date: 2022123 [YYYY(DOY)]
        tdy_formatted = int(datetime_now().strftime(r"%Y%j"))
        if i['id'] == tdy_formatted and i['posted']:
            return True
    return False

def check_newday():
    posted_tdy = get_posted_tdy()
    print('Posted today: ', posted_tdy)

    if not posted_tdy:
        now = datetime_now()
        posted_tdy = True
        DB.table = 'History'
        pri_key = int(datetime_now().strftime(r'%Y%j'))
        DB.insert({'id': pri_key, 'posted': True}, subapy.Filter('id', 'eq', pri_key), upsert=True)
        DB.table = 'Tasks'
        print('Posted today(Updated)')

get_posted_tdy()
check_newday()
get_posted_tdy()
