from typing import List, Dict, Any, Tuple, Optional
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain.agents import AgentExecutor, create_react_agent
from langchain.tools import Tool
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from pydantic import SecretStr
import os
from collections import defaultdict
import json
from dotenv import load_dotenv
import jieba  # 中文分词库

# 加载环境变量
load_dotenv()

# 配置DeepSeek模型
chat_model_deepseek = ChatOpenAI(
    model="deepseek-chat",
    base_url=os.environ["OPENAI_DEEPSEEK_BASE_URL_FREE"],
    api_key=SecretStr(os.environ["OPENAI_DEEPSEEK_APIKEY_FREE"]),
    temperature=0.3
)


# --- 数据模型定义 ---
class UserInput(BaseModel):
    raw_query: str = Field(description="原始用户输入")
    normalized_query: str = Field(description="标准化后的查询")
    matched_keywords: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="匹配到的关键词映射"
    )


class MajorAnalysisResult(BaseModel):
    matched_majors: List[str] = Field(description="匹配到的具体专业名称")
    matched_categories: List[str] = Field(description="匹配到的专业门类")
    related_entities: List[Dict[str, Any]] = Field(description="相关实体和关系")
    keyword_mapping: Dict[str, str] = Field(
        default_factory=dict,
        description="关键词替换记录"
    )


# --- 知识图谱工具 ---
class KnowledgeGraphTool:
    def __init__(self, kg_data: List[Tuple[str, str, str, str]]):
        self.kg_data = kg_data
        self._build_indexes()
        self._build_keyword_mappings()

        # 初始化jieba分词
        self._init_jieba()

    def _init_jieba(self):
        """初始化分词词典"""
        for entity in self.entity_attrs:
            jieba.add_word(entity)
            jieba.add_word(entity.split(" ")[0])  # 添加专业名称首词

    def _build_indexes(self):
        """建立实体和关系的索引"""
        self.entity_attrs = defaultdict(dict)
        self.entity_types = defaultdict(list)
        self.relations = defaultdict(list)

        for item in self.kg_data:
            if len(item) < 4:
                continue

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
                self.relations[obj].append(relation)

    def _build_keyword_mappings(self):
        """构建关键词映射表"""
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
            "AI": "人工智能",
            "CS": "计算机科学与技术",
            "大数据": "数据科学与大数据技术",

            # 从知识图谱中提取所有专业和门类
            **{entity: entity for entity in self.entity_attrs}
        }

        # 添加反向映射
        self.keyword_map.update({
            v.split()[0]: v for v in self.entity_attrs
            if " " in v and v.split()[0] not in self.keyword_map
        })

    def normalize_keywords(self, text: str) -> UserInput:
        """执行关键词标准化"""
        # 分词处理
        words = [w for w in jieba.lcut(text) if w.strip()]

        mapping_record = {}
        matched_keywords = {"majors": [], "categories": []}
        normalized_words = []

        for word in words:
            original = word
            # 精确匹配优先
            if word in self.keyword_map:
                word = self.keyword_map[word]
            else:
                # 模糊匹配
                for k, v in self.keyword_map.items():
                    if k in word and k != word:
                        word = word.replace(k, v)
                        break

            if original != word:
                mapping_record[original] = word

                # 记录匹配到的专业/门类
                if word in self.entity_attrs:
                    if "专业名称" in self.entity_types[word]:
                        matched_keywords["majors"].append(word)
                    elif "专业类" in self.entity_types[word]:
                        matched_keywords["categories"].append(word)

            normalized_words.append(word)

        return UserInput(
            raw_query=" ".join(words),
            normalized_query=" ".join(normalized_words),
            matched_keywords=matched_keywords
        )

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


# --- 专业分析Agent ---
class MajorAnalysisAgent:
    def __init__(self, kg_tool: KnowledgeGraphTool, llm=chat_model_deepseek):
        self.kg_tool = kg_tool
        self.llm = llm

        self.tools = [
            Tool(
                name="query_knowledge_graph",
                func=self.query_knowledge_graph,
                description="参数格式: {{\"majors\": [\"专业1\"], \"categories\": [\"门类1\"]}}"
            ),
            Tool(
                name="find_related_majors",
                func=self.find_related_majors,
                description="参数格式: {{\"category\": \"门类名称\"}}"
            )
        ]
        # 优化后的提示模板
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", f"""请严格按以下规则执行：

            1. 可用工具列表:
            {{tools}}
            
            2. 工具名称 (必须选择以下之一):
            {{tool_names}}
            
            3. 响应格式:
            Thought: 分析思考过程
            Action: 工具名
            Action Input: JSON格式参数
            Observation: 结果
            ... (可重复多次)
            Final Answer: 最终答案
            
            4. 当前任务:
            {{input}}
            
            5. 思考过程记录:
            {{agent_scratchpad}}

            注意：
            - Action Input必须是严格JSON格式
            - 不要添加任何额外解释"""), ("user", "{input}")
        ])



        self.agent_executor = AgentExecutor(
            agent=create_react_agent(llm=self.llm, tools=self.tools, prompt=self.prompt),
            tools=self.tools,
            handle_parsing_errors=True,
            max_iterations=3,
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

    def _get_keyword_help_text(self):
        """生成关键词帮助文本"""
        return "\n".join(
            f"- {k} → {v}"
            for k, v in sorted(self.kg_tool.keyword_map.items())
            if k != v
        )

    def analyze(self, user_input: UserInput) -> MajorAnalysisResult:
        """执行分析"""
        try:
            # 执行Agent分析
            agent_response = self.agent_executor.invoke({
                "input": f"已标准化输入: {user_input.normalized_query}"
            })

            # 解析结果
            majors = user_input.matched_keywords.get("majors", [])
            categories = user_input.matched_keywords.get("categories", [])

            # 从Agent输出中提取更多专业/门类
            if "专业:" in agent_response["output"]:
                majors.extend([
                    m.strip() for m in
                    agent_response["output"].split("专业:")[1].split("门类:")[0].split(",")
                ])

            if "门类:" in agent_response["output"]:
                categories.extend([
                    c.strip() for c in
                    agent_response["output"].split("门类:")[1].split(",")
                ])

            # 查询知识图谱
            related_entities = self.kg_tool.query_kg(
                list(set(majors)),
                list(set(categories))
            )

            return MajorAnalysisResult(
                matched_majors=majors,
                matched_categories=categories,
                related_entities=related_entities,
                keyword_mapping={
                    k: v for k, v in zip(
                        user_input.raw_query.split(),
                        user_input.normalized_query.split()
                    ) if k != v
                }
            )

        except Exception as e:
            print(f"分析出错: {str(e)}")
            return self._fallback_search(user_input)

    def _fallback_search(self, user_input: UserInput) -> MajorAnalysisResult:
        """降级搜索方案"""
        majors = user_input.matched_keywords.get("majors", [])
        categories = user_input.matched_keywords.get("categories", [])

        return MajorAnalysisResult(
            matched_majors=majors,
            matched_categories=categories,
            related_entities=self.kg_tool.query_kg(majors, categories),
            keyword_mapping={
                k: v for k, v in zip(
                    user_input.raw_query.split(),
                    user_input.normalized_query.split()
                ) if k != v
            }
        )


# --- 主流程 ---
def create_major_analysis_chain(kg_data: List[Tuple[str, str, str, str]]):
    """创建处理链"""
    kg_tool = KnowledgeGraphTool(kg_data)
    analysis_agent = MajorAnalysisAgent(kg_tool)

    return (
            RunnablePassthrough()
            | RunnableLambda(lambda x: {
        "user_query": x["user_query"],
        "normalized": kg_tool.normalize_keywords(x["user_query"])
    })
            | RunnableLambda(lambda x: analysis_agent.analyze(x["normalized"]))
    )


# --- 示例使用 ---
if __name__ == "__main__":
    # 示例知识图谱数据
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

    # 创建处理链
    chain = create_major_analysis_chain(kg_data)

    # 测试用例
    test_cases = [
        #"我想了解计科和经济",
        "对工科和AI感兴趣",
        #"哲学类和国贸哪个好",
        #"大数据专业就业前景"
    ]

    for query in test_cases:
        print(f"\n输入: {query}")
        result = chain.invoke({"user_query": query})

        print(f"标准化后: {result.keyword_mapping}")
        print(f"匹配专业: {result.matched_majors}")
        print(f"匹配门类: {result.matched_categories}")
        print(f"相关实体: {result.related_entities}")