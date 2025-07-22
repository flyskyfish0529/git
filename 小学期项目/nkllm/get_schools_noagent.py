from dotenv import load_dotenv
from pydantic import BaseModel

import MBTIseek
import chatwithDS

load_dotenv()


# 初始化服务
chat_service = chatwithDS.DeepSeekChatService()

live_city=""
score=0.0
rank=0
want_major=""
hobby=""
MBTI=""
career=MBTIseek.CareerRecommender()
MBTI_career="恭喜，您的性格适合所有工作，请尽情选专业吧！"
strategy=""
subjects=""
future_goal=""
unwant_major=""

def change_MBTI():
    global MBTI_career
    MBTI_career=career.get_career_recommendation_prepared(MBTI)

class InputMessage(BaseModel):
    score: str
    live_city: str
    rank:str
    want_major: str
    unwant_major: str
    hobby: str
    future_goal:str
    strategy: str
    subjects: str





async def student(input: InputMessage):
    global live_city, score, rank, want_major, hobby, strategy, subjects
    live_city = input.live_city
    score = float(input.score)
    rank = int(input.rank)
    want_major = input.want_major
    hobby = input.hobby
    strategy = input.strategy
    subjects = input.subjects
    unwant_major = input.unwant_major
    future_goal = input.future_goal
    return {
        "status": "success",
        "message": "学生信息已更新",
        "data": {
            "live_city": live_city,
            "score": score,
            "rank": rank,
            "want_major": want_major,
            "unwant_major": unwant_major,
            "hobby": hobby,
            "future_goal": future_goal,
            "strategy": strategy,
            "subjects": subjects
        }
    }

def seek(mbti_type):
    global MBTI
    MBTI = mbti_type
    change_MBTI()
    print(MBTI)
    return {
        "status": "success",
        "message": "MBTI类型已更新",
        "MBTI": MBTI,
        "MBTI_career": MBTI_career
    }


async def smart_recommend():
    prompt = (
f"""
请根据天津考生信息（严格使用2023年真实数据）：
- 分数：{score}（2023年天津高考）
- 排名：{rank}
- 专业：{want_major}（请注意，不是说想学医就必须去医科大学，其他有医学专业的学校也要纳入考虑范围，其他学科同理。）
- 选科：{subjects}
- 策略：{strategy}

【强制要求】
1. 仅使用2023年天津教育考试院公布的投档线（如北大医学部口腔：698分）。
2. 按此规则计算院校推荐：
   - 冲：{score} ≤ 院校线 ≤ {score+10}
   - 稳：{score-10} ≤ 院校线 ≤ {score}
   - 保：院校线 ≤ {score-10}
3. 每组院校必须为10所
4.同一院校名必须只能出现一次!!!!!!!!!!!!!!。

【输出格式】
冲一冲：
(学校1, 分数1, 概率40±5%)
...
稳一稳：
(学校1, 分数1, 概率65±5%)
...
保一保：
(学校1, 分数1, 概率85±5%)

不要输出其他任何文字。"""
    )
    result = await chat_service.chat(prompt)
    return result

