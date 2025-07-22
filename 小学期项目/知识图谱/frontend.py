import streamlit as st
import requests
import streamlit.components.v1 as components
from draw import display_graph_pyvis
import time
import json
import logging

st.title("📝 专业分析知识图谱")

user_input = st.text_input("请输入内容:")

tuples = None

if st.button("发送到后端"):
    if user_input:
        try:
            response = requests.post(
                "http://127.0.0.1:8000/process",
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
                        placeholder.markdown(full_response + "▌")
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
                    kg_response = requests.post("http://127.0.0.1:8000/get_dynamic_kg", json=payload, timeout=60)
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