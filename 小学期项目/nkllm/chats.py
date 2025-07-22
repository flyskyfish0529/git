import os

from dotenv import load_dotenv
from openai import OpenAI
load_dotenv()

client = OpenAI(api_key=os.environ['DEEPSEEK_API_KEY'], base_url="https://api.deepseek.com")

messages=[
        {"role": "system", "content": "你是一个严格遵循规则的高考志愿推荐专家。"},
    ]


async def chat(question):
    messages.append({"role": "user", "content":question})

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=messages,
        stream = False
    ).choices[0].message.content
    messages.append({"role": "assistance", "content": response})
    return (response.choices[0].message.content)