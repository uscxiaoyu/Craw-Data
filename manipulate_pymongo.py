# coding=utf-8
#%%
from pymongo import MongoClient

#%%
client = MongoClient()
db = client.moniter_crowdfunding
db.list_collection_names()

#%%
m_prj = db.projects
f_prj = db.failure_projects

#%%
print("预热中数量:", m_prj.count_documents({"状态":'预热中'}))
print("众筹中数量:", m_prj.count_documents({"状态":'众筹中'}))
print("众筹成功数量:", m_prj.count_documents({"状态":'众筹成功'}))
print("项目成功数量:", m_prj.count_documents({"状态": '项目成功'}))
print("众筹未成功数量:", f_prj.count_documents({"详细信息.状态": '众筹未成功'}))
print("项目未成功数量:", f_prj.count_documents({"详细信息.状态": '项目未成功'}))


#%%
f_prj.find_one({}, projection={})