import time

import requests
import streamlit as st
import re
import base64
import configparser


config = configparser.ConfigParser()
config.read('config.ini')

backward = config['IP']['backward']

def image_to_base64(image_path):
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode("utf-8")
st.title("MBTI专业生成器")

st.write(" MBTI专业生成器是一款基于国际公认的MBTI性格类型理论开发的智能职业推荐系统。通过科学分析您的性格特质，我们能够为您匹配最适合的专业发展方向，帮助您发现未来潜在的就业机会，规划更满意的人生。")
st.write("我们的系统采用先进的匹配算法，结合美国职业信息网络的权威职业数据，确保推荐结果的准确性和实用性。所有用户数据严格加密，测试过程完全匿名。")
st.write("立即开始您的专业探索之旅，发现最适合您性格特质的理想职业！")

text_input = st.text_input("请输入您的MBTI类型（不区分大小写），下方出现“✅有效的 MBTI 类型！”后，点击左侧小橘提交：").strip().upper()
if text_input:
    if re.fullmatch(r"^[IE][NS][FT][JP]$", text_input):
        st.success("✅ 有效的 MBTI 类型！")
    else:
        st.error("❌ 无效的 MBTI 类型！请确保格式正确（如 INTJ、ENFP）。")
# 替换为你的本地图片路径
img_path = "orange.png"
img_base64 = image_to_base64(img_path)

st.markdown(f"""
<style>
div.stButton > button {{
    background-image: url("data:image/png;base64,{img_base64}");
    background-size: contain;
    background-repeat: no-repeat;
    background-position: center;
    height: 60px;
    width: 60px;
    border: none;
    color: transparent;
    font-size: 0px;
    padding: 0;
}}
</style>
""", unsafe_allow_html=True)


col1, col2 = st.columns([1, 1])
with col1:
    submit=st.button("",key="submit")  # 替换为你的提交按钮名称
with col2:
    st.write("不知道自己的MBTI？点下面的小橘速测！")
    jump=st.button("",key="jump")
    if jump:
        st.switch_page("mbti_test_home.py")  # 替换为你的测试页面名称
if submit:
    if text_input:
        # 初始消息（分成两行）
        result_part1 = f"您的MBTI类型是：{text_input}。"
        result_part2 = "正在为您匹配最适合的职业..."
        text = ""
        placeholder = st.empty()
        # 显示第一部分（打字机效果）
        for char in result_part1:
            text += char
            placeholder.markdown(text, unsafe_allow_html=True)
            time.sleep(0.05)
        text += "<br>"
        for char in result_part2:
            text += char
            placeholder.markdown(text, unsafe_allow_html=True)
            time.sleep(0.05)
        # 获取职业推荐
        career_recommendations = requests.post(
            url=f"http://{backward}:8000/api/orange/seek",
            json={"mbti_type": text_input}
        ).json().get("description")

        # 处理职业推荐内容
        if career_recommendations:
            # 替换最后的分号为句号
            career_recommendations = career_recommendations.replace("；", "。").replace("。。", "。")
            career_recommendations = career_recommendations.replace(
                    "您比较适合的职业是：",
                    "<br>您比较适合的职业是：<br>"
                ).replace(
                    "您可能会感兴趣的职业是：",
                    "<br>您可能会感兴趣的职业是：<br>"
                )
            # 按换行符分割不同部分
            sections = career_recommendations.split('\n')

            for section in sections:
                if not section.strip():
                    continue

                # 添加换行
                text += "<br>"

                # 显示每个部分（打字机效果）
                for char in section:
                    text += char
                    placeholder.markdown(text, unsafe_allow_html=True)
                    time.sleep(0.03)
        else:
            text += "<br>未找到相关职业推荐"
            placeholder.markdown(text, unsafe_allow_html=True)
    else:
        st.error("请输入有效的MBTI类型！")