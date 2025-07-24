import streamlit as st
MBTI_pages=st.navigation({
        "MBTI":[st.Page("MBTI/MBTI_test_entrance.py", title="主页"),
         st.Page("MBTI/MBTI_home.py", title="MBTI简介"),
         st.Page("MBTI/MBTI_test.py", title="MBTI测试"),
         ]
})
MBTI_pages.run()

