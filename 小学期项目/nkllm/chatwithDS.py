import configparser
import os

from dotenv import load_dotenv
from openai import OpenAI

# 加载环境变量
load_dotenv()

# 读取配置文件
config = configparser.ConfigParser()
config.read('config.ini')
frontward = config['IP']['frontward']  # 前端地址


llm = OpenAI(
                base_url=os.environ['DEEPSEEK_BASE_URL'],
                api_key=os.environ['DEEPSEEK_API_KEY'],
)


class DeepSeekChatService:
    async def chat(self, message: str):
        output = llm.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content":
                    "你是一个严格遵循规则的高考志愿推荐专家。"
                        "必须按以下规则执行："
                        "1. 仅输出冲/稳/保三组院校，每组必须严格为10所，不满足则从下面一档提上来。格式严格为：(学校, 分数, 概率%)"
                        "2. 所有数据必须真实，禁止虚构"
                        "3. 同一院校只能出现一次"},
                {"role": "user", "content": message},
            ],
            temperature=0
        ).choices[0].message.content
        print(output)
        return {"output": output}

