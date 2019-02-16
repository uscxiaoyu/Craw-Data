#coding=utf-8
import smtplib
import base64
from email.mime.text import MIMEText
from email.utils import formataddr

def send_mail(title, content, mail_user, mail_pass, sender, receiver, mail_host='smtp.163.com'):
    message = MIMEText(content, 'plain')
    message['From'] = formataddr(['SERVER TEST!', sender])
    message['To'] = formataddr(['QQ', receiver])
    message['Subject'] = title
    try:
        smtpObj = smtplib.SMTP_SSL(mail_host, 465)
        smtpObj.ehlo()
        #smtpObj.connect(mail_host, 465)    # 465 为 SMTP SSL加密 端口号
        smtpObj.login(mail_user, mail_pass)
        smtpObj.sendmail(sender, receiver, message.as_string())
        smtpObj.close()
        print("邮件发送成功!")
    except smtplib.SMTPException as e:
        print("Error: 无法发送邮件!")
        print('错误如下:', e)

if __name__ == "__main__":
    mail_user, mail_pass, sender, receiver = "xy_workstudio", "xiaoyu1986", "xy_workstudio@163.com", "317889109@qq.com"
    title = "测试！"
    content = "123141"
    send_mail(title, content, mail_user, mail_pass, sender, receiver)

