import base64
import configparser
import json

import httpx
import pandas as pd
import pymysql
import streamlit as st
from PIL import Image
import time

# 读取配置文件
config = configparser.ConfigParser()
config.read('config.ini')

# 初始化学生信息DataFrame
student_info = pd.DataFrame({
    "信息类别": ["所在省份", "高考总分", "选考科目", "全省排名", "感兴趣科目", "不感兴趣科目", "职业发展目标",
                 "志愿填报策略","兴趣爱好"],
    "信息内容": ["", "", "", "", "", "", "", "",""]
})

if 'Current_page' not in st.session_state or st.session_state.Current_page == '':
    st.session_state.Current_page = 'page1'

# 页面1：收集学生信息
def page_1():
    cols = st.columns([7,2])
    # 收集信息
    with cols[1]:
        province = st.selectbox(
            "所在省份",
            options=[
                "北京市", "天津市", "河北省", "山西省", "内蒙古自治区", "辽宁省", "吉林省",
                "黑龙江省", "上海市", "江苏省", "浙江省", "安徽省", "福建省", "江西省",
                "山东省", "河南省", "湖北省", "湖南省", "广东省", "广西壮族自治区", "海南省",
                "重庆市", "四川省", "贵州省", "云南省", "西藏自治区", "陕西省", "甘肃省",
                "青海省", "宁夏回族自治区", "新疆维吾尔自治区", "香港特别行政区",
                "澳门特别行政区", "台湾省"
            ],
            index=1
        )
        score = st.number_input("高考总分", min_value=0, max_value=750, placeholder="请输入高考总分")

        # 显示选考科目
        selected_subjects = st.multiselect(
            "选考科目",
            placeholder="请选择选考科目",
            options=["物理", "化学", "生物", "地理", "历史", "政治"],
            max_selections=3,
            help="只能选择3个科目哦"
        )
        rank = st.number_input("全省排名", min_value=1)

    # 连接数据库并查询一分一段表
    # 数据库配置信息
    # 连接数据库并查询
    try:
        conn = pymysql.connect(
            host=config['score_distribution']['host'],
            user=config['score_distribution']['user'],
            password=config['score_distribution']['password'],
            database=config['score_distribution']['database'],
            charset=config['score_distribution']['charset']
        )
        df = pd.read_sql('SELECT * from Tianjin_score_distribution;', conn)
        conn.close()
    except Exception as e:
        st.write(f"数据库连接失败：{e}")

    # 显示一分一段表
    with st.expander("还不清楚自己的排名？点击查看一分一段表🍊"):
        st.write(df)

    # 定义函数将图片转换为Base64编码
    def img_to_base64(img_path):
        with open(img_path, "rb") as f:
            return base64.b64encode(f.read()).decode()

    # 显示信息填写提示
    img_base64 = img_to_base64("src/clx.png")
    st.markdown(
        """<h2 style='text-align: center;'>请完善您的信息(ง๑ •̀_•́)ง</h2>""",
        unsafe_allow_html=True
    )
    st.markdown(f"""
            <div style="display: flex; align-items: center; margin-bottom: 10px;">
                <img src="data:image/png;base64,{img_base64}" width="80"  style="margin-right: 1px;">
                <span style="font-size: 1.2em;">：填好后请点击最下方橘子提交</span>
            </div>
            """,
                unsafe_allow_html=True
                )

    # 收集其他信息
    want_major = st.text_input("感兴趣专业🍊", key="favourite_subjects",placeholder="还没有心仪的科目？点击侧边栏可获取更多专业推荐")
    unwant_major = st.text_input("不感兴趣专业🍊", key="unpleasant_subjects")
    future_goal = st.text_input("职业发展目标🍊", key="future_goal")
    strategy = st.selectbox("志愿填报策略🍊", placeholder="请选择您的偏好",
            options=["科目优先", "城市优先", "院校优先"],
            key="strategy")
    city_preference = st.text_input("偏好城市？",
                                   placeholder="请输入您的偏好城市",
                                   key="city_preference",
                                   disabled=(strategy!="城市优先"))
    hobby=st.text_input("兴趣爱好🍊", placeholder="请输入您的兴趣爱好", key="hobby")

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
    submit = st.button("", key="orange")

    # 更新DataFrame数据
    student_info.at[0, "信息内容"] = province
    student_info.at[1, "信息内容"] = str(score)
    student_info.at[2, "信息内容"] = ", ".join(selected_subjects)
    student_info.at[3, "信息内容"] = str(rank)
    student_info.at[4, "信息内容"] = want_major if want_major else "无"
    student_info.at[5, "信息内容"] = unwant_major if unwant_major else "无"
    student_info.at[6, "信息内容"] = future_goal if future_goal else "无"
    if strategy == "城市优先":
        student_info.at[7, "信息内容"] = strategy+":"+city_preference
    else:
        student_info.at[7, "信息内容"] = strategy
    student_info.at[8, "信息内容"] = hobby if hobby else "无"

    if submit:
        # 保存信息到session_state
        st.session_state.student_info = student_info
        st.session_state.Current_page = 'page2'
        st.rerun()

    # 显示动画效果
    with cols[0]:

        placeholder = st.empty()
        #st.image("src/home.png",width=1000)
        # 加载图片
        image1 = Image.open("src/home0.png").convert("RGBA")
        image2 = Image.open("src/home1.png").convert("RGBA")
        width, height = image1.size

        # 动画参数
        # 停留时间和滚动速度
        stay_duration = 5.0
        scroll_duration = 1.0
        # 帧数
        frames = 5

        # 初始化会话状态
        if 'animation_running' not in st.session_state:
            st.session_state.animation_running = True

        if st.session_state.animation_running:
            # 1. 显示图片1
            placeholder.image(image1, use_container_width=True)
            time.sleep(stay_duration)

            # 2. 图片1 → 图片2的滚动动画
            for i in range(frames):
                start_time = time.time()
                progress = i / (frames - 1)
                canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
                canvas.paste(image1, (int(-width * progress), 0))
                canvas.paste(image2, (int(width * (1 - progress)), 0))
                placeholder.image(canvas, use_container_width=True)
                elapsed = time.time() - start_time
                remaining = (scroll_duration / frames) - elapsed
                if remaining > 0:
                    time.sleep(remaining)

            # 3. 显示图片2
            placeholder.image(image2, use_container_width=True)
            time.sleep(stay_duration)

            # 4. 图片2 → 图片1的滚动动画
            for i in range(frames):
                start_time = time.time()
                progress = i / (frames - 1)
                canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
                canvas.paste(image2, (int(width * progress), 0))
                canvas.paste(image1, (int(-width * (1 - progress)), 0))
                placeholder.image(canvas, use_container_width=True)  # 修改这里
                elapsed = time.time() - start_time
                remaining = (scroll_duration / frames) - elapsed
                if remaining > 0:
                    time.sleep(remaining)

            # 循环完成后重新运行脚本
            st.rerun()
        else:
            placeholder.image(image1, use_container_width=True)  # 修改这里



# 页面2：显示考生信息并提交
def page_2():
    # 显示考生信息表格
    st.dataframe(
        st.session_state.student_info,
        hide_index=True,
        use_container_width=True,
        column_config={
            "信息类别": st.column_config.TextColumn("信息类别", width="medium"),
            "信息内容": st.column_config.TextColumn("信息内容", width="large")
        }
    )

    # 初始化按钮状态
    if 'confirmed' not in st.session_state:
        st.session_state.confirmed = False

    # 使用固定的唯一 key 创建按钮
    confirm_button = st.button(
        "确认信息无误，提交",
        #disabled=st.session_state.confirmed,  # 禁用已点击的按钮
        key="unique_confirm_button"  # 固定唯一 key
    )

    if confirm_button: #and not st.session_state.confirmed:
        #st.session_state.confirmed = True

        #创建发送文本模版
        #message_template = "我来自{province}，高考总分{score}，选考科目是{subjects}。我的全省排名是{rank}名。我对{favourite_subjects}感兴趣，对{unpleasant_subjects}不感兴趣。我的职业发展目标是：{future_goal}。我的偏好城市是：{city_preference}。"

        #创建文本对象
        # message_str=message_template.format(
        #     province=st.session_state.student_info.at[0, "信息内容"],
        #     score=st.session_state.student_info.at[1, "信息内容"],
        #     subjects=st.session_state.student_info.at[2, "信息内容"],
        #     rank=st.session_state.student_info.at[3, "信息内容"],
        #     favourite_subjects=st.session_state.student_info.at[4, "信息内容"],
        #     unpleasant_subjects=st.session_state.student_info.at[5, "信息内容"],
        #     future_goal=st.session_state.student_info.at[6, "信息内容"],
        #     city_preference=st.session_state.student_info.at[7, "信息内容"]
        # )

        live_city = st.session_state.student_info.at[0, "信息内容"]
        score=st.session_state.student_info.at[1, "信息内容"]
        subjects=st.session_state.student_info.at[2, "信息内容"]
        rank=st.session_state.student_info.at[3, "信息内容"]
        want_major=st.session_state.student_info.at[4, "信息内容"]
        unwant_major=st.session_state.student_info.at[5, "信息内容"]
        future_goal=st.session_state.student_info.at[6, "信息内容"]
        strategy=st.session_state.student_info.at[7, "信息内容"]
        hobby=st.session_state.student_info.at[8, "信息内容"]


        backward= config['IP']['backward']
        # fastapi服务地址
        url = f"http://{backward}"
        api_url = f"{url}/api/orange"

        # 发送请求到FastAPI服务端
        try:
            send={
                    "score": score,
                    "live_city": live_city,
                    "rank": rank,
                    "want_major": want_major,
                    "unwant_major": unwant_major,
                    "hobby":hobby,
                    "future_goal": future_goal,
                    "strategy": strategy,
                    "subjects": subjects,
                      }
            response=httpx.post(
                f"{api_url}/student",
                headers={"Content-Type": "application/json; charset=utf-8"},
                json=send
            )
            response.raise_for_status()  # 检查请求是否成功
            st.success("信息已提交！请稍等片刻，系统将为您推荐合适的专业。")
            st.write("正在处理，请稍候")
            #获取后端回复
            r1 = httpx.post(
                f"{api_url}/smart_recommend",
                headers={"Content-Type": "application/json; charset=utf-8"},
                json={},
                timeout=3600
            )
            if r1.status_code == 200:  # 请求成功
                try:
                    response_data = r1.json()  # 尝试解析JSON响应
                    if response_data:  # 如果响应数据不为空
                        st.write("已获取到院校推荐结果，请点击“获取志愿结果”前往查看🍊")  # 输出yes
                    else:
                        st.warning("后端返回了空数据")
                except ValueError:  # 如果响应不是有效的JSON
                    st.error("响应不是有效的JSON格式")

        except Exception as e:
            st.error(f"发送失败：{str(e)}")

#主程序
if st.session_state.Current_page == 'page1':
    page_1()
elif st.session_state.Current_page == 'page2':
    page_2()

