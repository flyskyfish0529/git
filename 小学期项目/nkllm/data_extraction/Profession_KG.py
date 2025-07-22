import os
import pandas as pd
from langchain.chains.summarize.refine_prompts import prompt_template
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.document_loaders import TextLoader
from langchain_community.document_loaders import Docx2txtLoader
from langchain_community.document_loaders import CSVLoader
from setuptools.command.build_ext import if_dl

# 文档加载 - 支持CSV文件
base_dir = "documents"
documents = []

for file in os.listdir(base_dir):
    file_path = os.path.join(base_dir, file)
    if file.endswith(".txt"):
        loader = TextLoader(file_path, encoding="utf-8")
        documents.extend(loader.load())
    elif file.endswith(".pdf"):
        loader = PyPDFLoader(file_path)
        documents.extend(loader.load())
    elif file.endswith(".docx"):
        loader = Docx2txtLoader(file_path)
        documents.extend(loader.load())
    elif file.endswith(".csv"):
        # 使用pandas读取CSV文件
        try:
            df = pd.read_csv(file_path, encoding='utf-8')
            # 将DataFrame转换为文本格式
            csv_text = df.to_string(index=False)
            # 创建Document对象
            from langchain.schema import Document
            doc = Document(page_content=csv_text, metadata={"source": file_path})
            documents.append(doc)
            print(f"成功加载CSV文件: {file}, 包含 {len(df)} 行数据")
        except Exception as e:
            print(f"加载CSV文件 {file} 时出错: {e}")
            # 尝试其他编码
            try:
                df = pd.read_csv(file_path, encoding='gbk')
                csv_text = df.to_string(index=False)
                from langchain.schema import Document
                doc = Document(page_content=csv_text, metadata={"source": file_path})
                documents.append(doc)
                print(f"使用GBK编码成功加载CSV文件: {file}")
            except Exception as e2:
                print(f"使用GBK编码加载CSV文件 {file} 也失败: {e2}")

print(f"总共加载了 {len(documents)} 个文档")

# 3.embedding-model
from langchain.text_splitter import RecursiveCharacterTextSplitter
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=4000,
    chunk_overlap=1000,
    separators=["\n\n", "\n", "  "]
)
chunked_documents = text_splitter.split_documents(documents)

# pip install transformers torch langchain-huggingface sentence-transformers
# 3.2封装
m3e_name = "embedding_models/moka/m3e-base"
bce_name = "embedding_models/netease-youdao"
model_kwarg = {'device': 'cpu'}
# 编码时，完成归一化
encode_kwargs = {'normalize_embeddings': True}
from langchain_huggingface import HuggingFaceEmbeddings
embedding_model = HuggingFaceEmbeddings(
    model_name=m3e_name,
    model_kwargs=model_kwarg,
    encode_kwargs=encode_kwargs
)
# pip install qdrant-client
# 存入向量数据库
from langchain_community.vectorstores import Qdrant
vectorstore = Qdrant.from_documents(
    documents=chunked_documents,
    embedding=embedding_model,
    location=":memory:",
    collection_name="my_documents"
)

# 4、retrieval： chat——model
# pip install langchain[all] langchain-openai pydev
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.retrievers.multi_query import MultiQueryRetriever
from pydantic import SecretStr
load_dotenv()
chat_model_qwen = ChatOpenAI(
    model="deepseek-chat"
    , base_url=os.environ["OPENAI_DEEPSEEK_BASE_URL_FREE"]
    , api_key=SecretStr(os.environ["OPENAI_DEEPSEEK_APIKEY_FREE"])
)

retriever_from_llm = MultiQueryRetriever.from_llm(
    retriever=vectorstore.as_retriever(search_kwargs={"k": 5}),
    llm=chat_model_qwen,
)
from langchain.chains import RetrievalQA
qa_chain = RetrievalQA.from_chain_type(chat_model_qwen, retriever=retriever_from_llm)

question = """-目标-
作为知识图谱专家，请从专业目录表格中提取以下结构化信息：

表格结构说明：
1. 表格包含7列：序号、门类/专业类、专业代码、专业名称、学位授予门类、修业年限、增设年度
2. 层级关系：学位授予门类 > 专业类 > 专业名称

-提取要求-
1. 实体识别：
(实体; <门类/专业类名称>; <"学位授予门类"|"专业类"|"专业名称">; <描述>)

2. 属性提取：
(实体属性; <实体名称>; <属性名>; <属性值>)

3. 关系提取：
(实体关系; <上级实体>; "包含"; <下级实体>)

-特别注意-
1. 当"门类/专业类"列同时包含门类和专业类时，需要分开识别
2. 专业代码中的"K"表示国家控制布点专业，"T"表示特设专业
3. 注意学位授予门类可能有多个值(如"工学,管理学")

-示例-
输入行：| 1 | 哲学类 | 010101 | 哲学 | 哲学 | 四年 | |
输出：
(实体; 哲学; 学位授予门类; 包含哲学类专业)
(实体; 哲学类; 专业类; 包含哲学、逻辑学等专业)
(实体; 哲学; 专业名称; 专业代码:010101)
(实体关系; 哲学; 包含; 哲学类)
(实体关系; 哲学类; 包含; 哲学)

当前表格内容：
{text}

请严格按照格式输出，不要包含任何解释或说明。
"""

def call_llm_stream(prompt: str) -> str:
    return chat_model_qwen.invoke(prompt).content

# 直接使用所有文档内容，不分块处理
text_content = "\n".join([doc.page_content for doc in documents])
print(f"文本内容总长度: {len(text_content)} 字符")

# 如果内容太长，分批处理
max_chunk_size = 8000  # 根据LLM的token限制调整
if len(text_content) > max_chunk_size:
    print("内容较长，将分批处理...")
    chunks = [text_content[i:i+max_chunk_size] for i in range(0, len(text_content), max_chunk_size)]
    all_outputs = []
    for i, chunk in enumerate(chunks):
        print(f"处理第 {i+1}/{len(chunks)} 块...")
        prompt = question.format(text=chunk)
        try:
            output_stream = call_llm_stream(prompt)
            all_outputs.append(output_stream)
        except Exception as e:
            print(f"处理第 {i+1} 块时出错: {e}")
            all_outputs.append(f"# 第 {i+1} 块处理出错: {e}")
    
    output_stream = "\n\n".join(all_outputs)
else:
    prompt = question.format(text=text_content)
    output_stream = call_llm_stream(prompt)

with open("output/output.txt", "w", encoding="utf-8") as f:
    f.write(output_stream)

print("输出已保存到 output.txt")
