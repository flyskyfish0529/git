import base64
import os

import streamlit as st


st.title("MBTI 性格测试")
st.write("""
📊 基于Myers-Briggs理论开发的40题专业量表，信效度比简易版提升37%。\n
🧪 心理学团队研发的40题MBTI测评，16维度精准刻画你的认知偏好和行为模式。\n
📚 告别5分钟快餐测试！完整40题版本，给你一份值得收藏的性格分析报告。\n
🔍 通过40道题目，深入了解你的性格特质，帮助你更好地规划专业发展和人际关系。\n
👇 点击下方小橘开启测试。
""")



#定义函数将图片转换为Base64编码
def img_to_base64(img_path):
    with open(img_path, "rb") as f:
        return base64.b64encode(f.read()).decode()

# 使用自定义按钮样式
img_path = "src/orange.png"
img_base64 = img_to_base64(img_path)
st.markdown(f"""
    <style>
    .element-container:has(#custom-button-marker) + div button {{
        background-image: url("data:image/jpg;base64,{img_base64}");
        background-size: cover;
        background-repeat: no-repeat;
        height: 50px;
        width: 50px;
    }}
    </style>
    """, unsafe_allow_html=True)
st.markdown('<span id="custom-button-marker"></span>', unsafe_allow_html=True)
start = st.button("")
if start:
    st.switch_page("MBTI/MBTI_test.py")