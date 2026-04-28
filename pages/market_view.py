"""Page 1: Market View — 날짜 직접 선택 + 차트 수정"""
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import datetime
from data.loader import TENOR_LABELS
from assets.styles import DEEP_GREEN, OLIVE, LEAF_GREEN, CORAL, HEATMAP_DIVERG, PLOTLY_TEMPLATE


COLORS_LINE  = ['#2D3F38', '#4A5E35', '#9A7085', '#005F73', '#8A3030', '#4E9B5A']
GREEN_SHADES = ['#2D3F38', '#4A5E35', '#4E9B5A', '#8DC175', '#8DD5C8', '#DDE8C0',
                '#8DB8A5', '#9A7085', '#8A9E96', '#B0BDB4']
TENOR_ORDER_MAP = {t: i for i, t in enumerate(TENOR_LABELS)}
COLOR_POS = '#4A5E35'
COLOR_NEG  = '#E87070'


def _base_layout(fig, title="", height=420):
    fig.update_layout(
        template=PLOTLY_TEMPLATE, height=height,
        title=dict(text=f"<b>{title}</b>",
                   font=dict(color=DEEP_GREEN, size=14), x=0),
        font=dict(family="Apple SD Gothic Neo, Noto Sans KR, sans-serif", size=12),
        legend=dict(
            orientation='h', yanchor='bottom', y=1.02,
            xanchor='right', x=1, font=dict(size=11),
            bgcolor='rgba(255,255,255,0.85)',
            bordercolor='#E0E0E0', borderwidth=1,
        ),
        margin=dict(l=65, r=75, t=64, b=44),
        plot_bgcolor='white', paper_bgcolor='white', hovermode='x unified',
    )
    fig.update_xaxes(
        showgrid=False,
        showline=True, linecolor='#BDBDBD', linewidth=1.5,
        tickfont=dict(size=12),
    )
    fig.update_yaxes(
        showgrid=True, gridcolor='#EEEEEE', gridwidth=1,
        tickfont=dict(size=11),
        title_font=dict(size=11, color='#555'),
    )
    return fig


def _date_range_picker(df: pd.DataFrame, key: str, default_days: int = 365):
    """시작일 / 종료일 직접 입력 (캘린더 피커)"""
    min_d = df['date'].min().date()
    max_d = df['date'].max().date()
    default_start = max(max_d - datetime.timedelta(days=default_days), min_d)
    c1, c2 = st.columns(2)
    with c1:
        start_d = st.date_input("시작일", value=default_start,
                                min_value=min_d, max_value=max_d,
                                key=f'{key}_start')
    with c2:
        end_d = st.date_input("종료일", value=max_d,
                              min_value=min_d, max_value=max_d,
                              key=f'{key}_end')
    if start_d > end_d:
        st.warning("시작일이 종료일보다 늦습니다.")
        start_d, end_d = end_d, start_d
    return pd.Timestamp(start_d), pd.Timestamp(end_d)



# ── 탭1: 변동 요약표 ──────────────────────────────────────────────
def _render_summary_table(df: pd.DataFrame):
    st.markdown("#### 채권 금리 및 스프레드 변동 요약")
    all_cats = sorted(df['category'].unique().tolist())
    target_tenors = ['6M', '1Y', '2Y', '3Y', '5Y']

    cf1, cf2 = st.columns([4, 2])
    with cf1:
        sel_cats = st.multiselect(
            "표시 계열", all_cats,
            default=[c for c in all_cats if any(x in c for x in
                ['공사/공단채 AAA', '은행채 AAA', '카드채 AA', '회사채 AA-', '회사채 AA'])][:6],
            key='table_cats')
    with cf2:
        ref_cat = st.selectbox(
            "스프레드 기준", all_cats,
            index=next((i for i, c in enumerate(all_cats)
                        if '국고채' in c or '공사/공단채 AAA' in c), 0),
            key='table_ref')

    if not sel_cats:
        st.info("계열을 선택하세요")
        return

    ref_y, ref_y1m = {}, {}
    for tn in target_tenors:
        s = df[(df['category'] == ref_cat) & (df['tenor'] == tn)].sort_values('date')
        ref_y[tn]   = s.iloc[-1]['yield'] if len(s) > 0 else np.nan
        ref_y1m[tn] = s.iloc[-22]['yield'] if len(s) >= 22 else np.nan

    rows = []
    for cat in sel_cats:
        sub = df[df['category'] == cat]
        row = {'섹터': sub['sector'].iloc[0] if len(sub) > 0 else '',
               '등급': sub['rating'].iloc[0] if len(sub) > 0 else ''}
        for tn in target_tenors:
            s   = df[(df['category'] == cat) & (df['tenor'] == tn)].sort_values('date')
            cur = s.iloc[-1]['yield'] if len(s) > 0 else np.nan
            cur1m = s.iloc[-22]['yield'] if len(s) >= 22 else np.nan
            row[f'금리_{tn}'] = round(cur, 2) if not np.isnan(cur) else None
            sp = ((cur - ref_y[tn]) * 100
                  if not np.isnan(cur) and not np.isnan(ref_y.get(tn, np.nan)) else None)
            row[f'sp_{tn}'] = round(sp, 1) if sp is not None else None
            if sp is not None and not np.isnan(cur1m) and not np.isnan(ref_y1m.get(tn, np.nan)):
                row[f'mom_{tn}'] = round(sp - (cur1m - ref_y1m[tn]) * 100, 1)
            else:
                row[f'mom_{tn}'] = None
        rows.append(row)

    html = """<style>
.ct{border-collapse:collapse;width:100%;font-size:11.5px;font-family:'Apple SD Gothic Neo',sans-serif}
.ct th{background:#1B5E20;color:#fff;padding:5px 7px;text-align:center;border:1px solid #388E3C}
.ct th.sub{background:#2E7D32;font-size:10px}
.ct td{padding:4px 7px;text-align:center;border:1px solid #E0E0E0}
.ct tr:nth-child(even) td{background:#F9FBE7}.ct tr:nth-child(odd) td{background:#fff}
.ct .neg{color:#C62828;font-weight:700}.ct .pos{color:#4E9B5A;font-weight:700}
.ct .cat{background:#E8F5E9!important;font-weight:700;color:#1B5E20;text-align:left}
</style><table class="ct"><thead><tr>
<th rowspan="2">섹터</th><th rowspan="2">등급</th>
<th colspan="5">금리(%)</th><th colspan="5">스프레드(bp)</th>
<th colspan="5">전월대비 스프레드 변동(bp)</th></tr><tr>"""
    html += "".join(f'<th class="sub">{t}</th>' for _ in range(3) for t in target_tenors)
    html += "</tr></thead><tbody>"
    for r in rows:
        html += f'<tr><td class="cat">{r["섹터"]}</td><td class="cat">{r["등급"]}</td>'
        for tn in target_tenors:
            v = r.get(f'금리_{tn}')
            html += f"<td>{v:.2f}</td>" if v is not None else "<td>-</td>"
        for tn in target_tenors:
            v = r.get(f'sp_{tn}')
            html += f"<td>{v:.1f}</td>" if v is not None else "<td>-</td>"
        for tn in target_tenors:
            v = r.get(f'mom_{tn}')
            if v is None:        html += "<td>-</td>"
            elif v < 0: html += f'<td class="neg">({abs(v):.1f})</td>'
            else:        html += f'<td class="pos">{v:.1f}</td>'
        html += "</tr>"
    html += "</tbody></table>"
    st.markdown(html, unsafe_allow_html=True)


# ── 탭2: 스프레드 차트 ────────────────────────────────────────────
def _render_spread_chart(df: pd.DataFrame):
    st.markdown("#### 크레딧 스프레드")
    all_cats = sorted(df['category'].unique().tolist())

    c1, c2, c3 = st.columns([2, 2, 1])
    with c1:
        cat_a = st.selectbox("계열 A", all_cats,
            index=next((i for i, c in enumerate(all_cats) if '카드채 AA' in c), 0),
            key='sp_cat_a')
    with c2:
        cat_b = st.selectbox("계열 B (기준)", all_cats,
            index=next((i for i, c in enumerate(all_cats)
                        if '국고채' in c or '공사/공단채 AAA' in c), 0),
            key='sp_cat_b')
    with c3:
        sel_tenor = st.selectbox("만기", TENOR_LABELS,
                                 index=TENOR_LABELS.index('2Y'), key='sp_tenor')

    o1, o2, o3 = st.columns(3)
    show_fill  = o1.toggle("스프레드 영역", value=True, key='sp_fill')
    show_cat_b = o2.toggle("기준선 표시",  value=True, key='sp_show_b')
    show_avg   = o3.toggle("평균선",      value=True, key='sp_avg')

    d_start, d_end = _date_range_picker(df, 'sp')
    dff = df[(df['date'] >= d_start) & (df['date'] <= d_end)]

    s_a = dff[(dff['category'] == cat_a) & (dff['tenor'] == sel_tenor)].sort_values('date')
    s_b = dff[(dff['category'] == cat_b) & (dff['tenor'] == sel_tenor)].sort_values('date')
    merged = pd.merge(
        s_a[['date', 'yield']].rename(columns={'yield': 'y_a'}),
        s_b[['date', 'yield']].rename(columns={'yield': 'y_b'}),
        on='date', how='inner')
    merged['spread_bp'] = (merged['y_a'] - merged['y_b']) * 100

    if len(merged) == 0:
        st.warning("공통 날짜 데이터 없음")
        return

    # ── z-order 제어: 금리선(secondary_y)이 fill(primary_y) 위에 오도록
    #    Plotly는 primary → secondary 순으로 렌더하므로
    #    fill = primary_y(먼저), 금리선 = secondary_y(나중/위) ────────
    fig = make_subplots(specs=[[{'secondary_y': True}]])

    # 1) 스프레드 fill — primary y (뒤에 렌더)
    if show_fill:
        fig.add_trace(go.Scatter(
            x=merged['date'], y=merged['spread_bp'],
            name='스프레드(bp)', fill='tozeroy',
            fillcolor='rgba(141,193,117,0.15)',
            line=dict(color='rgba(141,193,117,0.5)', width=1),
            hovertemplate='스프레드: %{y:.1f}bp<extra></extra>'),
            secondary_y=False)

    # 2) 평균선 — primary y
    if show_fill and show_avg:
        avg_sp = merged['spread_bp'].mean()
        fig.add_trace(go.Scatter(
            x=[merged['date'].min(), merged['date'].max()],
            y=[avg_sp, avg_sp],
            name=f'평균 {avg_sp:.1f}bp',
            line=dict(color='#BDBDBD', width=1.2, dash='dash'),
            hoverinfo='skip'),
            secondary_y=False)

    # 3) 기준선 — secondary y
    if show_cat_b:
        fig.add_trace(go.Scatter(
            x=s_b['date'], y=s_b['yield'],
            name=f'{cat_b} {sel_tenor}',
            line=dict(color='#BDBDBD', width=1.5, dash='dot'),
            hovertemplate='%{y:.3f}%<extra></extra>'),
            secondary_y=True)

    # 4) 주요 금리선 — secondary y (맨 위, 선명하게)
    fig.add_trace(go.Scatter(
        x=s_a['date'], y=s_a['yield'],
        name=f'{cat_a} {sel_tenor}',
        line=dict(color=DEEP_GREEN, width=2.2),
        hovertemplate='%{y:.3f}%<extra></extra>'),
        secondary_y=True)

    _base_layout(fig, f'{cat_a} {sel_tenor} 금리 및 스프레드', 450)
    fig.update_yaxes(title_text='스프레드(bp)', ticksuffix='bp', secondary_y=False,
                     showgrid=True, gridcolor='#E8F5E9',
                     showline=True, linecolor='#C8E6C9', rangemode='tozero')
    fig.update_yaxes(title_text='금리(%)', ticksuffix='%', secondary_y=True,
                     showgrid=False, showline=True, linecolor='#C8E6C9')
    st.plotly_chart(fig, use_container_width=True)

    last_sp = merged['spread_bp'].iloc[-1]
    avg_sp  = merged['spread_bp'].mean()
    pct_rk  = (merged['spread_bp'] < last_sp).sum() / len(merged) * 100
    prev    = merged[merged['date'] <= merged['date'].max() - pd.Timedelta(days=21)]
    mom_sp  = last_sp - prev['spread_bp'].iloc[-1] if len(prev) > 0 else np.nan

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("현재 스프레드", f"{last_sp:.1f}bp")
    m2.metric("기간 평균",    f"{avg_sp:.1f}bp")
    m3.metric("1M 변화", f"{mom_sp:+.1f}bp" if not np.isnan(mom_sp) else "-",
              delta_color="inverse")
    m4.metric("Percentile", f"{pct_rk:.0f}%")
    m5.metric("최대/최소",
              f"{merged['spread_bp'].max():.0f}/{merged['spread_bp'].min():.0f}bp")

    st.markdown("---")
    st.markdown("##### 스프레드 다중 비교")
    extra = st.multiselect("추가 계열", [c for c in all_cats if c != cat_a],
                           default=[], max_selections=4, key='sp_extra')
    if extra:
        fig2 = go.Figure()
        for i, cc in enumerate([cat_a] + extra):
            se = dff[(dff['category'] == cc) & (dff['tenor'] == sel_tenor)].sort_values('date')
            m2df = pd.merge(
                se[['date', 'yield']].rename(columns={'yield': 'y_e'}),
                s_b[['date', 'yield']].rename(columns={'yield': 'y_b'}),
                on='date', how='inner')
            m2df['sp'] = (m2df['y_e'] - m2df['y_b']) * 100
            fig2.add_trace(go.Scatter(
                x=m2df['date'], y=m2df['sp'],
                name=f"{cc} vs {cat_b.split()[-1]}",
                line=dict(color=COLORS_LINE[i % len(COLORS_LINE)], width=2,
                          dash='solid' if i == 0 else 'dot'),
                hovertemplate='%{y:.1f}bp<extra></extra>'))
        _base_layout(fig2, f'스프레드 비교 | 기준: {cat_b} {sel_tenor}', 380)
        fig2.update_yaxes(ticksuffix='bp')
        st.plotly_chart(fig2, use_container_width=True)


# ── 탭3: 커브 & 변동 ──────────────────────────────────────────────
def _single_curve_mom(df: pd.DataFrame, cat: str,
                      d1: pd.Timestamp, d2: pd.Timestamp):
    def get_cv(dt: pd.Timestamp):
        avail = df[df['category'] == cat]['date'].unique()
        if len(avail) == 0:
            return pd.DataFrame(), None
        nd = min(avail, key=lambda x: abs((x - dt).days))
        return df[(df['category'] == cat) & (df['date'] == nd)].copy(), nd

    cv1, actual_d1 = get_cv(d1)
    cv2, actual_d2 = get_cv(d2)

    if len(cv1) == 0 or len(cv2) == 0:
        st.warning(f"데이터 없음: {cat}")
        return

    common_t = [t for t in TENOR_LABELS
                if t in set(cv1['tenor']) and t in set(cv2['tenor'])]
    if not common_t:
        st.warning("공통 만기 없음")
        return

    m1_map = cv1.set_index('tenor')['yield']
    m2_map = cv2.set_index('tenor')['yield']
    ys_bar = [(m1_map[t] - m2_map[t]) * 100 for t in common_t]
    bar_colors = [COLOR_POS if v >= 0 else COLOR_NEG for v in ys_bar]

    # ── 제목: st.markdown으로 차트 위에 표시 (annotation HTML 버그 방지) ──
    d1_str = actual_d1.strftime('%Y-%m-%d')
    d2_str = actual_d2.strftime('%Y-%m-%d')
    st.markdown(
        f"<div style='font-size:14px;font-weight:700;color:{DEEP_GREEN};"
        f"margin-bottom:2px'>{cat}"
        f"<span style='font-size:12px;font-weight:400;color:#888;margin-left:10px'>"
        f"커브 및 변동&nbsp;&nbsp;{d1_str} vs {d2_str}</span></div>",
        unsafe_allow_html=True,
    )

    # ── 겹침 방지: max 대비 30% 미만 바는 텍스트 숨김 ──────────────
    max_abs = max(abs(v) for v in ys_bar) if ys_bar else 1
    bar_texts = [
        f"{v:+.1f}" if abs(v) >= max_abs * 0.30 else ""
        for v in ys_bar
    ]

    # ── Figure ──────────────────────────────────────────────────
    fig = make_subplots(specs=[[{'secondary_y': True}]])

    # 1) 바 — primary y (먼저, 뒤에)
    fig.add_trace(go.Bar(
        x=common_t, y=ys_bar,
        marker_color=bar_colors,
        marker_line_width=0,
        opacity=0.85,
        text=bar_texts,
        textposition='outside',
        textfont=dict(size=11, color='#333333',
                      family='Apple SD Gothic Neo, sans-serif'),
        cliponaxis=False,
        name='변동(bp)',
        hovertemplate='%{x}: %{y:+.2f}bp<extra></extra>',
    ), secondary_y=False)

    # 2) 비교일 라인 — secondary y
    cv2_s = (cv2[cv2['tenor'].isin(TENOR_LABELS)].copy()
             .assign(ord=lambda d: d['tenor'].map(TENOR_ORDER_MAP))
             .sort_values('ord'))
    fig.add_trace(go.Scatter(
        x=cv2_s['tenor'], y=cv2_s['yield'],
        name=d2_str,
        mode='lines+markers',
        line=dict(color='#9E9E9E', width=2, dash='dot'),
        marker=dict(size=7, symbol='circle-open', line=dict(width=2, color='#9E9E9E')),
        hovertemplate='%{x}: %{y:.3f}%<extra></extra>',
    ), secondary_y=True)

    # 3) 기준일 라인 — secondary y (맨 위)
    cv1_s = (cv1[cv1['tenor'].isin(TENOR_LABELS)].copy()
             .assign(ord=lambda d: d['tenor'].map(TENOR_ORDER_MAP))
             .sort_values('ord'))
    fig.add_trace(go.Scatter(
        x=cv1_s['tenor'], y=cv1_s['yield'],
        name=d1_str,
        mode='lines+markers',
        line=dict(color=DEEP_GREEN, width=2.5),
        marker=dict(size=8, symbol='circle',
                    color=DEEP_GREEN, line=dict(width=1.5, color='white')),
        hovertemplate='%{x}: %{y:.3f}%<extra></extra>',
    ), secondary_y=True)

    # ── y축 범위 계산 ─────────────────────────────────────────
    max_abs_bar = max(abs(v) for v in ys_bar) if ys_bar else 1
    bar_range   = [-max_abs_bar * 1.65, max_abs_bar * 1.65]

    all_y = list(cv1_s['yield']) + list(cv2_s['yield'])
    y_span  = max(all_y) - min(all_y) if all_y else 0.2
    line_range = ([min(all_y) - y_span * 0.3, max(all_y) + y_span * 0.5]
                  if all_y else None)

    # ── 레이아웃 ───────────────────────────────────────────────
    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        height=420,
        title=dict(text=''),          # None 금지 — JS에서 "undefined" 렌더됨
        font=dict(family='Apple SD Gothic Neo, Noto Sans KR, sans-serif', size=12),
        legend=dict(
            orientation='h',
            yanchor='bottom', y=1.02,
            xanchor='right',  x=1,
            font=dict(size=11),
            bgcolor='rgba(255,255,255,0.8)',
            bordercolor='#E0E0E0',
            borderwidth=1,
        ),
        margin=dict(l=70, r=85, t=36, b=44),
        plot_bgcolor='white',
        paper_bgcolor='white',
        hovermode='x unified',
        bargap=0.30,
        xaxis=dict(
            categoryorder='array',
            categoryarray=TENOR_LABELS,
            showgrid=False,
            showline=True, linecolor='#BDBDBD', linewidth=1.5,
            tickfont=dict(size=12, color='#444'),
        ),
    )

    fig.update_yaxes(
        title_text='변동(bp)',
        ticksuffix='bp',
        secondary_y=False,
        showgrid=True, gridcolor='#EEEEEE', gridwidth=1,
        zeroline=True, zerolinecolor='#AAAAAA', zerolinewidth=1.5,
        showline=False,
        range=bar_range,
        tickfont=dict(size=11, color='#555'),
        title_font=dict(size=11, color='#555'),
        title_standoff=12,
    )
    fig.update_yaxes(
        title_text='금리(%)',
        ticksuffix='%',
        secondary_y=True,
        showgrid=False,
        showline=False,
        tickformat='.2f',
        range=line_range,
        tickfont=dict(size=11, color='#555'),
        title_font=dict(size=11, color='#555'),
        title_standoff=12,
    )

    st.plotly_chart(fig, use_container_width=True)


def _render_curve_mom(df: pd.DataFrame):
    st.markdown("#### 커브 및 금리 변동 비교")
    all_cats  = sorted(df['category'].unique().tolist())
    avail     = sorted(df['date'].dropna().unique(), reverse=True)
    min_d     = pd.Timestamp(avail[-1]).date()
    max_d     = pd.Timestamp(avail[0]).date()

    # ── 날짜 직접 입력 (캘린더 피커) ─────────────────────────
    st.markdown("**비교 날짜 설정** — 영업일이 아닌 날은 가장 가까운 영업일로 자동 조정됩니다.")
    dc1, dc2, dc3 = st.columns([2, 2, 1])
    with dc1:
        d1_inp = st.date_input("📅 기준일 (최신)", value=max_d,
                               min_value=min_d, max_value=max_d, key='cv_d1')
    with dc2:
        d2_inp = st.date_input("📅 비교일 (이전)",
                               value=max(max_d - datetime.timedelta(days=30), min_d),
                               min_value=min_d, max_value=max_d, key='cv_d2')
    with dc3:
        n_panels = st.radio("패널", [1, 2], index=1, horizontal=True, key='cv_npanels')

    d1, d2 = pd.Timestamp(d1_inp), pd.Timestamp(d2_inp)
    if d1 < d2:
        d1, d2 = d2, d1
        st.info("기준일 ↔ 비교일 자동 교환")
    if d1 == d2:
        st.warning("두 날짜가 같습니다.")
        return

    st.markdown("---")
    defaults = [
        next((c for c in all_cats if '공사/공단채 AAA' in c), all_cats[0]),
        next((c for c in all_cats if '카드채 AA' in c),
             all_cats[min(1, len(all_cats) - 1)]),
    ]
    cols = st.columns(n_panels)
    for idx in range(n_panels):
        with cols[idx]:
            cv_cat = st.selectbox(
                f"계열 {idx + 1}", all_cats,
                index=all_cats.index(defaults[idx]) if defaults[idx] in all_cats else 0,
                key=f'cv_cat_{idx}')
            _single_curve_mom(df, cv_cat, d1, d2)


# ── 탭4: 금리 시계열 ──────────────────────────────────────────────
def _render_timeseries(df: pd.DataFrame):
    st.markdown("#### 금리 시계열")
    all_cats = sorted(df['category'].unique().tolist())

    fc1, fc2 = st.columns([3, 1])
    with fc1:
        ts_cats = st.multiselect("계열 선택 (최대 6개)", all_cats,
                                  default=all_cats[:3], max_selections=6, key='ts_cats')
    with fc2:
        ts_tenor = st.selectbox("만기", TENOR_LABELS,
                                index=TENOR_LABELS.index('3Y'), key='ts_tenor')

    d_start, d_end = _date_range_picker(df, 'ts')
    dff = df[(df['date'] >= d_start) & (df['date'] <= d_end)]

    if not ts_cats:
        st.info("계열을 선택하세요")
        return

    fig = go.Figure()
    for i, cc in enumerate(ts_cats):
        s = dff[(dff['category'] == cc) & (dff['tenor'] == ts_tenor)]
        if len(s) == 0:
            continue
        fig.add_trace(go.Scatter(x=s['date'], y=s['yield'],
            name=f'{cc} ({ts_tenor})',
            line=dict(color=COLORS_LINE[i % len(COLORS_LINE)], width=2),
            hovertemplate=f'{cc}: %{{y:.3f}}%<extra></extra>'))
    _base_layout(fig, f'금리 시계열 | {ts_tenor}', 430)
    fig.update_yaxes(ticksuffix='%')
    st.plotly_chart(fig, use_container_width=True)

    lv = [{'계열': cc,
            '금리': dff[(dff['category'] == cc) & (dff['tenor'] == ts_tenor)].iloc[-1]['yield']}
          for cc in ts_cats
          if len(dff[(dff['category'] == cc) & (dff['tenor'] == ts_tenor)]) > 0]
    if lv:
        lv_df = pd.DataFrame(lv).sort_values('금리')
        fig2 = go.Figure(go.Bar(
            x=lv_df['금리'], y=lv_df['계열'], orientation='h',
            marker_color=DEEP_GREEN,
            text=[f"{v:.3f}%" for v in lv_df['금리']], textposition='outside',
            hovertemplate='%{y}: %{x:.3f}%<extra></extra>'))
        _base_layout(fig2, f'최신 금리 비교 | {ts_tenor}', max(200, len(lv) * 42 + 80))
        fig2.update_xaxes(ticksuffix='%')
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown("---")
    st.markdown("##### 만기별 금리 추이")
    mc1, mc2 = st.columns([2, 2])
    with mc1:
        mt_cat    = st.selectbox("계열", all_cats, key='mt_cat')
    with mc2:
        mt_tenors = st.multiselect("만기", TENOR_LABELS,
                                   default=['1Y', '2Y', '3Y', '5Y'], key='mt_tenors')
    d_s2, d_e2 = _date_range_picker(df, 'mt')
    dff2 = df[(df['date'] >= d_s2) & (df['date'] <= d_e2)]

    fig3 = go.Figure()
    for i, tn in enumerate(mt_tenors or ['1Y', '3Y']):
        s = dff2[(dff2['category'] == mt_cat) & (dff2['tenor'] == tn)]
        if len(s) > 0:
            fig3.add_trace(go.Scatter(x=s['date'], y=s['yield'], name=tn,
                line=dict(color=GREEN_SHADES[i % len(GREEN_SHADES)], width=1.8),
                hovertemplate=f'{tn}: %{{y:.3f}}%<extra></extra>'))
    _base_layout(fig3, f'만기별 금리 | {mt_cat}', 400)
    fig3.update_yaxes(ticksuffix='%')
    st.plotly_chart(fig3, use_container_width=True)


# ── 메인 ──────────────────────────────────────────────────────────
def render(df: pd.DataFrame):
    st.header("Market View")
    c1, c2, c3 = st.columns(3)
    c1.metric("데이터 시작", df['date'].min().strftime('%Y-%m-%d'))
    c2.metric("데이터 종료", df['date'].max().strftime('%Y-%m-%d'))
    c3.metric("계열 수",    f"{df['category'].nunique()}개")
    st.markdown("---")

    tab1, tab2, tab3, tab4 = st.tabs(
        ["금리·스프레드 변동표", "크레딧 스프레드", "커브·변동 비교", "금리 시계열"])
    with tab1: _render_summary_table(df)
    with tab2: _render_spread_chart(df)
    with tab3: _render_curve_mom(df)
    with tab4: _render_timeseries(df)