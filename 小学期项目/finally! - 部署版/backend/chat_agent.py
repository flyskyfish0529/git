import configparser
import json
import os

import pymysql
from sqlalchemy import create_engine
import openai
from dotenv import load_dotenv
from langchain.agents import AgentType, AgentExecutor
from langchain.agents import initialize_agent, Tool
from langchain_community.agent_toolkits import create_sql_agent
from langchain_community.chat_models import ChatZhipuAI
from langchain_community.utilities import SQLDatabase, SerpAPIWrapper

import math
from langchain_openai import ChatOpenAI
from openai import OpenAI
from pydantic import SecretStr
import re
import json
from collections import defaultdict
from collections import defaultdict
from decimal import Decimal


# 加载环境变量
load_dotenv()

# 读取配置文件
config = configparser.ConfigParser()
config.read('config.ini')
frontward = config['IP']['frontward']  # 前端地址

# 加载数据库连接字段
user = config['database'].get('user')
password = config['database'].get('password')  # 默认空密码
host = config['database'].get('host')
port = config['database'].get('port', '3306')  # 默认端口 3306
database_college = config['database'].get('database_college')
auth_part = f"{user}:{password}" if password else user

# 数据库连接字符串
db_configs = f"mysql+pymysql://{auth_part}@{host}:{port}/{database_college}"

# 批量创建 SQLDatabase 实例
db = SQLDatabase.from_uri(database_uri=db_configs, sample_rows_in_table_info=3)

result_json = {}
secondary_llm = OpenAI(
    api_key=os.environ['ZHIPU_API_KEY'],
    base_url=os.environ['ZHIPU_BASE_URL'],
)

def group_by_school_min_score_sum_enroll(results):
    """
    results: List[Tuple]，每个元组格式为
    (院校名称, 专业名称, 招生人数, 平均分, ...)
    返回：List[Dict]，每个dict包含院校名称、总招生人数、最低平均分
    """
    school_data = defaultdict(lambda: {'招生人数': 0, '平均分':0})

    for row in results:
        school = row[0]
        enroll = int(row[2])
        avg_score = float(row[3])
        school_data[school]['招生人数'] += enroll
        if school_data[school]['平均分'] is None or avg_score >= school_data[school]['平均分']:
            school_data[school]['平均分'] = avg_score

    grouped = []
    for school, data in school_data.items():
        grouped.append({
            '院校名称': school,
            '总招生人数': data['招生人数'],
            '平均分': data['平均分']
        })
    return grouped

def split_to_chong_wen_bao(grouped_results, score):
    """
    grouped_results: List[Dict]，每个dict包含'院校名称'、'总招生人数'、'平均分'
    score: float，考生分数
    返回：冲、稳、保三组列表
    """
    chong, wen, bao = [], [], []
    for item in grouped_results:
        avg = item['平均分']
        if avg > score:
            chong.append(item)
        elif score - 10 <= avg <= score:
            wen.append(item)
        else:
            bao.append(item)
    return chong, wen, bao

def ask_llm(message):
    return secondary_llm.chat.completions.create(
        messages=[{"role": "user", "content": message}],
        model='glm-4',
        temperature=1
    ).choices[0].message.content


def calc_prob(item, score, mode):
    avg = item['平均分']
    enroll = item['总招生人数']
    enroll = max(enroll, 1)  # 防止log(0)
    if mode == 'chong':
        prob = 40 - (avg - score) * 4 + math.log(enroll) * 2
        prob = max(prob, 20)
    elif mode == 'wen':
        prob = 60 + (score - avg) * 4 + math.log(enroll) * 2
        prob = min(prob, 90)
    else:  # bao
        prob = 90 + (score - avg) * 0.5 + math.log(enroll) * 1
        prob = min(prob, 99)
    return round(prob, 1)

def extract_pure_sql(text):
    """
    提取字符串中的纯SQL语句，去除markdown代码块和解释性文字。
    """
    # 先去除markdown代码块标记
    text = re.sub(r"```sql|```", "", text, flags=re.IGNORECASE).strip()
    # 尝试提取以WITH/SELECT/INSERT/UPDATE/DELETE等SQL关键字开头的部分
    sql_match = re.search(r"(WITH|SELECT|INSERT|UPDATE|DELETE)[\s\S]+", text, re.IGNORECASE)
    if sql_match:
        return sql_match.group(0).strip()
    return text  # 如果没有匹配到，返回原始内容



def fix_sql_parentheses(sql: str) -> str:
    """
    自动修正SQL语句中加权得分表达式括号不匹配的问题
    """
    # 匹配加权得分表达式（WHERE和SELECT里的）
    pattern = re.compile(r'(\(?0\.3\s.*?)(?=AS|>=)', re.DOTALL)

    def fix_expr(m):
        # 统计左右括号数量
        expr = m.group(1)
        left = expr.count('(')
        right = expr.count(')')
        # 如果左括号多，补齐右括号
        if left > right:
            expr += ')' * (left - right)
        return expr

    # 替换所有加权得分表达式
    fixed_sql = pattern.sub(lambda m: fix_expr(m), sql)
    return fixed_sql


class DeepSeekChatService:
    def __init__(self):
        try:

            # 创建大模型
            self.llm = ChatOpenAI(
                model="deepseek-chat",
                base_url=os.environ['DEEPSEEK_BASE_URL'],
                api_key=SecretStr(os.environ['DEEPSEEK_API_KEY']),
                temperature=0.5
            )

            # 创建 agent
            self.agents = create_sql_agent(
                llm=self.llm,
                db=db,
                agent_type="openai-tools",
                verbose=False
            )

            # 创建数据库工具
            self.db_tools = [
                Tool(
                    name="CollegeDB",
                    func=self.agents.run,
                    description="查询全国学校招生计划信息(包括院校所在地、院校专业组代码、院校名称、专业名称、计划数、收费标准等)（表tianjin_enrollment_plan）、"
                                "招生分数线(包含院校专业组代码、该专业组代码所需要的最低分等信息，只有分数信息没有其他信息，如所在城市等请去其他表查询)(表tianjin_college_admission)、"
                                "学科评估结果(包含类别、学科、校名、评选结果等)(表subject_assessment)、"
                                "学校排名(包含排名、院校、省份、类型、得分)(表common_ranking)"
                    "执行SQL查询获取高校信息。必须遵循以下规则："
                    "所有数据必须来自这些表，禁止使用其他来源"
                    "查询结果必须去重，特别是学校名称"
                    "分数信息必须来自 tianjin_college_admission 表"
                )]

            # 移除搜索工具，避免从外部获取数据
            # self.search_tool = [Tool(
            #     name="SerpAPI",
            #     func=self.search.run,
            #     description="使用 SerpAPI 搜索互联网信息"
            # )]

            # 创建大模型对话工具
            self.llm_tool = [
                Tool(
                    name="ClaudeExpert",
                    func=ask_llm,
                    description="调用 glm-4 回答复杂问题或需要大模型分析的任务",
                )
            ]

            # 创建数学计算工具
            from langchain_community.agent_toolkits.load_tools import load_tools
            self.math_tool = load_tools(
                tool_names=["llm-math"],
                llm=self.llm
            )

            # 合成大工具
            self.all_tools = self.db_tools+self.math_tool+ self.llm_tool # 只使用数据库工具

            # 创建agent_executor
            self.agent_executor = initialize_agent(
                self.all_tools,
                self.llm,
                agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
                verbose=False,  # 关闭详细日志
                streaming=False,
                handle_parsing_errors=True,
                max_iterations=15,  # 增加迭代次数
                return_intermediate_steps=False,
                agent_kwargs={
                    "system_message": """你是一个严格的数据库查询助手。必须遵守以下规则：
            1. 按照用户需求，提供的SQL查询语句。
            2. 只给出sql语句，禁止添加任何解释性文字"""
                      }
                        )
        except Exception as e:
                raise e

    async def get_sql(self, message: str)->str:
        # 直接执行，不使用流式输出
        result = await self.agent_executor.ainvoke({"input": message})
        # 提取输出内容
        if isinstance(result, dict):
            output = result.get("output", "")
        else:
            output = str(result)
        output=extract_pure_sql(output)
        print(output)
        return output

    async def chat(self,message:str,score):
        sql=await self.get_sql(message=message)
        db_config = {
            'host': config['database']['host'],
            'database': config['database']['database_college'],
            'user': config['database']['user'],
            'password': config['database']['password'],
            'charset': 'utf8mb4'
        }
        connection = pymysql.connect(**db_config)
        with connection.cursor() as cursor:
            fix=fix_sql_parentheses(sql)
            print(fix)
            cursor.execute(fix)
            results = cursor.fetchall()
            grouped_results = group_by_school_min_score_sum_enroll(results)
            chong, wen, bao = split_to_chong_wen_bao(grouped_results, score)
            # 3. 输出结果
            # 只保留每档前5个
            chong_top5 = chong[:5]
            wen_top5 = wen[:5]
            bao_top5 = bao[:5]

            # 计算录取概率并添加到每个院校
            for item in chong_top5:
                item['录取概率'] = f"{calc_prob(item, score, 'chong')}%"
            for item in wen_top5:
                item['录取概率'] = f"{calc_prob(item, score, 'wen')}%"
            for item in bao_top5:
                item['录取概率'] = f"{calc_prob(item, score, 'bao')}%"

            global result_json
            result_json = {
                "冲一冲": chong_top5,
                "稳一稳": wen_top5,
                "保一保": bao_top5
            }
            return json.dumps(result_json, ensure_ascii=False, indent=2)

async def get():
    return json.dumps(result_json, ensure_ascii=False, indent=2)