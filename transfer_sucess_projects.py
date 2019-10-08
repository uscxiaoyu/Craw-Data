#%%
from pymongo import MongoClient
import datetime
import time

client = MongoClient('localhost', 27017)
db = client.moniter_crowdfunding

#%%
sucess_projects = db.sucess_projects
failure_projects = db.failure_projects
projects = db.projects
count_success = 0

#%%
for proj in projects.find({"状态": "项目成功"}):
    try:
        sucess_projects.insert_one(proj)
        projects.delete_one({"_id": proj["_id"]})
        count_success += 1
    except Exception as e:
        print(e)

#%%
print(time.ctime())
print(f"一共转移成功项目{count_success}项")
#%%
count_failure = 0
for proj in projects.find({'状态': '众筹中',
                           '状态变换时间0-1': {'$lt': datetime.datetime.now() - datetime.timedelta(days=60)},
                           '评论': {'$exists': 1}}):
    print(proj['_id'], proj['状态变换时间0-1'])
    try:
        delta_time = datetime.datetime.now() - proj['项目动态信息'][-1]['爬取时间']
        if delta_time.days > 5:
            failure_projects.insert_one(
                {**proj, 'transfer_time': datetime.datetime.now()})
            projects.delete_one({"_id": proj["_id"]})
            count_failure += 1
            print('  success!')
    except Exception as e:
        print(' ', e)

#%%
print(time.ctime())
print(f"一共转移失败项目{count_failure}项")
