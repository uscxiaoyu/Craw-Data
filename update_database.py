# coding=utf-8
from pymongo import MongoClient
import os
import datetime

client = MongoClient()
db = client.moniter_crowdfunding
db.list_collection_names()

db.projects.drop()
db.front_page.drop()
db.failure_projects.drop()

output = os.popen("mongorestore -d moniter_crowdfunding --dir /Users/xiaoyu/Desktop/moniter_crowdfunding")
print(output.read())
