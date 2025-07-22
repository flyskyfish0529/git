from dotenv import load_dotenv
from pydantic import BaseModel
import MBTIseek
import chat_agent

load_dotenv()

chat_service = chat_agent.DeepSeekChatService()

live_city = ""
score = 0.0
rank = 0
want_major = ""
hobby = ""
MBTI = ""
career = MBTIseek.CareerRecommender()
MBTI_career = ""
strategy = ""
subjects = ""
future_goal = ""
unwant_major = ""

def change_MBTI():
    global MBTI_career
    MBTI_career = career.get_career_recommendation_prepared(MBTI)

class InputMessage(BaseModel):
    score: str
    live_city: str
    rank: str
    want_major: str
    unwant_major: str
    hobby: str
    future_goal: str
    strategy: str
    subjects: str

async def student(input: InputMessage):
    global live_city, score, rank, want_major, hobby, strategy, subjects, unwant_major, future_goal
    live_city = input.live_city
    score = float(input.score)
    rank = int(input.rank)
    want_major = input.want_major
    hobby = input.hobby
    strategy = input.strategy
    subjects = input.subjects
    unwant_major = input.unwant_major
    future_goal = input.future_goal
    return {"status": "success", "message": "学生信息已更新", "data": input.dict()}

def seek(mbti_type):
    global MBTI
    MBTI = mbti_type
    change_MBTI()
    return {"status": "success", "message": "MBTI类型已更新", "MBTI": MBTI, "MBTI_career": MBTI_career}

async def smart_recommend():
        prompt = f"""
    请严格按照以下步骤执行高校推荐：

    1. 执行SQL查询获取基础数据：
    请根据以下要求编写一个SQL语句并查询：
            
                1. 核心比较参数：
                - 考生分数：{score}（需与院校平均分比较）
                - 意向专业：{want_major or '不限'}（用于专业筛选）
                
                2. 参数使用要求：
                ```sql
                -- 分数比较示例：
                (1-ABS(平均分-{score})/50)  -- 计算分数匹配度
                
                -- 专业筛选示例：
                {f"AND e.专业名称 LIKE '%{want_major}%'" if want_major else ""}
                {f"AND s.学科 LIKE '%{want_major}%'" if want_major else ""}
                参数验证规则：
                
                分数({score})必须是50-750之间的数字
                
                专业({want_major})应进行SQL注入过滤
                
                空专业参数时应查询所有专业
                
                - 主要表：tianjin_enrollment_plan（别名e）
                - 关联表：tianjin_college_admission（别名a）、subject_assessment（别名s）、common_ranking（别名r）
                
                3. 查询字段：
                - 院校名称（来自e表）
                - 专业名称（来自e表）
                - 计划数（去除逗号后转换为数字，命名为招生人数）
                - 总成绩的平均值（命名为平均分）
                - 学科评估的最高结果（命名为学科评估）
                - 学校排名的最小值（命名为学校排名）
                
                4. 关联条件：
                - e.院校名称 = a.院校名称
                - e.院校名称 = s.校名（可选学科筛选）
                - e.院校名称 = r.院校
                
                5. 筛选条件：
                - 计划数 > 0（需先去除逗号）
                - 可选的专业名称筛选
                
                6. 排序规则：
                按以下加权公式降序排序：
                - 分数匹配度（30%权重）：(1-ABS(平均分-考生分数)/50)
                - 学科评估（40%权重）：A+=1.0, A=0.9, A-=0.8, B+=0.7, B=0.6, B-=0.5, 其他=0.3
                - 学校排名（10%权重）：(1-排名/500)
                - 招生规模（20%权重）：LN(招生人数+1)/LN(100)
                
                7. 其他要求：
                - 使用WITH子句创建临时表"基础数据"
                - 处理计划数字段中的逗号分隔
                - 使用中文别名
                - 保留完整的JOIN和LEFT JOIN逻辑
    最后生成的sql语句与这个比较，不对的话以我下面的为准。
    WITH 基础数据 AS (
        SELECT 
            e.院校名称,
            e.专业名称,
            CAST(REPLACE(e.计划数, ',', '') AS UNSIGNED) AS 招生人数,
            AVG(a.总成绩) AS 平均分,
            MAX(s.评选结果) AS 学科评估,
            MIN(r.排名) AS 学校排名
        FROM tianjin_enrollment_plan e
        JOIN tianjin_college_admission a ON e.院校名称 = a.院校名称
        LEFT JOIN subject_assessment s ON e.院校名称 = s.校名
            {f"AND s.学科 LIKE '%{want_major}%'" if want_major else ""}
        LEFT JOIN common_ranking r ON e.院校名称 = r.院校
        WHERE CAST(REPLACE(e.计划数, ',', '') AS UNSIGNED) > 0
        {f"AND e.专业名称 LIKE '%{want_major}%'" if want_major else ""}
        GROUP BY e.院校名称, e.专业名称, e.计划数
    )
    SELECT * FROM 基础数据
    ORDER BY 
        (30*(1-ABS(平均分-{score})/50) +
        (40*CASE 学科评估
            WHEN 'A+' THEN 1.0 WHEN 'A' THEN 0.9 WHEN 'A-' THEN 0.8
            WHEN 'B+' THEN 0.7 WHEN 'B' THEN 0.6 WHEN 'B-' THEN 0.5
            ELSE 0.3 END) +
        (10*(1-学校排名/500)) +
        (20*LN(招生人数+1)/LN(100)) DESC

2. 将结果分为三档（每档严格10所且不重复）：
- 冲：平均分 > {score}+10分（按平均分降序取前10所）
- 稳：{score}-10 ≤ 平均分 ≤ {score}+10分（按平均分降序取接下来的10所）
- 保：平均分 < {score}-10分（按平均分降序取再接下来的10所）

3. 录取概率计算规则：
- 冲（院校分数高于学生分数）：40-(平均分-{score})*4+ln(录取人数)/2，最低10%
- 稳（院校分数略低于学生分数）： 60+（{score}-平均分）*4+ln(录取人数)/2
- 保（院校分数低于学生分数）：80+（{score}-平均分）*0.2+ln(录取人数)/4，最高99%

4. 按录取概率降序排序。

5. 最终输出要求：
冲一冲（10所）：
[按录取概率降序排列，每所院校只出现一次]
1. 院校名称 (平均分, 录取概率%, 招生人数, 学科评估)
...
10. 院校名称 (平均分, 录取概率%, 招生人数, 学科评估)

稳一稳（10所）：
[按录取概率降序排列，不与冲档重复]
1. 院校名称 (平均分, 录取概率%, 招生人数, 学科评估)
...
10. 院校名称 (平均分, 录取概率%, 招生人数, 学科评估)

保一保（10所）：
[按录取概率降序排列，不与前两档重复]
1. 院校名称 (平均分, 录取概率%, 招生人数, 学科评估)
...
10. 院校名称 (平均分, 录取概率%, 招生人数, 学科评估)

严格检查：
1. 确保每所院校只在其中一个档位出现
2. 每个档位严格按录取概率降序排列
3. 概率计算必须精确到小数点后1位
"""

        result = await chat_service.chat(prompt)
        return result

if __name__=="__main__":
    score=650.0
    live_city="天津"
    rank=2561
    want_major="医学"
    strategy="专业优先"
    subjects="物理，化学，生物"
    future_goal="当口腔医生"
    import asyncio

    asyncio.run(smart_recommend())