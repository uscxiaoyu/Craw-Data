# coding=utf-8
#%%
from pymongo import MongoClient
import datetime
#%%
# 数据库名称和容量
client = MongoClient()
print("name                   sizeOnDisk")
for x in client.list_databases():
    print(f"{x['name']:22}\t{x['sizeOnDisk']/(1024**2):.2f}M")

#%%
db = client.moniter_crowdfunding
db.list_collection_names()

#%%
m_prj = db.projects  # 众筹中项目信息
f_prj = db.failure_projects  # 失败项目信息

#%%
print("预热中数量:", m_prj.count_documents({"状态":'预热中'}))
print("众筹中数量:", m_prj.count_documents({"状态":'众筹中'}))
print("众筹成功数量:", m_prj.count_documents({"状态":'众筹成功'}))
print("项目成功数量:", m_prj.count_documents({"状态": '项目成功'}))
print("众筹未成功数量:", f_prj.count_documents({"详细信息.状态": '众筹未成功'}))
print("项目未成功数量:", f_prj.count_documents({"详细信息.状态": '项目未成功'}))

#%%
x = f_prj.find_one()
x.keys()

#%%
detail_x = x["详细信息"]
print(detail_x.keys())

#%%
# 挽回损失
rec_cont = list(f_prj.find({"失败时间": {"$gt": datetime.datetime(2019, 1, 8, 16, 0, 0),
                                 "$lt": datetime.datetime(2019, 1, 8, 18, 30, 0)}}))
#%%
for x in rec_cont:
    print(x["项目编号"])
#%%
for x in rec_cont:
    print(x['失败时间'], x['项目编号'])
    detail_x = x["详细信息"]
    if detail_x["状态"] == "众筹失败":
        detail_x["状态"] = "预热中"
    elif detail_x["状态"] == "众筹未成功":
        detail_x["状态"] = "众筹中"
    elif detail_x["状态"] == "项目未成功":
        detail_x["状态"] = "众筹成功"
    try:
        m_prj.insert_one(detail_x)
    except Exception as e:
        print("操作失败", e)

#%%
m_prj.delete_one({"_id": "109256"})

#%%
for x in rec_cont:
    if x["项目编号"] == "109256":
        print(x['失败时间'], x['项目编号'])
        detail_x = x["详细信息"]
        if detail_x["状态"] == "众筹失败":
            detail_x["状态"] = "预热中"
        elif detail_x["状态"] == "众筹未成功":
            detail_x["状态"] = "众筹中"
        elif detail_x["状态"] == "项目未成功":
            detail_x["状态"] = "众筹成功"
        try:
            m_prj.insert_one(detail_x)
        except Exception as e:
            print("操作失败", e)