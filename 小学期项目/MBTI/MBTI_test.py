import time
import streamlit as st
import requests


import configparser

config = configparser.ConfigParser()
config.read('config.ini')

# 后端API地址
BACKEND_URL = config['IP']['backward']  # 根据实际后端地址修改

# 初始化session state
if 'current_page' not in st.session_state:
    st.session_state.current_page = 0
if 'selected_options' not in st.session_state:
    st.session_state.selected_options = {}
if 'questions' not in st.session_state:
    st.session_state.questions = []
if 'test_completed' not in st.session_state:
    st.session_state.test_completed = False
if 'all_questions_loaded' not in st.session_state:
    st.session_state.all_questions_loaded = False


def get_all_questions():
    """从后端获取所有问题"""
    try:
        questions = []
        # 获取第一题
        questions = requests.post(
            f"{BACKEND_URL}/api/orange/questions",
            json={}
        ).json().get("question")
        return questions
    except requests.exceptions.RequestException as e:
        st.error(f"连接后端失败: {e}")
        return None


def get_result():
    """提交当前页的所有选择"""
    try:
        mbti=requests.post(
            f"{BACKEND_URL}/api/orange/result",
            json={"operation": st.session_state.selected_options}
        )
        return mbti.json()
    except requests.exceptions.RequestException as e:
        st.error(f"提交答案失败: {e}")


def clear():
    """重置测试"""
    st.session_state.current_page = 0
    st.session_state.selected_options = {}
    st.session_state.questions = []
    st.session_state.test_completed = False
    st.session_state.all_questions_loaded = False
    requests.post(
        f"{BACKEND_URL}/api/orange/clear",
        json={}
    )


def main():
    st.title("MBTI 性格测试")
    st.write("回答以下问题，发现你的性格类型")

    # 初始化加载所有问题
    if not st.session_state.all_questions_loaded:
        questions = get_all_questions()
        if questions:
            st.session_state.questions = questions
            st.session_state.all_questions_loaded = True
            st.rerun()
        return

    # 显示问题或结果
    if not st.session_state.test_completed:
        # 计算当前页的问题范围
        start_idx = st.session_state.current_page * 5
        end_idx = min(start_idx + 5, len(st.session_state.questions))

        # 显示当前页的问题
        for i in range(start_idx, end_idx):
            question = st.session_state.questions[i]
            st.subheader(f"问题 {i + 1}")

            # 显示选项单选框
            options = ["尚未选择", question[1], question[2]]
            selected = st.radio(
                question[0],
                options,
                index=st.session_state.selected_options.get(i, 0),
                key=f"question_{i}"
            )
            st.session_state.selected_options[i] = options.index(selected)

        # 导航按钮
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            # 上一页按钮
            if st.button("上一页", disabled=st.session_state.current_page == 0):
                st.session_state.current_page -= 1
                st.rerun()

        with col2:
            # 下一页或提交按钮
            if end_idx == len(st.session_state.questions):
                # 检查是否所有问题都已回答
                all_answered = all(
                    st.session_state.selected_options.get(i, 0) != 0
                    for i in range(len(st.session_state.questions))
                )
                if st.button("提交", disabled=not all_answered):
                    st.session_state.test_completed = True
                    st.rerun()
            else:
                all_answered = all(
                    st.session_state.selected_options.get(i, 0) != 0
                    for i in range(start_idx,end_idx)
                )
                if st.button("下一页",disabled=not all_answered):
                    st.session_state.current_page += 1
                    st.rerun()

        # 显示进度条
        total_answered = sum(
            1 for i in range(len(st.session_state.questions))
            if st.session_state.selected_options.get(i, 0) != 0
        )
        progress = total_answered / len(st.session_state.questions)
        st.progress(progress)

        # 显示当前进度
        st.caption(f"已完成 {total_answered}/{len(st.session_state.questions)} 题")
        st.caption(f"当前页: {st.session_state.current_page + 1}/{(len(st.session_state.questions) // 5)}")
    else:
        # 显示测试结果
        MBTIresult = get_result()
        result_part1 = f"您的MBTI类型是：{MBTIresult}。"
        result_part2 = "正在为您匹配最适合的职业..."
        placeholder = st.empty()
        text = ""
        # 显示第一部分（打字机效果）
        for char in result_part1:
            text += char
            placeholder.markdown(text, unsafe_allow_html=True)
            time.sleep(0.05)

        # 换行显示第二部分
        text += "<br>"
        for char in result_part2:
            text += char
            placeholder.markdown(text, unsafe_allow_html=True)
            time.sleep(0.05)
        # 获取职业推荐
        career_recommendations = requests.post(
            url=f"{BACKEND_URL}/api/orange/seek",
            json={"mbti_type": MBTIresult}
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
        # 重新测试按钮
        clear()
        st.button("重新测试")
if __name__ == "__main__":
    main()