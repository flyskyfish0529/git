import configparser
import json
import os

import openai
from dotenv import load_dotenv
from langchain.agents import AgentType, AgentExecutor
from langchain.agents import initialize_agent, Tool
from langchain_community.agent_toolkits import create_sql_agent
from langchain_community.chat_models import ChatZhipuAI
from langchain_community.utilities import SQLDatabase, SerpAPIWrapper

from langchain_openai import ChatOpenAI
from openai import OpenAI
from pydantic import SecretStr
import re
import json

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

secondary_llm = OpenAI(
    api_key=os.environ['ZHIPU_API_KEY'],
    base_url=os.environ['ZHIPU_BASE_URL'],
)


def ask_llm(message):
    return secondary_llm.chat.completions.create(
        messages=[{"role": "user", "content": message}],
        model='glm-4',
        temperature=1
    ).choices[0].message.content


def extract_json(text):
    # 去除 markdown 代码块标记
    text = re.sub(r"```json|```", "", text, flags=re.IGNORECASE).strip()

    # 尝试查找JSON对象
    json_match = re.search(r'\{.*\}', text, re.DOTALL)
    if json_match:
        json_str = json_match.group(0)
        try:
            # 处理转义字符
            json_str = json_str.replace('\\n', '\n').replace('\\t', '\t')
            return json.loads(json_str)
        except Exception as e:
            print(f"extract_json 解析失败: {e}")
            return text

    # 如果没有找到JSON对象，直接返回原始文本
    return text


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
            # 使用传统的AgentExecutor，避免PlanAndExecute的验证错误
            self.agent_executor = initialize_agent(
                self.all_tools,
                self.llm,
                agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
                verbose=True,  # 开启详细日志，便于调试
                streaming=False,  # 关闭流式输出
                handle_parsing_errors=True,
                max_iterations=10,  # 减少迭代次数，避免重复查询
                return_intermediate_steps=False,  # 只返回最终结果
                agent_kwargs={
                    "system_message": """你是一个严格的数据库查询助手。你必须：
1. 只使用SQL查询获取数据
2. 确保学校名称不重复
3. 所有分数必须来自数据库

5. 禁止添加任何解释性文字
6. 如果无法满足以上要求，立即停止并报告错误"""
                }
            )
        except Exception as e:
            raise e

    async def chat(self, message: str):
        # 直接执行，不使用流式输出
        result = await self.agent_executor.ainvoke({"input": message})
        # 提取输出内容
        if isinstance(result, dict):
            output = result.get("output", "")
        else:
            output = str(result)
        print(f"Agent执行结果: {output}")
        json = {"output": output}
        return json

