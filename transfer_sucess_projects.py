#%%
from pymongo import MongoClient
import time

client = MongoClient('localhost', 27017)
db = client.moniter_crowdfunding

#%%
sucess_projects = db.sucess_projects
projects = db.projects
count = 0

#%%
for proj in projects.find({"状态": "项目成功"}):
    try:
        sucess_projects.insert_one(proj)
        projects.delete_one({"_id": proj["_id"]})
        count += 1
    except Exception as e:
        print(e)

#%%
print(time.ctime())
print(f"一共转移{count}项")
#%%
