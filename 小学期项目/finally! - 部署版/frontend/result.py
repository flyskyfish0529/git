import ast
import configparser
import httpx
import streamlit as st
import requests
import json
import time
import random
from typing import Generator
import logging
from dotenv import load_dotenv
import pandas as pd

load_dotenv()
# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 读取配置文件
config = configparser.ConfigParser()
config.read('config.ini')
backward= config['IP']['backward']
# fastapi服务地址
url = f"http://{backward}"
api_url = f"{url}/api/orange"


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

    def stream_chat_response(self, message: str) -> Generator[str, None, None]:
        """流式获取聊天响应"""
        try:
            payload = {"message": message,
                       "max_tokens": 1000,
                       "history": st.session_state.chat_history
                       }


            with requests.post(
                    f"{api_url}/chat/stream",
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
            with st.chat_message("user",avatar="src/user.png"):
                st.write(user_msg)
            with st.chat_message("assistant",avatar="src/orange.png"):
                st.write(ai_msg)

    def run(self):
        """运行主应用"""

        # 主聊天区域
        chat_container = st.container()

        with chat_container:
            # 渲染聊天历史
            self.render_chat_history()

            # 当前流式响应
            if st.session_state.is_streaming and st.session_state.current_response:
                with st.chat_message("assistant"):
                    st.write(st.session_state.current_response)


        user_input = st.chat_input(
            "您还有什么想问的吗🍊",
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
        with st.chat_message("user",avatar="src/user.png"):
            st.write(user_input)

        # 开始流式响应
        st.session_state.is_streaming = True
        st.session_state.current_response = ""

        # 创建助手消息占位符
        with st.chat_message("assistant",avatar="src/orange.png"):
            message_placeholder = st.empty()

            # 流式更新响应
            full_response = ""

            try:
                for chunk in self.stream_chat_response(user_input):
                    full_response += chunk
                    message_placeholder.markdown(full_response + "🍊")
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
    # 尝试获取推荐结果
    try:
        response = httpx.get(
            f"{api_url}/recommend_result",
            headers={"Content-Type": "application/json; charset=utf-8"},
            timeout=3600
        )
        response.raise_for_status()  # 检查HTTP状态码
        response_data = response.json()

        if not response_data:  # 检查数据是否为空
            st.info("正在生成您的志愿推荐，请稍候...")
            return

        # 解析数据并显示
        data_dict = ast.literal_eval(response_data)
        df_list = []
        for category, schools in data_dict.items():
            for school in schools:
                school["志愿类型"] = category
                df_list.append(school)

        df = pd.DataFrame(df_list)
        df = df[["志愿类型", "院校名称", "总招生人数", "平均分", "录取概率"]]

        with st.expander("点击获取您的志愿表"):
            st.dataframe(
                df,
                column_config={
                    "志愿类型": "志愿类型",
                    "院校名称": "院校名称",
                    "总招生人数": st.column_config.NumberColumn("总招生人数", format="%d人"),
                    "平均分": st.column_config.NumberColumn("平均分", format="%.1f分"),
                    "录取概率": "录取概率"
                },
                hide_index=True,
                use_container_width=True
            )

    except httpx.HTTPStatusError as e:
        st.info("数据正在准备中，请稍后刷新页面...")
        logger.info(f"等待后端数据: {e}")
    except json.JSONDecodeError:
        st.info("数据解析中，请稍候...")
    except Exception as e:
        logger.error(f"获取数据失败: {e}")
        st.error("未获取志愿表")

    # 运行聊天界面
    chat_interface = StreamlitChatInterface()
    chat_interface.run()


st.markdown(
    """<h2 style='text-align: center;'>获取您的院校推荐</h2>""",
    unsafe_allow_html=True
)
main()



