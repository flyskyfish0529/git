import streamlit as st
import requests
import json
import time
import random
from typing import Generator
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 配置页面
st.set_page_config(
    page_title="DeepSeek 流式聊天",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 配置后端API地址
BACKEND_URL = "http://localhost:8000"


class StreamlitChatInterface:
    def __init__(self):
        self.initialize_session_state()

    def initialize_session_state(self):
        """初始化会话状态"""
        if 'chat_history' not in st.session_state:
            st.session_state.chat_history = []
        if 'is_streaming' not in st.session_state:
            st.session_state.is_streaming = False
        if 'current_response' not in st.session_state:
            st.session_state.current_response = ""

    def get_default_prompts(self):
        """获取默认提示词"""
        try:
            response = requests.get(f"{BACKEND_URL}/default-prompts", timeout=5)
            if response.status_code == 200:
                return response.json()["prompts"]
        except Exception as e:
            logger.error(f"获取默认提示词失败: {e}")

        # 备用默认提示词
        return [
            "请介绍一下人工智能的发展历史",
            "解释一下机器学习和深度学习的区别",
            "描述一下量子计算的基本原理",
            "讲解一下区块链技术的应用场景",
            "分析一下云计算的优势和挑战"
        ]

    def check_backend_health(self):
        """检查后端服务健康状态"""
        try:
            response = requests.get(f"{BACKEND_URL}/health", timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"后端健康检查失败: {e}")
            return False

    def stream_chat_response(self, message: str) -> Generator[str, None, None]:
        """流式获取聊天响应"""
        try:
            payload = {"message": message, "max_tokens": 1000}

            with requests.post(
                    f"{BACKEND_URL}/chat/stream",
                    json=payload,
                    stream=True,
                    timeout=30,
                    headers={'Accept': 'text/plain'}
            ) as response:

                if response.status_code != 200:
                    yield f"错误: HTTP {response.status_code}"
                    return

                buffer = ""
                for chunk in response.iter_content(chunk_size=1024, decode_unicode=True):
                    if chunk:
                        buffer += chunk

                        # 处理SSE格式数据
                        while "\n\n" in buffer:
                            line, buffer = buffer.split("\n\n", 1)
                            if line.startswith("data: "):
                                try:
                                    data = json.loads(line[6:])  # 移除"data: "前缀
                                    if data["type"] == "content":
                                        yield data["content"]
                                    elif data["type"] == "end":
                                        return
                                    elif data["type"] == "error":
                                        yield f"错误: {data['content']}"
                                        return
                                except json.JSONDecodeError:
                                    continue

        except requests.RequestException as e:
            yield f"网络错误: {str(e)}"
        except Exception as e:
            yield f"未知错误: {str(e)}"

    def render_chat_history(self):
        """渲染聊天历史"""
        for i, (user_msg, ai_msg) in enumerate(st.session_state.chat_history):
            with st.chat_message("user"):
                st.write(user_msg)
            with st.chat_message("assistant"):
                st.write(ai_msg)

    def render_sidebar(self):
        """渲染侧边栏"""
        with st.sidebar:
            st.header("🤖 DeepSeek 流式聊天")

            # 健康检查
            if self.check_backend_health():
                st.success("✅ 后端服务正常")
            else:
                st.error("❌ 后端服务不可用")
                st.stop()

            st.divider()

            # 默认提示词
            st.subheader("📝 默认提示词")
            default_prompts = self.get_default_prompts()

            if st.button("🎲 随机选择提示词"):
                selected_prompt = random.choice(default_prompts)
                st.session_state.selected_prompt = selected_prompt
                st.rerun()

            if 'selected_prompt' in st.session_state:
                st.info(f"已选择: {st.session_state.selected_prompt}")

            st.divider()

            # 聊天历史管理
            st.subheader("📜 聊天历史")
            st.write(f"对话数量: {len(st.session_state.chat_history)}")

            if st.button("🗑️ 清空历史"):
                st.session_state.chat_history = []
                st.session_state.current_response = ""
                st.rerun()

            st.divider()

            # 配置信息
            st.subheader("⚙️ 配置信息")
            st.json({
                "后端地址": BACKEND_URL,
                "模型": "deepseek-chat",
                "流式输出": True,
                "温度": 0.3
            })

    def run(self):
        """运行主应用"""
        st.title("🤖 DeepSeek 流式聊天助手")

        # 渲染侧边栏
        self.render_sidebar()

        # 主聊天区域
        chat_container = st.container()

        with chat_container:
            # 渲染聊天历史
            self.render_chat_history()

            # 当前流式响应
            if st.session_state.is_streaming and st.session_state.current_response:
                with st.chat_message("assistant"):
                    st.write(st.session_state.current_response)

        # 输入区域
        input_container = st.container()

        with input_container:
            # 使用选中的提示词作为默认值
            default_value = st.session_state.get('selected_prompt', '')

            user_input = st.chat_input(
                "请输入您的问题...",
                disabled=st.session_state.is_streaming,
                key="user_input"
            )

            # 处理用户输入
            if user_input:
                self.process_user_input(user_input)

            # 如果有选中的提示词，自动处理
            if ('selected_prompt' in st.session_state and
                    not st.session_state.is_streaming and
                    st.session_state.selected_prompt):
                self.process_user_input(st.session_state.selected_prompt)
                del st.session_state.selected_prompt

    def process_user_input(self, user_input: str):
        """处理用户输入并开始流式响应"""
        if not user_input.strip():
            return

        # 显示用户消息
        with st.chat_message("user"):
            st.write(user_input)

        # 开始流式响应
        st.session_state.is_streaming = True
        st.session_state.current_response = ""

        # 创建助手消息占位符
        with st.chat_message("assistant"):
            message_placeholder = st.empty()

            # 流式更新响应
            full_response = ""

            try:
                for chunk in self.stream_chat_response(user_input):
                    full_response += chunk
                    message_placeholder.markdown(full_response + "▌")
                    time.sleep(0.01)  # 小延迟以提供更好的视觉效果

                # 完成响应
                message_placeholder.markdown(full_response)

                # 添加到聊天历史
                st.session_state.chat_history.append((user_input, full_response))

            except Exception as e:
                error_msg = f"响应生成错误: {str(e)}"
                message_placeholder.error(error_msg)
                st.session_state.chat_history.append((user_input, error_msg))

            finally:
                # 重置状态
                st.session_state.is_streaming = False
                st.session_state.current_response = ""

                # 刷新页面以更新输入框状态
                st.rerun()


def main():
    """主函数"""
    try:
        chat_interface = StreamlitChatInterface()
        chat_interface.run()
    except Exception as e:
        st.error(f"应用启动失败: {str(e)}")
        logger.error(f"应用启动失败: {e}")


if __name__ == "__main__":
    main()