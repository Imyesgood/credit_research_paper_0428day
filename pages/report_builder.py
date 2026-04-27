"""Page 4: Report Builder — session_state 저장 (클라우드 호환)"""
import streamlit as st
import pandas as pd
from datetime import datetime
from data.loader import TENOR_LABELS, get_spread
from scoring.engine import compute_score
from assets.styles import DEEP_GREEN, LEAF_GREEN, GRAY


def _load_report() -> dict:
    return st.session_state.get('report_data', {})


def _save_report(data: dict):
    data['last_saved'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    st.session_state['report_data'] = data


def _auto_generate_comment(df, cat, tenor, sp_base):
    s = df[(df['category'] == cat) & (df['tenor'] == tenor)]
    if len(s) == 0:
        return "데이터 없음"
    ys = s.set_index('date')['yield'].sort_index()
    sp_df = get_spread(df, cat, sp_base, tenor)
    sp_series = sp_df.set_index('date')['spread'] if len(sp_df) > 0 else None
    sc = compute_score(ys, sp_series)
    last_yield = ys.iloc[-1]
    prev_1m_yield = ys.iloc[-22] if len(ys) >= 22 else ys.iloc[0]
    mom_bp = (last_yield - prev_1m_yield) * 100
    pct = sc['rate_pct'] * 100
    return f"""[{cat} | {tenor}]
현재 금리: {last_yield:.3f}% (1Y 분위 {pct:.0f}%ile)
전월 대비: {'+' if mom_bp >= 0 else ''}{mom_bp:.1f}bp {'상승' if mom_bp >= 0 else '하락'}
투자의견: {sc['view']} (Score: {sc['total_score']})
{sc['comment']}"""


def render(df: pd.DataFrame):
    st.header("Report Builder")
    st.caption("자동 생성 후 수동 수정 가능")

    all_cats = sorted(df['category'].unique().tolist())
    default_base = next((c for c in all_cats if '국고채' in c or '공사/공단채 AAA' in c), all_cats[0])

    saved = _load_report()
    if saved.get('last_saved'):
        st.info(f"마지막 저장: {saved['last_saved']}")

    with st.sidebar:
        st.markdown("### 리포트 설정")
        report_tenor = st.selectbox("기준 만기", TENOR_LABELS, index=TENOR_LABELS.index('3Y'), key='rp_tenor')
        sp_base_rp = st.selectbox("스프레드 기준", all_cats,
                                   index=all_cats.index(default_base) if default_base in all_cats else 0,
                                   key='rp_sp_base')
        report_date = datetime.now().strftime('%Y년 %m월')

    tab1, tab2, tab3 = st.tabs(["Market Overview", "섹터별 의견", "전략 요약"])

    with tab1:
        st.markdown("#### 시장 총평")
        if st.button("자동 생성", key='auto_overview'):
            sample_cats = [c for c in all_cats if '회사채 AA-' in c or '회사채 AA+' in c or '은행채 AAA' in c][:3]
            auto_lines = []
            for cc in sample_cats:
                s = df[(df['category'] == cc) & (df['tenor'] == report_tenor)]
                if len(s) > 0:
                    ys = s.set_index('date')['yield'].sort_index()
                    sc = compute_score(ys)
                    last = ys.iloc[-1]
                    auto_lines.append(f"- {cc}: {last:.3f}% | {sc['view']}")
            auto_text = f"""{report_date} 크레딧 채권 시장 총평

국내 크레딧 채권 시장은 금리 변동성이 지속되는 가운데, 섹터별 스프레드 차별화가 나타나고 있다.

주요 지표 현황 ({report_tenor} 기준):
""" + '\n'.join(auto_lines) + """

시장 전반의 투자 환경은 [시장 상황에 따라 수정]하며,
향후 [전망 내용]이 예상된다."""
            st.session_state['overview_text'] = auto_text

        overview = st.text_area("시장 총평",
            value=st.session_state.get('overview_text', saved.get('overview', '')),
            height=350, key='overview_input', label_visibility='collapsed')

    with tab2:
        st.markdown("#### 섹터별 투자의견")
        report_cats = st.multiselect("분석 카테고리 선택", all_cats,
            default=saved.get('report_cats', [c for c in all_cats if '회사채' in c][:5]),
            key='report_cats')

        if st.button("전체 자동 생성", key='auto_sector'):
            for cc in report_cats:
                st.session_state[f'sector_{cc}'] = _auto_generate_comment(df, cc, report_tenor, sp_base_rp)

        sector_texts = {}
        for cc in report_cats:
            st.markdown("---")
            s = df[(df['category'] == cc) & (df['tenor'] == report_tenor)]
            if len(s) > 0:
                ys = s.set_index('date')['yield'].sort_index()
                sc = compute_score(ys)
                vcol = {'OW': '#1B5E20', 'NW': '#616161', 'UW': '#C62828'}[sc['view']]
                vbg  = {'OW': '#E8F5E9', 'NW': '#F5F5F5', 'UW': '#FFEBEE'}[sc['view']]
                header_col, auto_col = st.columns([4, 1])
                with header_col:
                    st.markdown(f"""<div style="display:flex;align-items:center;gap:10px">
                        <span style="font-weight:700;color:{DEEP_GREEN};font-size:15px">{cc}</span>
                        <span style="background:{vbg};color:{vcol};border-radius:12px;padding:2px 12px;font-weight:900;font-size:14px">{sc['view']}</span>
                        <span style="color:{GRAY};font-size:12px">Score: {sc['total_score']}</span>
                    </div>""", unsafe_allow_html=True)
                with auto_col:
                    if st.button("자동", key=f'auto_{cc}', help="자동 생성"):
                        st.session_state[f'sector_{cc}'] = _auto_generate_comment(df, cc, report_tenor, sp_base_rp)

            default_val = st.session_state.get(f'sector_{cc}', saved.get(f'sector_{cc}', ''))
            if not default_val and len(s) > 0:
                default_val = _auto_generate_comment(df, cc, report_tenor, sp_base_rp)
            sector_texts[cc] = st.text_area(f"{cc} 코멘트", value=default_val,
                height=150, key=f'sector_input_{cc}', label_visibility='collapsed')

    with tab3:
        st.markdown("#### 전략 요약 및 투자의견")
        if st.button("자동 생성", key='auto_strategy'):
            ow_cats, uw_cats, nw_cats = [], [], []
            for cc in (report_cats if report_cats else all_cats[:10]):
                s = df[(df['category'] == cc) & (df['tenor'] == report_tenor)]
                if len(s) > 0:
                    ys = s.set_index('date')['yield'].sort_index()
                    sc = compute_score(ys)
                    {'OW': ow_cats, 'UW': uw_cats, 'NW': nw_cats}[sc['view']].append(cc)
            strategy_auto = f"""{report_date} 크레딧 채권 전략 요약

■ Overweight (OW)
{chr(10).join('- ' + c for c in ow_cats) if ow_cats else '- 해당 없음'}

■ Neutral Weight (NW)
{chr(10).join('- ' + c for c in nw_cats) if nw_cats else '- 해당 없음'}

■ Underweight (UW)
{chr(10).join('- ' + c for c in uw_cats) if uw_cats else '- 해당 없음'}

■ 핵심 전략
[전략 내용을 여기에 수정 입력]

■ 주요 리스크
- [리스크 1]
- [리스크 2]"""
            st.session_state['strategy_text'] = strategy_auto

        strategy = st.text_area("전략 요약",
            value=st.session_state.get('strategy_text', saved.get('strategy', '')),
            height=450, key='strategy_input', label_visibility='collapsed')

    st.markdown("---")
    col_s1, col_s2, _ = st.columns([1, 1, 4])
    with col_s1:
        if st.button("저장", type='primary', use_container_width=True, key='save_report'):
            data = {
                'overview': st.session_state.get('overview_input', ''),
                'strategy': st.session_state.get('strategy_input', ''),
                'report_cats': st.session_state.get('report_cats', []),
            }
            for cc in report_cats:
                data[f'sector_{cc}'] = st.session_state.get(f'sector_input_{cc}', '')
            _save_report(data)
            st.success("저장 완료!")
            st.rerun()

    st.markdown("---")
    with st.expander("리포트 전체 미리보기"):
        preview_text = f"""{'='*60}
크레딧 채권 리서치 | {report_date}
{'='*60}

【시장 총평】
{st.session_state.get('overview_input', saved.get('overview', ''))}

【섹터별 의견】
"""
        for cc in report_cats:
            v = st.session_state.get(f'sector_input_{cc}', saved.get(f'sector_{cc}', ''))
            if v:
                preview_text += f"\n{v}\n"
        preview_text += f"""
【전략 요약】
{st.session_state.get('strategy_input', saved.get('strategy', ''))}

{'='*60}
생성일: {datetime.now().strftime('%Y-%m-%d %H:%M')}
"""
        st.text_area("미리보기", value=preview_text, height=600, label_visibility='collapsed')
        st.download_button("텍스트 다운로드", preview_text,
                           file_name=f"credit_research_{datetime.now().strftime('%Y%m%d')}.txt",
                           mime='text/plain')
