import configparser

import streamlit as st
import requests
import streamlit.components.v1 as components
from knowledge_graph.draw import display_graph_pyvis
import time
import json
import logging

# 读取配置文件
config = configparser.ConfigParser()
config.read('config.ini')
backward= config['IP']['backward']

st.title("📝 专业分析知识图谱")

st.write("你是否对不同专业的具体方向依然模糊不清？\n")
st.write("你是否对不同专业的具体方向依然模糊不清？\n")
st.write("你是否对未来的专业选择感到迷茫，不知从何入手？\n")

st.write("别担心，专业知识图谱功能为你指明方向！只需输入你的兴趣领域,我们就能为你梳理出清晰的细分方向，帮你找到最适合自己的学术路径。\n")

st.write("       ✅ 精准推荐：从专业授予门类到具体专业名称一键获取专业细分领域。\n")
st.write("       ✅ 高效决策：告别信息过载，快速锁定研究方向。 \n")
st.write("       ✅ 个性化探索：无论你对理工科感兴趣，还是对文史哲经感兴趣，都能找到属于你的知识地图。\n")

st.write("开启你的专业探索之旅，让未来的道路更加清晰！\n")

user_input = st.text_input("请输入您的专业偏好（如：我对物理学感兴趣）")

tuples = None

if st.button("获取专业知识图谱🍊"):
    if user_input:
        try:
            response = requests.post(
                f"http://{backward}/process",
                json={"text": user_input},
                stream=True,
                timeout=120
            )

            if response.status_code != 200:
                st.error(f"后端错误: {response.status_code}")
                st.stop()

            placeholder = st.empty()
            full_response = ""
            error_flag = False

            # 流式输出
            try:
                buffer = ""
                for line in response.iter_lines(decode_unicode=True):
                    if not line:
                        continue
                    if line.startswith("data: "):
                        line = line[6:]
                    if not line.strip():
                        continue
                    try:
                        data = json.loads(line)
                    except Exception:
                        continue
                    if data.get("type") == "content":
                        full_response += data.get("content", "")
                        placeholder.markdown(full_response + "🍊")
                    elif data.get("type") == "end":
                        placeholder.markdown(full_response)
                        break
                    elif data.get("type") == "error":
                        st.error(data.get("content", "未知错误"))
                        error_flag = True
                        break
                    # 其他类型忽略
                    time.sleep(0.01)

                if not error_flag:
                    # 分析文本输出后，自动请求知识图谱
                    payload = {"text": user_input, "extra": ""}
                    kg_response = requests.post(f"http://{backward}/get_dynamic_kg", json=payload, timeout=60)
                    if kg_response.status_code == 200:
                        kg_data = kg_response.json().get("kg_data", [])
                        if isinstance(kg_data, list) and kg_data:
                            html_str = display_graph_pyvis(triplets=[tuple(row) for row in kg_data])
                            components.html(html_str, height=600, scrolling=True)
                        else:
                            st.warning("分析后知识图谱数据为空！")
                    else:
                        st.error(f"知识图谱后端错误: {kg_response.status_code}")

            except Exception as e:
                st.error(f"流式处理错误: {str(e)}")

        except requests.exceptions.RequestException as e:
            st.error(f"连接后端失败: {e}")
        except Exception as e:
            st.error(f"处理过程中出现错误: {str(e)}")
    else:
        st.warning("请输入内容再提交！")