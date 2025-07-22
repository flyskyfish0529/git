from typing import List, Dict, Any, Tuple
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain.agents import AgentExecutor, create_react_agent
from langchain.tools import Tool
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_openai import ChatOpenAI
from pydantic import SecretStr
import os
import json
from collections import defaultdict
from dotenv import load_dotenv

load_dotenv()

# 配置DeepSeek Chat模型
chat_model_deepseek = ChatOpenAI(
    model="deepseek-chat",
    base_url=os.environ["OPENAI_DEEPSEEK_BASE_URL_FREE"],
    api_key=SecretStr(os.environ["OPENAI_DEEPSEEK_APIKEY_FREE"]),
    temperature = 0.6
)


# 定义输入模型
class UserInput(BaseModel):
    user_query: str = Field(description="用户输入的意向专业或职业规划方向")


# 定义输出模型
class MajorAnalysisResult(BaseModel):
    matched_majors: List[str] = Field(description="匹配到的具体专业名称")
    matched_categories: List[str] = Field(description="匹配到的专业门类")
    related_entities: List[Dict[str, Any]] = Field(description="相关实体和关系")


# 知识图谱查询工具（适配三元组格式）
class KnowledgeGraphTool:
    def __init__(self, kg_data: List[Tuple[str, str, str, str]]):
        """
        初始化知识图谱工具

        参数:
            kg_data: 知识图谱数据，格式为(类型, 主体, 谓词, 客体)的四元组列表
            示例: ("实体", "哲学", "学位授予门类", "包含哲学类专业")
        """
        self.kg_data = kg_data
        self._build_indexes()

    def _build_keyword_map(self):
        """建立关键词到标准名称的映射表"""
        self.keyword_map = {
            # 通用简称映射
            "计算机": "计算机科学与技术",
            "计科": "计算机科学与技术",
            "计算机科学": "计算机科学与技术",
            "经济": "经济学",
            "金融": "金融学",
            "国贸": "国际经济与贸易",
            "哲学类": "哲学类",
            "工科": "工学类",
            "理科": "理学类",

            # 从知识图谱中提取所有专业和门类作为标准名称
            **{entity: entity for entity in self.entity_attrs}
        }

    def _build_indexes(self):
        """建立实体和关系的索引"""
        # 实体属性索引 {实体名称: {属性名: 属性值}}
        self.entity_attrs = defaultdict(dict)

        # 实体类型索引 {实体名称: [实体类型]}
        self.entity_types = defaultdict(list)

        # 关系索引 {实体名称: [关系列表]}
        self.relations = defaultdict(list)

        for item in self.kg_data:
            if len(item) < 4:
                continue  # 跳过不完整的三元组

            item_type, subject, predicate, obj = item

            if item_type == "实体":
                self.entity_attrs[subject][predicate] = obj
                self.entity_types[subject].append(predicate)
            elif item_type == "实体关系":
                relation = {
                    "subject": subject,
                    "relation": predicate,
                    "object": obj
                }
                self.relations[subject].append(relation)
                # 双向索引，方便反向查询
                self.relations[obj].append(relation)

    def query_kg(self, majors: List[str], categories: List[str]) -> List[Dict[str, Any]]:
        """
        从知识图谱中查询相关实体和关系

        参数:
            majors: 专业名称列表，如 ["哲学", "逻辑学"]
            categories: 专业门类列表，如 ["哲学类"]

        返回:
            [{
                "entity": {实体信息},
                "relations": [相关关系]
            }]
        """
        results = []

        # 查询具体专业
        for major in majors:
            if major in self.entity_attrs:
                # 获取所有属性
                attrs = {"name": major, **self.entity_attrs[major]}
                # 获取所有关系（去重）
                relations = list({
                                     tuple(sorted((rel["subject"], rel["relation"], rel["object"]))): rel
                                     for rel in self.relations.get(major, [])
                                 }.values())
                results.append({
                    "entity": attrs,
                    "relations": relations
                })

        # 查询专业门类
        for category in categories:
            if category in self.entity_attrs:
                # 获取所有属性
                attrs = {"name": category, **self.entity_attrs[category]}
                # 获取所有关系（去重）
                relations = list({
                                     tuple(sorted((rel["subject"], rel["relation"], rel["object"]))): rel
                                     for rel in self.relations.get(category, [])
                                 }.values())
                results.append({
                    "entity": attrs,
                    "relations": relations
                })

        return results

    def find_related_majors(self, category: str) -> List[Dict[str, Any]]:
        """
        查找属于某个门类的所有专业

        参数:
            category: 专业门类名称，如 "哲学类"

        返回:
            [{
                "major": 专业名称,
                "attrs": 专业属性,
                "relations": 与门类的关系
            }]
        """
        related = []
        for rel in self.relations.get(category, []):
            if rel["relation"] == "包含" and rel["subject"] == category:
                major = rel["object"]
                if "专业名称" in self.entity_types.get(major, []):
                    related.append({
                        "major": major,
                        "attrs": self.entity_attrs.get(major, {}),
                        "relations": [rel]
                    })
        return related


# 专业分析Agent
class MajorAnalysisAgent:
    def __init__(self, kg_tool, llm=chat_model_deepseek):
        self.kg_tool = kg_tool
        self.llm = llm

        # 定义Agent提示词
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一个大学志愿填报助手，负责分析用户的专业意向。
            用户会提供他们的意向专业或职业规划方向，你需要识别出相关的具体专业名称和专业门类。

            已知的专业门类包括但不限于:
            - 哲学类
            - 经济学类
            - 法学类
            - 教育学类
            - 文学类
            - 历史学类
            - 理学类(数学类、物理学类、化学类等)
            - 工学类(计算机类、机械类、土木类等)
            - 农学类
            - 医学类
            - 管理学类
            - 艺术学类

            你必须严格按以下格式响应，不要添加任何解释或注释：

            工具列表:
            {tools}
            
            响应格式:
            Thought: 分析思考过程
            Action: 工具名 (只能是: {tool_names})
            Action Input: {{"参数名":"参数值"}}
            Observation: 工具返回结果
            ... (可重复多次)
            Final Answer: 最终答案
            
            请仔细分析用户的输入：{input}
            请仔细分析用户的输入，识别出所有相关的具体专业名称和专业门类。"""),
            ("user", "{input}")
        ])

        # 定义工具
        self.tools = [
            Tool(
                name="query_knowledge_graph",
                func=self.query_knowledge_graph,
                description="必须传入JSON格式参数，如: {{\"majors\": [\"哲学\"], \"categories\": [\"哲学类\"]}}"
            ),
            Tool(
                name="find_related_majors",
                func=self.find_related_majors,
                description="必须传入JSON格式参数，如: {{\"category\": \"哲学类\"}}"
            )
        ]

        # 创建Agent
        self.agent = create_react_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=self.prompt
        )

        self.agent_executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            handle_parsing_errors=True,  # 添加此参数
            verbose=True
        )

    def query_knowledge_graph(self, majors: List[str], categories: List[str]) -> str:
        """查询知识图谱的包装方法"""
        results = self.kg_tool.query_kg(majors, categories)
        return str(results)

    def find_related_majors(self, category: str) -> str:
        """查找门类包含专业的包装方法"""
        results = self.kg_tool.find_related_majors(category)
        return str(results)

    def analyze(self, user_input: str) -> MajorAnalysisResult:
        """分析用户输入并返回结果"""
        try:
            # 第一步：尝试通过Agent获取结构化结果
            agent_response = self.agent_executor.invoke(
                {"input": f"分析专业方向: {user_input}"}
            )

            # 从中间步骤提取参数
            majors = set()
            categories = set()

            for step in agent_response['intermediate_steps']:
                action, _ = step
                try:
                    params = json.loads(action.tool_input)
                    if action.tool == "query_knowledge_graph":
                        majors.update(params.get("majors", []))
                        categories.update(params.get("categories", []))
                    elif action.tool == "find_related_majors":
                        categories.add(params["category"])
                except:
                    continue

            # 第二步：如果Agent失败，使用降级方案
            if not majors and not categories:
                return self._fallback_search(user_input)

            # 查询知识图谱
            related_entities = self.kg_tool.query_kg(list(majors), list(categories))
            return MajorAnalysisResult(
                matched_majors=list(majors),
                matched_categories=list(categories),
                related_entities=related_entities
            )

        except Exception as e:
            print(f"分析出错: {str(e)}")
            return self._fallback_search(user_input)

    def _fallback_search(self, query: str) -> MajorAnalysisResult:
        """降级搜索方案"""
        keywords = ["计算机", "经济", "哲学"]  # 可根据实际需求扩展
        majors = []
        categories = []

        # 简单关键词匹配
        for entity in self.kg_tool.entity_attrs:
            if any(kw in entity for kw in keywords):
                if "专业名称" in self.kg_tool.entity_types[entity]:
                    majors.append(entity)
                elif "专业类" in self.kg_tool.entity_types[entity]:
                    categories.append(entity)

        return MajorAnalysisResult(
            matched_majors=majors,
            matched_categories=categories,
            related_entities=self.kg_tool.query_kg(majors, categories)
        )


# 构建完整的Chain
def create_major_analysis_chain(kg_data, llm=chat_model_deepseek):
    # 初始化知识图谱工具
    kg_tool = KnowledgeGraphTool(kg_data)

    # 初始化专业分析Agent
    analysis_agent = MajorAnalysisAgent(kg_tool, llm)

    # 定义处理链
    chain = (
            RunnablePassthrough()
            | RunnableLambda(lambda x: analysis_agent.analyze(x["user_query"]))
    )

    return chain


# 示例使用
if __name__ == "__main__":

    # 示例知识图谱数据（三元组格式）
    kg_data = []
    with open(r"D:\大二下\企业实习实训\workspace\0715\output\output_all.txt", "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or not line.startswith("("):
                continue
            # 去掉括号和分号，分割为元组
            line = line.strip("()")
            parts = [p.strip() for p in line.split(";")]
            kg_data.append(tuple(parts))

    # 创建Chain (使用DeepSeek模型)
    analysis_chain = create_major_analysis_chain(kg_data)

    # 模拟用户输入
    user_input = {"user_query": "我对计算机科学和经济学感兴趣"}

    # 执行Chain
    result = analysis_chain.invoke(user_input)
    print("查询结果:", result)