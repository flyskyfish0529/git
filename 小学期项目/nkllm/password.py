import configparser

import pymysql
from dotenv import load_dotenv
from pydantic import BaseModel

# 加载环境变量
load_dotenv()

# 读取配置文件
config = configparser.ConfigParser()
config.read('config.ini')


db_config = {
    'host': config['database']['host'],
    'database': config['database']['database_user'],
    'user': config['database']['user'],
    'password': config['database']['password'],
    'charset': 'utf8mb4'
}
connection = pymysql.connect(**db_config)

frontward = config['IP']['frontward']  # 前端地址

class user(BaseModel):
    phone_number:str
    password:str

async def judge(thisuser:user):
    with connection.cursor() as cursor:
        sql = f"SELECT * FROM alluser where phone_number={thisuser.phone_number}"
        cursor.execute(sql)
        user_a = cursor.fetchall()
        if len(user_a) == 0:
            return {"state": 400, "message": "请先注册账号。"}
        elif user_a[1]!=thisuser.password:
            return {"state": 400, "message": "密码错误，请重试。"}
        else:
            return {"state": 200, "message": "密码正确。"}


async def change(thisuser:user):
    with connection.cursor() as cursor:
        sql=f"update alluser set password={thisuser.password} where phone_number={thisuser.phone_number}"
        cursor.execute(sql)
        return {"state": 200, "message": "成功修改。"}

async def reg(thisuser:user):
    with connection.cursor() as cursor:
        sql = f"SELECT * FROM alluser where phone_number={thisuser.phone_number}"
        cursor.execute(sql)
        user_a = cursor.fetchall()
        if len(user_a) != 0:
            return {"state": 400, "message": "您已经注册账号。"}
        sql=f"insert into alluser(phone_number,password) values({thisuser.phone_number},{thisuser.password})"
        cursor.execute(sql)
        return {"state": 200, "message": "成功注册账号。"}