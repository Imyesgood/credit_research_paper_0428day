"""
크레딧 리서치 자동화 앱
메인 진입점
"""
import streamlit as st
import pandas as pd
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from assets.styles import CSS, DEEP_GREEN
from data.loader import load_excel

st.set_page_config(
    page_title="Credit Research Engine",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(CSS, unsafe_allow_html=True)

with st.sidebar:
    st.html(f"""
    <div style="text-align:center; padding:16px 0 8px">
        <div style="font-weight:900; font-size:16px; color:{DEEP_GREEN}">Credit Research</div>
        <div style="font-size:11px; color:#9E9E9E">채권 크레딧 분석 엔진</div>
    </div>
    """)
    st.divider()

    st.markdown("### 데이터 업로드")
    uploaded = st.file_uploader(
        "Excel 파일 업로드",
        type=['xlsx', 'xls'],
        help="시가평가 3사평균 Wide-format Excel",
        label_visibility='collapsed',
    )

    if uploaded:
        st.success(f"업로드 완료: {uploaded.name}")
    else:
        st.info("Excel 파일을 업로드하세요")

    st.divider()

    st.markdown("### 메뉴")
    page = st.radio(
        "페이지",
        options=["Market View", "Sector Matrix", "Credit Flow", "Report Builder"],
        label_visibility='collapsed',
    )

    st.divider()
    st.caption("v0.1 | Expandable Engine")

if uploaded is None:
    st.html(f"""
    <div style="text-align:center; padding:60px 20px">
        <h1 style="color:{DEEP_GREEN}; margin-top:16px; font-size:2rem; font-weight:700">크레딧 리서치 엔진</h1>
        <p style="color:#616161; font-size:16px; margin:16px 0">
            데이터 업로드 → 자동 분석 → Score → OW/NW/UW → 코멘트 자동 생성
        </p>
    </div>
    """)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.html(f"""
        <div style="border:1px solid #D8E4D0; border-radius:8px; padding:20px; background:#F5F7F2">
            <div style="font-weight:700; color:{DEEP_GREEN}; margin-bottom:8px; font-size:15px">Market View</div>
            <div style="font-size:13px; color:#555">금리 시계열, 스프레드, 커브, MoM 변화 시각화</div>
        </div>
        """)
    with c2:
        st.html(f"""
        <div style="border:1px solid #D8E4D0; border-radius:8px; padding:20px; background:#F5F7F2">
            <div style="font-weight:700; color:{DEEP_GREEN}; margin-bottom:8px; font-size:15px">Sector Matrix</div>
            <div style="font-size:13px; color:#555">섹터 x 등급 x 만기 히트맵 + 자동 OW/NW/UW 스코어링</div>
        </div>
        """)
    with c3:
        st.html(f"""
        <div style="border:1px solid #D8E4D0; border-radius:8px; padding:20px; background:#F5F7F2">
            <div style="font-weight:700; color:{DEEP_GREEN}; margin-bottom:8px; font-size:15px">Report Builder</div>
            <div style="font-size:13px; color:#555">자동 코멘트 생성 + 수동 수정 + 텍스트 출력</div>
        </div>
        """)

    st.markdown("---")
    st.markdown("""
    **사용 방법:**
    1. 좌측 사이드바에서 Excel 파일 업로드 (시가평가 3사평균 Wide-format)
    2. 원하는 페이지 선택
    3. 필터 조정 후 차트/분석 확인
    4. Report Builder에서 코멘트 자동 생성 후 수정
    """)
    st.stop()

with st.spinner("데이터 파싱 중..."):
    try:
        df = load_excel(uploaded.getvalue())
    except Exception as e:
        st.error(f"파일 로드 오류: {e}")
        st.stop()

with st.sidebar:
    st.html(f"""
    <div style="background:#E8F5E9; border-radius:6px; padding:10px; font-size:11px; color:#333">
        {df['date'].min().strftime('%Y-%m-%d')} ~ {df['date'].max().strftime('%Y-%m-%d')}<br>
        계열 {df['category'].nunique()}개 &nbsp;|&nbsp; {len(df):,}개 데이터포인트
    </div>
    """)

if page == "Market View":
    from pages.market_view import render
    render(df)
elif page == "Sector Matrix":
    from pages.sector_matrix import render
    render(df)
elif page == "Credit Flow":
    from pages.credit_flow import render
    render(df)
elif page == "Report Builder":
    from pages.report_builder import render
    render(df)