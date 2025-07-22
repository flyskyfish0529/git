import streamlit as st
pages=st.navigation(
        [st.Page("MBTIfront.py", title="主页"),
         st.Page("mbti_test_home.py", title="MBTI简介"),
         st.Page("MBTI_test.py", title="MBTI测试"),
         ]
        )
pages.run()

