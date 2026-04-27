"""Page 3: Credit Flow — session_state 저장 (클라우드 호환)"""
import streamlit as st
from datetime import datetime
from assets.styles import DEEP_GREEN, LEAF_GREEN, GRAY


def _load_saved() -> dict:
    return st.session_state.get('credit_flow_data', {
        'issuance': '', 'demand': '', 'rating_changes': '',
        'news': '', 'memo': '', 'last_saved': '',
    })


def _save_data(data: dict):
    data['last_saved'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    st.session_state['credit_flow_data'] = data


def render(_=None):
    st.header("Credit Flow")
    st.caption("발행, 수요예측, 신용등급 변경 등 수동 입력 섹션")

    saved = _load_saved()
    if saved.get('last_saved'):
        st.info(f"마지막 저장: {saved['last_saved']}")

    tab1, tab2, tab3, tab4 = st.tabs(["발행 현황", "수요예측", "신용등급 변경", "뉴스/메모"])

    with tab1:
        st.markdown("#### 월간 발행 현황")
        st.caption("복붙 가능 | ↑↓ 방향키로 이동")
        col1, col2 = st.columns([3, 1])
        with col1:
            issuance_text = st.text_area("발행 데이터 입력", value=saved.get('issuance', ''), height=400,
                placeholder="2026-04 | 회사채 AA- | LG에너지솔루션 | 3년 | 5,000억 | 3.85%\n...",
                key='issuance_input', label_visibility='collapsed')
        with col2:
            st.markdown("##### 입력 가이드")
            st.markdown("- 날짜 | 섹터 등급 | 발행사 | 만기 | 금액 | 금리\n- 자유 형식 가능\n- 엑셀 복붙 가능")
            if issuance_text:
                lines = [l for l in issuance_text.strip().split('\n') if l.strip()]
                st.metric("총 건수", f"{len(lines)}건")

    with tab2:
        st.markdown("#### 수요예측 현황")
        col1, col2 = st.columns([3, 1])
        with col1:
            demand_text = st.text_area("수요예측 데이터", value=saved.get('demand', ''), height=400,
                placeholder="발행사 | 등급 | 만기 | 발행액 | 모집액 | 경쟁률 | 최종금리 | 비고\n...",
                key='demand_input', label_visibility='collapsed')
        with col2:
            st.markdown("##### 입력 가이드")
            st.markdown("- 발행사 | 등급 | 만기 | 발행액 | 모집액 | 경쟁률 | 금리\n- 엑셀 복붙 가능")
            if demand_text:
                lines = [l for l in demand_text.strip().split('\n') if l.strip()]
                st.metric("수요예측 건수", f"{len(lines)}건")

    with tab3:
        st.markdown("#### 신용등급 변경 내역")
        col1, col2 = st.columns([3, 1])
        with col1:
            rating_text = st.text_area("등급 변경 내역", value=saved.get('rating_changes', ''), height=400,
                placeholder="날짜 | 발행사 | 변경 전 | 변경 후 | 방향 | 평가사 | 사유\n...",
                key='rating_input', label_visibility='collapsed')
        with col2:
            st.markdown("##### 입력 가이드")
            st.markdown("- 날짜 | 발행사 | 이전등급 | 변경등급 | 방향 | 평가사\n- 엑셀 복붙 가능")
            if rating_text:
                lines = [l for l in rating_text.strip().split('\n') if l.strip()]
                st.metric("등급 변경 건수", f"{len(lines)}건")

    with tab4:
        st.markdown("#### 뉴스 / 시장 메모")
        col1, _ = st.columns([3, 1])
        with col1:
            news_text = st.text_area("뉴스/메모", value=saved.get('news', ''), height=200,
                placeholder="시장 주요 뉴스, 이슈 등 자유 입력...",
                key='news_input', label_visibility='collapsed')
            st.markdown("#### 추가 메모")
            memo_text = st.text_area("메모", value=saved.get('memo', ''), height=150,
                placeholder="기타 참고사항...",
                key='memo_input', label_visibility='collapsed')

    st.markdown("---")
    col_s1, col_s2, col_s3 = st.columns([1, 1, 4])
    with col_s1:
        if st.button("저장", type='primary', use_container_width=True):
            data = {
                'issuance': st.session_state.get('issuance_input', ''),
                'demand': st.session_state.get('demand_input', ''),
                'rating_changes': st.session_state.get('rating_input', ''),
                'news': st.session_state.get('news_input', ''),
                'memo': st.session_state.get('memo_input', ''),
            }
            _save_data(data)
            st.success("저장 완료!")
            st.rerun()
    with col_s2:
        if st.button("초기화", use_container_width=True):
            st.session_state.pop('credit_flow_data', None)
            st.rerun()
