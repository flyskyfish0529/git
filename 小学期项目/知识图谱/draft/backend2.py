from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, SecretStr
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
import asyncio
import json
import os
import uvicorn
from typing import AsyncGenerator
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="DeepSeek Streaming API", version="1.0.0")

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 请求模型
class ChatRequest(BaseModel):
    message: str
    max_tokens: int = 1000


class DeepSeekChatService:
    def __init__(self):
        try:
            self.chat_model = ChatOpenAI(
                model="deepseek-chat",
                base_url=os.environ["OPENAI_DEEPSEEK_BASE_URL_FREE"],
                api_key=SecretStr(os.environ["OPENAI_DEEPSEEK_APIKEY_FREE"]),
                temperature=0.3,
                streaming=True
            )
            logger.info("DeepSeek ChatModel initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize DeepSeek ChatModel: {e}")
            raise

    async def stream_chat(self, message: str) -> AsyncGenerator[str, None]:
        """流式生成聊天响应"""
        try:
            # 创建消息
            messages = [HumanMessage(content=message)]

            # 流式调用
            async for chunk in self.chat_model.astream(messages):
                if chunk.content:
                    # 构造SSE格式数据
                    data = {
                        "type": "content",
                        "content": chunk.content
                    }
                    yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

            # 发送结束信号
            end_data = {"type": "end", "content": ""}
            yield f"data: {json.dumps(end_data, ensure_ascii=False)}\n\n"

        except Exception as e:
            logger.error(f"Streaming chat error: {e}")
            error_data = {
                "type": "error",
                "content": f"Error: {str(e)}"
            }
            yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"


# 初始化服务
chat_service = DeepSeekChatService()


@app.get("/")
async def root():
    return {"message": "DeepSeek Streaming API is running"}


@app.post("/chat/stream")
async def stream_chat(request: ChatRequest):
    """流式聊天端点"""
    try:
        return StreamingResponse(
            chat_service.stream_chat(request.message),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
            }
        )
    except Exception as e:
        logger.error(f"Stream chat endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "healthy", "service": "DeepSeek Streaming API"}


# 默认提示词生成器
def get_default_prompts():
    """获取默认提示词列表"""
    return [
        "请介绍一下人工智能的发展历史",
        "解释一下机器学习和深度学习的区别",
        "描述一下量子计算的基本原理",
        "讲解一下区块链技术的应用场景",
        "分析一下云计算的优势和挑战",
        "介绍一下自然语言处理的主要技术",
        "解释一下计算机视觉的应用领域",
        "描述一下物联网的技术架构",
        "讲解一下大数据处理的方法",
        "分析一下网络安全的重要性"
    ]


@app.get("/default-prompts")
async def get_default_prompts_endpoint():
    """获取默认提示词"""
    return {"prompts": get_default_prompts()}


if __name__ == "__main__":
    # 检查环境变量
    required_env_vars = ["OPENAI_DEEPSEEK_BASE_URL_FREE", "OPENAI_DEEPSEEK_APIKEY_FREE"]
    missing_vars = [var for var in required_env_vars if not os.environ.get(var)]

    if missing_vars:
        logger.error(f"Missing environment variables: {missing_vars}")
        print("请设置以下环境变量:")
        for var in missing_vars:
            print(f"  export {var}='your_value'")
        exit(1)

    print("🚀 启动DeepSeek流式聊天后端服务...")
    print("📝 API文档: http://localhost:8000/docs")
    print("🏥 健康检查: http://localhost:8000/health")

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )