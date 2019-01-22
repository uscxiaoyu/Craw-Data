#%%
from pymongo import MongoClient
from singlecrawl import Single_proj_craw
import datetime
import time
# 数据库:名称和容量
client = MongoClient()
print("name                   sizeOnDisk")
for x in client.list_databases():
    print(f"{x['name']:22}\t{x['sizeOnDisk']/(1024**2):.2f}M")

#%%
db = client.moniter_crowdfunding
db.list_collection_names()
#%%
m_prj = db.projects  # 众筹中项目信息
#%%
x = m_prj.find_one({"状态": "项目成功"})
x.keys()
#%%
x["_id"], x['状态变换时间2-3'], x['状态变换时间3-4']

#%%
len(x["评论"]["评论详细"])
#%%
# 重新给没有获取评论信息的项目爬取评论信息
review_dict = {}
for item in m_prj.find({"状态": "项目成功", "状态变换时间3-4": {"$gt": datetime.datetime(2019, 1, 8, 12, 0, 0)}}):
    p_id = item["_id"]
    t1 = time.process_time()
    try:
        s_craw = Single_proj_craw(p_id, count_inqury=20)
        review_data = s_craw.start_craw()
        review_dict[p_id] = review_data
    except Exception as e:
        print(e)
    print(f"项目编号: {p_id}  耗时: {time.process_time() - t1:.2f}秒")
#%%
review_data.keys()
#%%
# 将爬取的评论信息写入到mongodb数据库中
for item in m_prj.find({"状态": "项目成功", "状态变换时间3-4": {"$gt": datetime.datetime(2019, 1, 8, 12, 0, 0)}}):
    p_id = item["_id"]
    try:
        print(item["评论"].keys())
    except Exception as e:
        print(item["_id"], "重新插入评论信息")
        m_prj.update_one({"_id": p_id}, {"$set": {"评论": review_dict[p_id]}})
        