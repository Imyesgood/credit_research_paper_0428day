"""Page 5: Signal Dashboard — Duration / Curve / Credit 투자의견 자동 생성"""
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import datetime
from data.loader import TENOR_LABELS
from assets.styles import DEEP_GREEN, LEAF_GREEN, CORAL, PLOTLY_TEMPLATE

# ── 색상 / 뱃지 설정 ────────────────────────────────────────────
VIEW_CFG = {
    'OW': {'label': '비중확대', 'emoji': '▲', 'bg': '#E8F5E9', 'fg': '#1B5E20', 'border': '#66BB6A'},
    'NW': {'label': '중립',     'emoji': '—', 'bg': '#F5F5F5', 'fg': '#424242', 'border': '#BDBDBD'},
    'UW': {'label': '비중축소', 'emoji': '▼', 'bg': '#FFEBEE', 'fg': '#B71C1C', 'border': '#EF9A9A'},
}

# ── 시그널 임계값 (수정 가능) ──────────────────────────────────
DURATION_THRESH_BP = 10    # 주간 금리변화 ±bp
CURVE_THRESH_BP    = 10    # 주간 커브변화 ±bp
CREDIT_THRESH_BP   = 15    # 주간 스프레드변화 ±bp


# ─────────────────────────────────────────────────────────────────
# 시그널 계산 함수
# ─────────────────────────────────────────────────────────────────
def _get_series(df: pd.DataFrame, category: str, tenor: str) -> pd.Series:
    s = df[(df['category'] == category) & (df['tenor'] == tenor)]
    return s.set_index('date')['yield'].sort_index().dropna()


def _weekly_change(series: pd.Series, days: int = 5) -> float:
    """영업일 기준 5일 전 대비 변화 (bp)"""
    if len(series) < 2:
        return np.nan
    current = series.iloc[-1]
    prev    = series.iloc[-days] if len(series) > days else series.iloc[0]
    return (current - prev) * 100


def _signal_duration(df: pd.DataFrame, gov_cat: str, tenor: str = '3Y',
                     thresh: float = 10) -> dict:
    s = _get_series(df, gov_cat, tenor)
    if s.empty:
        return {'view': 'NW', 'chg_bp': np.nan, 'current': np.nan, 'series': s}
    chg = _weekly_change(s)
    if   np.isnan(chg):      view = 'NW'
    elif chg <= -thresh:     view = 'OW'
    elif chg >= +thresh:     view = 'UW'
    else:                    view = 'NW'
    return {'view': view, 'chg_bp': chg, 'current': s.iloc[-1], 'series': s}


def _signal_curve(df: pd.DataFrame, gov_cat: str,
                  long_tenor: str = '5Y', short_tenor: str = '1Y',
                  thresh: float = 10) -> dict:
    s_long  = _get_series(df, gov_cat, long_tenor)
    s_short = _get_series(df, gov_cat, short_tenor)
    idx = s_long.index.intersection(s_short.index)
    if len(idx) == 0:
        return {'view': 'NW', 'chg_bp': np.nan, 'slope_bp': np.nan,
                'series': pd.Series(dtype=float), 'label': f'{long_tenor}-{short_tenor}'}
    slope = ((s_long - s_short) * 100).reindex(idx).dropna()
    chg   = _weekly_change(slope)
    slope_now = slope.iloc[-1] if len(slope) else np.nan
    if   np.isnan(chg):    view = 'NW'
    elif chg >= +thresh:   view = 'OW'
    elif chg <= -thresh:   view = 'UW'
    else:                  view = 'NW'
    return {'view': view, 'chg_bp': chg, 'slope_bp': slope_now, 'series': slope,
            'label': f'{long_tenor}-{short_tenor}'}


def _signal_credit(df: pd.DataFrame, credit_cat: str,
                   gov_cat: str, tenor: str = '3Y',
                   thresh: float = 15) -> dict:
    s_cr  = _get_series(df, credit_cat, tenor)
    s_gov = _get_series(df, gov_cat, tenor)
    idx   = s_cr.index.intersection(s_gov.index)
    if len(idx) == 0:
        return {'view': 'NW', 'chg_bp': np.nan, 'spread_bp': np.nan,
                'series': pd.Series(dtype=float)}
    spread = ((s_cr - s_gov) * 100).reindex(idx).dropna()
    chg    = _weekly_change(spread)
    sp_now = spread.iloc[-1] if len(spread) else np.nan
    if   np.isnan(chg):    view = 'NW'
    elif chg >= +thresh:   view = 'UW'
    elif chg <= -thresh:   view = 'OW'
    else:                  view = 'NW'
    return {'view': view, 'chg_bp': chg, 'spread_bp': sp_now, 'series': spread}


# ─────────────────────────────────────────────────────────────────
# UI 컴포넌트
# ─────────────────────────────────────────────────────────────────
def _badge(view: str, large: bool = False) -> str:
    c = VIEW_CFG[view]
    fs = '20px' if large else '13px'
    pad = '10px 20px' if large else '3px 12px'
    return (f'<span style="background:{c["bg"]};color:{c["fg"]};border:1px solid {c["border"]};'
            f'border-radius:6px;padding:{pad};font-weight:700;font-size:{fs}">'
            f'{c["emoji"]} {c["label"]}</span>')


def _signal_card(title: str, sig: dict, detail_lines: list[str]):
    c = VIEW_CFG[sig['view']]
    lines_html = ''.join(
        f'<div style="margin:3px 0;font-size:12px;color:#555">{l}</div>'
        for l in detail_lines
    )
    st.markdown(f"""
<div style="border:1px solid {c['border']};border-radius:8px;padding:18px 20px;
            background:{c['bg']};height:100%">
  <div style="font-size:12px;color:#777;margin-bottom:6px;font-weight:500">{title}</div>
  <div style="font-size:22px;font-weight:800;color:{c['fg']};margin-bottom:10px">
    {c['emoji']} {c['label']}
  </div>
  {lines_html}
</div>""", unsafe_allow_html=True)


def _time_series_chart(series_dict: dict, title: str, y_suffix: str,
                       height: int = 280, ref_line: float = None) -> go.Figure:
    colors = [DEEP_GREEN, '#4A5E35', '#9A7085', '#005F73', CORAL]
    fig = go.Figure()
    for i, (name, s) in enumerate(series_dict.items()):
        if s is None or len(s) == 0:
            continue
        fig.add_trace(go.Scatter(
            x=s.index, y=s.values, name=name,
            line=dict(color=colors[i % len(colors)], width=2),
            hovertemplate=f'{name}: %{{y:.2f}}{y_suffix}<extra></extra>',
        ))
    if ref_line is not None:
        fig.add_hline(y=ref_line, line_dash='dash', line_color='#BDBDBD', line_width=1)

    fig.update_layout(
        template=PLOTLY_TEMPLATE, height=height,
        title=dict(text=f'<b>{title}</b>', font=dict(color=DEEP_GREEN, size=13), x=0),
        font=dict(family='Apple SD Gothic Neo, Noto Sans KR, sans-serif', size=11),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1,
                    font=dict(size=10), bgcolor='rgba(255,255,255,0.8)',
                    bordercolor='#E0E0E0', borderwidth=1),
        margin=dict(l=55, r=20, t=50, b=36),
        plot_bgcolor='white', paper_bgcolor='white', hovermode='x unified',
    )
    fig.update_xaxes(showgrid=False, showline=True, linecolor='#BDBDBD')
    fig.update_yaxes(showgrid=True, gridcolor='#EEEEEE', ticksuffix=y_suffix,
                     zeroline=True, zerolinecolor='#CCCCCC', zerolinewidth=1.2)
    return fig


# ─────────────────────────────────────────────────────────────────
# 메인 렌더
# ─────────────────────────────────────────────────────────────────
def render(df: pd.DataFrame):
    st.header("Signal Dashboard")
    st.caption("섹터별 만기별 금리 데이터 → Duration / Curve / Credit 투자의견 자동 산출")

    all_cats = sorted(df['category'].unique().tolist())
    gov_cat  = next((c for c in all_cats if '국고채' in c), None)
    if gov_cat is None:
        st.error("국고채 데이터가 없습니다.")
        return

    # ── 날짜 필터 ──────────────────────────────────────────────
    min_d = df['date'].min().date()
    max_d = df['date'].max().date()
    with st.expander("📅 분석 기간 설정", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            start_d = st.date_input("시작일",
                                    value=max(max_d - datetime.timedelta(days=180), min_d),
                                    min_value=min_d, max_value=max_d, key='sig_start')
        with c2:
            end_d = st.date_input("종료일", value=max_d,
                                  min_value=min_d, max_value=max_d, key='sig_end')
    dff = df[(df['date'] >= pd.Timestamp(start_d)) & (df['date'] <= pd.Timestamp(end_d))]

    # ── 임계값 설정 ────────────────────────────────────────────
    with st.expander("⚙️ 시그널 임계값 조정", expanded=False):
        t1, t2, t3 = st.columns(3)
        dur_t = t1.number_input("Duration 임계값 (bp)", value=10,
                                min_value=1, max_value=50, key='dur_t')
        cur_t = t2.number_input("Curve 임계값 (bp)",    value=10,
                                min_value=1, max_value=50, key='cur_t')
        crd_t = t3.number_input("Credit 임계값 (bp)",   value=15,
                                min_value=1, max_value=50, key='crd_t')

    # ── 신호 계산 옵션 ─────────────────────────────────────────
    st.markdown("---")
    o1, o2, o3 = st.columns(3)
    with o1:
        dur_tenor = st.selectbox("Duration 기준 만기", ['3Y','5Y','2Y','1Y'],
                                  key='dur_tenor')
    with o2:
        curve_long  = st.selectbox("커브 장기단", ['5Y','3Y','4Y'], key='cur_long')
        curve_short = st.selectbox("커브 단기단", ['1Y','6M','2Y'], key='cur_short')
    with o3:
        credit_cats_avail = [c for c in all_cats if '국고채' not in c]
        credit_tenor = st.selectbox("Credit 기준 만기", ['3Y','5Y','2Y'], key='crd_tenor')

    # ── 시그널 계산 ────────────────────────────────────────────
    sig_dur = _signal_duration(dff, gov_cat, dur_tenor, dur_t)
    sig_cur = _signal_curve(dff, gov_cat, curve_long, curve_short, cur_t)

    rep_credit_cats = [c for c in all_cats if any(x in c for x in
                       ['공사/공단채 AAA', '회사채 AA-', '카드채 AA'])][:3]

    sig_credits = {cat: _signal_credit(dff, cat, gov_cat, credit_tenor, crd_t)
                   for cat in rep_credit_cats}

    # 대표 크레딧 합산 시그널 (majority vote)
    credit_views = [v['view'] for v in sig_credits.values()]
    rep_credit_view = max(set(credit_views), key=credit_views.count) if credit_views else 'NW'
    rep_credit_chg  = np.nanmean([v['chg_bp'] for v in sig_credits.values()])

    # ── 최신 날짜 표시 ─────────────────────────────────────────
    latest = dff['date'].max()
    st.markdown(
        f"<div style='font-size:12px;color:#888;margin-bottom:8px'>"
        f"기준일: <b>{latest.strftime('%Y-%m-%d')}</b> | "
        f"주간변화 = 최근 5영업일 기준</div>",
        unsafe_allow_html=True
    )

    # ══════════════════════════════════════════════════════════════
    # 상단 3개 시그널 카드
    # ══════════════════════════════════════════════════════════════
    c1, c2, c3 = st.columns(3)
    with c1:
        chg_str = f"{sig_dur['chg_bp']:+.1f}bp" if not np.isnan(sig_dur['chg_bp']) else "-"
        lvl_str = f"{sig_dur['current']:.3f}%" if not np.isnan(sig_dur['current']) else "-"
        _signal_card(
            f"Duration  ({gov_cat} {dur_tenor})",
            sig_dur,
            [f"현재 금리: {lvl_str}",
             f"주간 변화: {chg_str}",
             f"임계값: ±{DURATION_THRESH_BP}bp"],
        )
    with c2:
        chg_str = f"{sig_cur['chg_bp']:+.1f}bp" if not np.isnan(sig_cur['chg_bp']) else "-"
        sl_str  = f"{sig_cur['slope_bp']:+.1f}bp" if not np.isnan(sig_cur['slope_bp']) else "-"
        _signal_card(
            f"Curve  ({curve_long}-{curve_short})",
            sig_cur,
            [f"현재 Slope: {sl_str}",
             f"주간 변화: {chg_str}",
             f"임계값: ±{CURVE_THRESH_BP}bp"],
        )
    with c3:
        chg_str = f"{rep_credit_chg:+.1f}bp" if not np.isnan(rep_credit_chg) else "-"
        _signal_card(
            f"Credit  ({credit_tenor} 스프레드, 평균)",
            {'view': rep_credit_view},
            [f"주간 변화: {chg_str}",
             f"임계값: ±{CREDIT_THRESH_BP}bp",
             f"대상: {len(rep_credit_cats)}개 계열"],
        )

    # ── 포지션 요약 한 줄 ──────────────────────────────────────
    def _view_label(v):
        return {'OW': '비중확대↑', 'NW': '중립', 'UW': '비중축소↓'}[v]

    st.markdown("---")
    summary_bg = '#F5F7F2'
    st.markdown(f"""
<div style="background:{summary_bg};border-radius:8px;padding:16px 20px;
            border-left:4px solid {DEEP_GREEN};margin-bottom:8px">
  <div style="font-size:11px;color:#888;margin-bottom:6px">📌 종합 포지션 요약</div>
  <div style="font-size:14px;font-weight:600;color:{DEEP_GREEN}">
    Duration: {_view_label(sig_dur['view'])} &nbsp;|&nbsp;
    Curve: {_view_label(sig_cur['view'])} &nbsp;|&nbsp;
    Credit: {_view_label(rep_credit_view)}
  </div>
</div>""", unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════
    # 섹터별 크레딧 시그널 테이블
    # ══════════════════════════════════════════════════════════════
    st.markdown("#### 섹터별 크레딧 시그널")

    sel_credit_cats = st.multiselect(
        "분석 계열 (vs 국고채)", credit_cats_avail,
        default=credit_cats_avail[:min(6, len(credit_cats_avail))],
        key='sig_credit_cats',
    )

    if sel_credit_cats:
        rows = []
        for cat in sel_credit_cats:
            sig = _signal_credit(dff, cat, gov_cat, credit_tenor, crd_t)
            rows.append({
                '계열': cat,
                '현재 스프레드': f"{sig['spread_bp']:.1f}bp" if not np.isnan(sig.get('spread_bp', np.nan)) else '-',
                '주간 변화': f"{sig['chg_bp']:+.1f}bp" if not np.isnan(sig.get('chg_bp', np.nan)) else '-',
                '투자의견': sig['view'],
            })

        # 색깔 있는 HTML 테이블
        html = """<style>
.st{border-collapse:collapse;width:100%;font-size:12px;font-family:'Apple SD Gothic Neo',sans-serif}
.st th{background:#2D3F38;color:#fff;padding:8px 12px;text-align:left}
.st td{padding:7px 12px;border-bottom:1px solid #EEEEEE}
.st tr:hover td{background:#F5F7F2}
.ow{color:#1B5E20;font-weight:700} .nw{color:#424242} .uw{color:#B71C1C;font-weight:700}
</style><table class="st"><thead><tr>
<th>계열</th><th>현재 스프레드</th><th>주간 변화</th><th>투자의견</th>
</tr></thead><tbody>"""
        for r in rows:
            v = r['투자의견']
            cls = {'OW': 'ow', 'NW': 'nw', 'UW': 'uw'}[v]
            label = VIEW_CFG[v]['label']
            emoji = VIEW_CFG[v]['emoji']
            html += (f'<tr><td>{r["계열"]}</td>'
                     f'<td>{r["현재 스프레드"]}</td>'
                     f'<td>{r["주간 변화"]}</td>'
                     f'<td class="{cls}">{emoji} {label}</td></tr>')
        html += '</tbody></table>'
        st.markdown(html, unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════
    # 시계열 차트
    # ══════════════════════════════════════════════════════════════
    st.markdown("---")
    st.markdown("#### 시계열 차트")

    tab1, tab2, tab3 = st.tabs(["금리 레벨", "커브 Slope", "크레딧 스프레드"])

    with tab1:
        gov_tenors = ['1Y', '3Y', '5Y']
        series_dict = {}
        for tn in gov_tenors:
            s = _get_series(dff, gov_cat, tn)
            if len(s): series_dict[f'{gov_cat} {tn}'] = s * 100  # % → 그대로, suffix '%'
        # 실제로 yield는 이미 %이므로 그대로 씀
        series_dict2 = {k: v / 100 for k, v in series_dict.items()}
        fig = _time_series_chart(
            {k: _get_series(dff, gov_cat, tn)
             for tn, k in zip(gov_tenors, [f'{gov_cat} {t}' for t in gov_tenors])
             if len(_get_series(dff, gov_cat, tn))},
            f'{gov_cat} 금리', '%', height=300,
        )
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        s_long  = _get_series(dff, gov_cat, curve_long)
        s_short = _get_series(dff, gov_cat, curve_short)
        idx = s_long.index.intersection(s_short.index)
        if len(idx):
            slope = (s_long - s_short).reindex(idx) * 100
            fig = _time_series_chart(
                {f'Slope {curve_long}-{curve_short}': slope},
                f'커브 Slope  ({gov_cat})', 'bp', height=300, ref_line=0,
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("커브 데이터 없음")

    with tab3:
        sp_dict = {}
        for cat in (sel_credit_cats or rep_credit_cats)[:5]:
            sig = _signal_credit(dff, cat, gov_cat, credit_tenor, crd_t)
            if len(sig['series']):
                sp_dict[cat] = sig['series']
        if sp_dict:
            fig = _time_series_chart(sp_dict, f'크레딧 스프레드 vs {gov_cat} ({credit_tenor})',
                                     'bp', height=300, ref_line=0)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("스프레드 데이터 없음")

    # ══════════════════════════════════════════════════════════════
    # 시그널 히스토리 (최근 20영업일)
    # ══════════════════════════════════════════════════════════════
    st.markdown("---")
    st.markdown("#### 시그널 히스토리 (최근 20영업일)")

    avail_dates = sorted(dff['date'].unique(), reverse=True)[:20]
    hist_rows = []
    for d in avail_dates:
        sub = dff[dff['date'] <= d]
        if len(sub) < 6:
            continue
        sd  = _signal_duration(sub, gov_cat, dur_tenor, dur_t)
        sc  = _signal_curve(sub, gov_cat, curve_long, curve_short, cur_t)
        # 대표 크레딧
        cv  = [_signal_credit(sub, c, gov_cat, credit_tenor, crd_t)['view']
               for c in rep_credit_cats if len(_get_series(sub, c, credit_tenor))]
        crv = max(set(cv), key=cv.count) if cv else 'NW'
        hist_rows.append({
            '날짜': d.strftime('%Y-%m-%d'),
            'Duration': VIEW_CFG[sd['view']]['emoji'] + ' ' + VIEW_CFG[sd['view']]['label'],
            'Curve':    VIEW_CFG[sc['view']]['emoji'] + ' ' + VIEW_CFG[sc['view']]['label'],
            'Credit':   VIEW_CFG[crv]['emoji']        + ' ' + VIEW_CFG[crv]['label'],
            'dur_v': sd['view'], 'cur_v': sc['view'], 'crd_v': crv,
        })

    if hist_rows:
        html2 = """<style>
.ht{border-collapse:collapse;width:100%;font-size:12px;font-family:'Apple SD Gothic Neo',sans-serif}
.ht th{background:#2D3F38;color:#fff;padding:7px 14px;text-align:center}
.ht td{padding:6px 14px;border-bottom:1px solid #EEEEEE;text-align:center}
.ht tr:hover td{background:#F5F7F2}
.ow2{color:#1B5E20;font-weight:700}.nw2{color:#777}.uw2{color:#B71C1C;font-weight:700}
</style><table class="ht"><thead><tr>
<th>날짜</th><th>Duration</th><th>Curve</th><th>Credit</th>
</tr></thead><tbody>"""
        for r in hist_rows:
            cls = {'OW': 'ow2', 'NW': 'nw2', 'UW': 'uw2'}
            html2 += (f'<tr><td>{r["날짜"]}</td>'
                      f'<td class="{cls[r["dur_v"]]}">{r["Duration"]}</td>'
                      f'<td class="{cls[r["cur_v"]]}">{r["Curve"]}</td>'
                      f'<td class="{cls[r["crd_v"]]}">{r["Credit"]}</td></tr>')
        html2 += '</tbody></table>'
        st.markdown(html2, unsafe_allow_html=True)