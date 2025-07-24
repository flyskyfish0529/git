import base64
import configparser
import time

import httpx
import pandas as pd
import streamlit as st
import random
import requests
from streamlit_lottie import st_lottie
import re

# 初始化st.session_statef
if 'users' not in st.session_state:
    st.session_state.users = {}
if 'verification_codes' not in st.session_state:
    st.session_state.verification_codes = {}
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'current_user' not in st.session_state:
    st.session_state.current_user = None
if 'Current_Page' not in st.session_state:
    st.session_state.Current_Page = 'login'  # 默认登录页

# 验证码发送函数
def send_code(phone):
    code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
    st.session_state.verification_codes[phone] = {
        'code': code,
    }
    st.success(f"验证码已发送（模拟：{code}）")

# 验证码验证函数
def verify(phone, code):
    if phone not in st.session_state.verification_codes:
        return False
    v = st.session_state.verification_codes[phone]
    return v['code'] == code

# 用户登录
def login_user(phone, pwd):
    #发送手机号和密码到后端
    send={
        "phone_number":phone,
        "password":pwd
    }
    try:
        response=httpx.post(
            f"{api_url}/loader",
            json=send,
            timeout=3600
        )
        response.raise_for_status()
        state=response.json().get("state")
        message=response.json().get("message")
        #根据后端回复输出
        if state==200:
            st.session_state.logged_in = True
            st.session_state.current_user = phone
            st.session_state.Current_Page = 'home'
            st.session_state.error_message = None  # 清除错误消息
            return True
        else:
            st.session_state.error_message = message  # 存储错误消息
            return False
    except Exception as e:
        st.error(f"发送失败：{str(e)}")

# 注册用户功能
def register_user(phone, pwd):
    # 发送手机号和密码到后端
    send = {
        "phone_number": phone,
        "password": pwd
    }
    try:
        response = httpx.post(
            f"{api_url}/register",
            json=send,
            timeout=3600
        )
        response.raise_for_status()
        state = response.json().get("state")
        message = response.json().get("message")
        # 根据后端回复输出
        if state == 200:
            st.session_state.logged_in = True
            st.session_state.current_user = phone
            st.session_state.Current_Page = 'home'
            st.session_state.error_message = None  # 清除错误消息
            return True
        else:
            st.session_state.error_message = message  # 存储错误消息
            return False
    except Exception as e:
        st.error(f"发送失败：{str(e)}")

# 用户登出功能
def logout_user():
    st.session_state.logged_in = False
    st.session_state.current_user = None
    st.session_state.Current_Page = 'login'

# 动画加载
@st.cache_data
def load_lottie(url: str):
    return requests.get(url).json()

lottie_login = load_lottie("https://assets2.lottiefiles.com/packages/lf20_jcikwtux.json")
lottie_reg = load_lottie("https://assets9.lottiefiles.com/packages/lf20_uwos7l6e.json")
lottie_submit = load_lottie("https://assets4.lottiefiles.com/packages/lf20_touohxv0.json")

# ------------------ CSS样式 ------------------
def global_css():
    st.markdown("""
    <style>
    body { background: linear-gradient(135deg,#f5f7fa 0%, #e4edf5 100%); }
    .glass-card {
        background: rgba(255,255,255,0.55);
        border-radius: 18px;
        padding: 32px 36px;
        margin: 28px 0;
        box-shadow: 0 8px 32px 0 rgba(31,38,135,0.15);
        backdrop-filter: blur(8px);
        border: 1px solid rgba(255,255,255,0.18);
    }
    </style>
    """, unsafe_allow_html=True)

# 登录页
def login_page():

    global_css()
    st.markdown("<h1 style='text-align:center; color:#4f8df7;'>小橘助手--专业的大学志愿填报助手 - 登录</h1>", unsafe_allow_html=True)
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)


    # 登录方式选择
    col1, col2 = st.columns(2)
    with col1:
        use_code = st.button("📱 验证码登录", use_container_width=True)
    with col2:
        use_pwd  = st.button("🔑 密码登录",   use_container_width=True)

    if "login_mode" not in st.session_state:
        st.session_state.login_mode = None
    if use_code:
        st.session_state.login_mode = "code"
    elif use_pwd:
        st.session_state.login_mode = "pwd"

    # 验证码登录
    if st.session_state.login_mode == "code":
        st.markdown("#### 验证码登录")
        with st.form("code_login_form"):
            phone = st.text_input("手机号")
            code  = st.text_input("验证码")
            col_send, col_submit = st.columns(2)
            with col_send:
                if st.form_submit_button("📤 获取验证码", use_container_width=True):
                    if phone.isdigit() and len(phone) == 11:
                        send_code(phone)
                    else:
                        st.error("请输入11位手机号")
            with col_submit:
                if st.form_submit_button("✅ 登录", use_container_width=True):
                    if not phone:
                        st.error("请输入手机号")
                    elif phone not in st.session_state.verification_codes:
                        st.error("请先获取验证码")
                    elif not verify(phone, code):
                        st.error("验证码错误或已过期")
                    else:
                        # 直接登录，无需注册
                        if phone not in st.session_state.users:
                            st.session_state.users[phone] = {
                                'password': None,
                            }
                        st.session_state.logged_in = True
                        st.session_state.current_user = phone
                        st.session_state.Current_Page = 'home'
                        st.rerun()

    # 密码登录
    elif st.session_state.login_mode == "pwd":
        st.markdown("#### 密码登录")
        with st.form("pwd_login_form"):
            phone = st.text_input("手机号")
            pwd   = st.text_input("密码", type="password")
            if st.form_submit_button("🔐 登录", use_container_width=True):
                if not phone:
                    st.error("请输入手机号")
                else:
                    login_user(phone,pwd)

                    st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

    # 仅保留注册按钮
    if st.session_state.get('error_message'):
        st.error(st.session_state.error_message)
    if st.button("📝 立即注册", use_container_width=True):
        st.session_state.Current_Page= 'register'
        st.rerun()
    if st.button("🔒管理员模式", use_container_width=True):
        st.session_state.Current_Page= 'administer'
        st.rerun()
#管理员
def administer_page():
    with st.form("register_form"):
        account = st.text_input("管理员账号")
        pwd   = st.text_input("管理员密码")
        if st.form_submit_button("以管理员身份登录👨‍💻",use_container_width=True):
            if not account:
                st.error("请输入管理员账号")
            elif not account.isdigit() or len(account) != 11:
                st.error("账号号必须为11位数字")
            else:
                response=httpx.post(
                    f"{api_url}/lookat",
                    json={"phone_number":account,"password":pwd},
                    timeout=3600
                )
                state=response.json().get("state")
                message=response.json().get("message")
                if state!=200:
                    st.markdown(f"<p style='text-align:center; color:orange;'>{message}</p>", unsafe_allow_html=True)
                else:
                    df=pd.DataFrame(message,columns=["手机号","密码"])
                    st.dataframe(df,hide_index=True)
        if st.form_submit_button("返回登录页面",use_container_width=True):
            st.session_state.Current_Page='login'
            st.rerun()

# 注册页
def register_page():
    import re
    global_css()
    st.markdown("<h1 style='text-align:center; color:#4f8df7;'>高考志愿报考系统 - 注册</h1>", unsafe_allow_html=True)
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st_lottie(lottie_reg, height=160, key="reg")



    with st.form("register_form"):
        phone = st.text_input("📱 手机号")
        pwd   = st.text_input("🔑 密码", type="password")
        cpwd  = st.text_input("🔑 确认密码", type="password")
        code  = st.text_input("验证码")

        col1, col2 = st.columns(2)
        with col1:
            if st.form_submit_button("📤 获取验证码", use_container_width=True):
                if not phone:
                    st.error("请输入手机号")
                elif not phone.isdigit() or len(phone) != 11:
                    st.error("手机号必须为11位数字")
                else:
                    send_code(phone)
        with col2:
            if st.form_submit_button("🎯 立即注册", use_container_width=True):
                if not phone:
                    st.error("请输入手机号")
                if not re.fullmatch(r"1[3-9]\d{9}", phone):
                    st.error("手机号格式不正确，请输入有效的11位手机号")
                elif phone in st.session_state.users:
                    st.error("该手机号已注册")
                elif not pwd:
                    st.error("请输入密码")
                elif not cpwd:
                    st.error("请确认密码")
                elif pwd != cpwd:
                    st.error("两次密码不一致")
                elif phone not in st.session_state.verification_codes:
                    st.error("请先获取验证码")
                elif not verify(phone, code):
                    st.error("验证码错误或已过期")
                else:
                    register_user(phone, pwd)

                    st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)
    if st.session_state.get('error_message'):
        st.error(st.session_state.error_message)
    if st.button("🔙 返回登录", use_container_width=True):
        st.session_state.Current_Page = 'login'
        st.rerun()

# 登录成功界面
def success_login():
    st.set_page_config(page_title="登录成功", layout="centered")

    # 用户信息卡片
    st.markdown("""
        <div style='
            border-radius: 15px;
            padding: 25px;
            margin: 20px 0;
            text-align: center;
        '>
            <p style='font-size: 30px; margin-bottom: 5px;'>👤 <b>{}</b></p>
            <p style='color: #666;'>🍊您已成功登录高考志愿填报系统🍊</p>
        </div>
        """.format(st.session_state.current_user), unsafe_allow_html=True)

    #用户提示
    def img_to_base64(img_path):
        with open(img_path, "rb") as f:
            return "data:image/png;base64," + base64.b64encode(f.read()).decode()
    img_base64 = img_to_base64("src/orange.png")
    st.markdown(f"""
    <div style='display: flex; align-items: center; justify-content: center;'>
      <span style='font-size: 2em; color:orange; margin: 0 4px 0 0; padding: 0;'>⬅⬅⬅您可以使用左侧功能</span>
      <img src={img_base64} style='height: 50px; width: auto; vertical-align: middle;'>
    </div>
    """, unsafe_allow_html=True)
    # 安全提示
    st.markdown("""
        <div style='
            margin-top: 40px;
            font-size: 20px;
            color: #ff914d;
            text-align: center;
        '>
            <p>🔒 安全提示：请勿在公共设备保存登录状态</p>
        </div>
        """, unsafe_allow_html=True)

# ------------------ 路由 ------------------
def main():
    if st.session_state.Current_Page == 'login':
        login_page()
    elif st.session_state.Current_Page == 'register':
        register_page()
    elif st.session_state.Current_Page=='home':
        success_login()
    elif st.session_state.Current_Page=='administer':
        administer_page()

#加载配置文件
config = configparser.ConfigParser()
config.read('config.ini')
backward= config['IP']['backward']
# fastapi服务地址
url = f"http://{backward}"
api_url = f"{url}/api/orange"

main()