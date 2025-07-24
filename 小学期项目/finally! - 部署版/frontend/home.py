import streamlit as st


# 必须放在最前面：设置页面配置
st.set_page_config(
    page_title="高考志愿填报助手",
    layout="centered",
    initial_sidebar_state="expanded"
)


# 使用 st.navigation 作为主导航（自动加载第一个页面）

nav_config = {
    "注册&登录":[
        st.Page("login.py", title="注册"),
    ],
    "志愿填报推荐": [
        st.Page("user_messages.py", title="主页",default=True),
    ],
    "专业探索工具": [
            st.Page("MBTI/MBTI_home.py", title="MBTI|专业生成器"),
            st.Page("MBTI/MBTI_test_entrance.py", title="MBTI|测试入口"),
            st.Page("MBTI/MBTI_test.py", title="MBTI|性格测试"),
        st.Page("knowledge_graph/knowledge_graph_front.py", title="知识图谱"),
    ],
    "获取志愿结果":[
        st.Page("result.py",title="获取志愿结果")
    ]
}
pages = st.navigation(nav_config)

if 'logged_in' not in st.session_state:
    st.warning("请先登录以使用系统功能")
    if st.button("前往登录页面"):
        st.session_state.logged_in = False
        st.switch_page("login.py")
    st.stop()  # 阻止继续执行后面的代码


pages.run()

with st.sidebar:
    st.write("图片来源于网络，测试结果仅供参考")