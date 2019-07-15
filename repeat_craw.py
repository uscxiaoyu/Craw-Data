#utf-8
import os

try:
    os.system("/ usr/bin/python3 / home/ubuntu/GitProjects/Craw-Data/crowdfunding_monitor.py >> /home/ubuntu/GitProjects/Craw-Data/execu.log 2 > &1")
except Exception as e:
    print(e)
    os.system("/ usr/bin/python3 / home/ubuntu/GitProjects/Craw-Data/crowdfunding_monitor.py >> /home/ubuntu/GitProjects/Craw-Data/execu.log 2 > &1")
