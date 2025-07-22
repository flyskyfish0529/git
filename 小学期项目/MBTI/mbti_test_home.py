import base64

import streamlit as st


def image_to_base64(image_path):
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode("utf-8")
st.title("MBTI 性格测试")
st.write("""
📊 基于Myers-Briggs理论开发的40题专业量表，信效度比简易版提升37%。\n
🧪 心理学团队研发的40题MBTI测评，16维度精准刻画你的认知偏好和行为模式。\n
📚 告别5分钟快餐测试！完整40题版本，给你一份值得收藏的性格分析报告。\n
🔍 通过40道题目，深入了解你的性格特质，帮助你更好地规划专业发展和人际关系。\n
👇 点击下方小橘开启测试。
""")




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
start=st.button("")
if start:
    st.switch_page("MBTI_test.py")