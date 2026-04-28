"""Page 2: Sector Matrix — 순서 변경 (외부 라이브러리 불필요)"""
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import datetime
from data.loader import TENOR_LABELS
from scoring.engine import compute_score
from assets.styles import (DEEP_GREEN, HEATMAP_GREEN, HEATMAP_DIVERG, PLOTLY_TEMPLATE)

ALL_RATINGS = ['AAA', 'AA+', 'AA', 'AA-', 'A+', 'A', 'A-']


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



def _init_state(df):
    sectors_in_data = sorted(df['sector'].unique().tolist())
    if 'mx_sector_order' not in st.session_state:
        st.session_state['mx_sector_order'] = sectors_in_data[:]
    else:
        existing = st.session_state['mx_sector_order']
        for s in sectors_in_data:
            if s not in existing:
                existing.append(s)
        st.session_state['mx_sector_order'] = [s for s in existing if s in sectors_in_data]

    if 'mx_rating_order' not in st.session_state:
        st.session_state['mx_rating_order'] = ALL_RATINGS[:]


def _reorder_ui(label: str, items: list, state_key: str, n_cols: int = 4):
    """
    ↑/↓ 버튼으로 순서 변경 + 체크박스로 표시/숨김 제어
    외부 라이브러리 불필요
    """
    current = st.session_state[state_key]

    with st.expander(f"{label} 순서 / 표시 설정", expanded=False):
        st.caption("↑ ↓ 버튼으로 순서 변경 | 체크박스로 표시 여부 결정")

        cols = st.columns([3, 1, 1, 2])
        cols[0].markdown("**항목**")
        cols[1].markdown("**위로**")
        cols[2].markdown("**아래로**")
        cols[3].markdown("**표시**")

        new_order  = current[:]
        to_display = list(new_order)   # 표시할 항목 (체크된 것만)

        for i, item in enumerate(new_order):
            c0, c1, c2, c3 = st.columns([3, 1, 1, 2])
            c0.write(item)

            # 위로
            if i > 0 and c1.button("↑", key=f'{state_key}_up_{i}', use_container_width=True):
                new_order[i - 1], new_order[i] = new_order[i], new_order[i - 1]
                st.session_state[state_key] = new_order
                st.rerun()

            # 아래로
            if i < len(new_order) - 1 and c2.button("↓", key=f'{state_key}_dn_{i}', use_container_width=True):
                new_order[i], new_order[i + 1] = new_order[i + 1], new_order[i]
                st.session_state[state_key] = new_order
                st.rerun()

            # 체크박스
            shown = c3.checkbox("", value=True, key=f'{state_key}_chk_{item}', label_visibility='collapsed')
            if not shown and item in to_display:
                to_display.remove(item)

        st.session_state[state_key] = new_order

    # 체크된 항목만 반환
    return [x for x in st.session_state[state_key]
            if st.session_state.get(f'{state_key}_chk_{x}', True)]


def render(df: pd.DataFrame):
    st.header("Sector Matrix")
    _init_state(df)

    # ── 분석 기간 선택 ────────────────────────────────────────────
    st.markdown("**분석 기간**")
    d_start, d_end = _date_range_picker(df, 'mx')
    dff = df[(df['date'] >= d_start) & (df['date'] <= d_end)]

    if len(dff) == 0:
        st.warning("선택한 기간에 데이터가 없습니다.")
        return

    st.caption(f"조회 기간: {d_start.strftime('%Y-%m-%d')} ~ {d_end.strftime('%Y-%m-%d')} "
               f"| 최신 기준일: {dff['date'].max().strftime('%Y-%m-%d')}")
    st.markdown("---")

    all_cats = sorted(dff['category'].unique().tolist())
    default_base = next((c for c in all_cats if '국고채' in c or '공사/공단채 AAA' in c), all_cats[0])

    mf1, mf2, mf3 = st.columns([1, 2, 3])
    with mf1:
        sel_tenor_mx = st.selectbox("기준 만기", TENOR_LABELS,
                                    index=TENOR_LABELS.index('3Y'), key='mx_tenor')
    with mf2:
        show_mode = st.radio("표시 값", ['금리(%)', '스프레드(bp)'], horizontal=True, key='mx_mode')
    with mf3:
        sp_base = st.selectbox("스프레드 기준 계열", all_cats,
                               index=all_cats.index(default_base) if default_base in all_cats else 0,
                               key='mx_base')

    # ── 순서 설정 UI (↑↓ 버튼 방식) ─────────────────────────────
    col_s, col_r = st.columns(2)
    with col_s:
        sector_order = _reorder_ui("섹터", sorted(dff['sector'].unique().tolist()),
                                   'mx_sector_order')
    with col_r:
        rating_order = _reorder_ui("등급", ALL_RATINGS, 'mx_rating_order')

    if not sector_order or not rating_order:
        st.warning("섹터 또는 등급을 하나 이상 선택하세요.")
        return

    # ── 매트릭스 빌드 (dff 기준) ──────────────────────────────────
    matrix_data    = {}
    base_yield_cache = None
    if show_mode == '스프레드(bp)':
        base_s = dff[(dff['category'] == sp_base) & (dff['tenor'] == sel_tenor_mx)]
        base_yield_cache = (base_s.sort_values('date').iloc[-1]['yield']
                            if len(base_s) > 0 else np.nan)

    for cat in all_cats:
        sub = dff[dff['category'] == cat]
        if len(sub) == 0: continue
        sec = sub['sector'].iloc[0]
        rat = sub['rating'].iloc[0]
        s   = dff[(dff['category'] == cat) & (dff['tenor'] == sel_tenor_mx)]
        if len(s) == 0: continue
        last_yield = s.sort_values('date').iloc[-1]['yield']
        if show_mode == '스프레드(bp)':
            val = (round((last_yield - base_yield_cache) * 100, 1)
                   if base_yield_cache is not None and not np.isnan(base_yield_cache)
                   and not np.isnan(last_yield) else np.nan)
        else:
            val = round(last_yield, 3) if not np.isnan(last_yield) else np.nan
        matrix_data[(sec, rat)] = val

    suffix = '%' if show_mode == '금리(%)' else 'bp'

    z_vals, hover_text, text_vals = [], [], []
    for sec in sector_order:
        row_z, row_h, row_t = [], [], []
        for rat in rating_order:
            v = matrix_data.get((sec, rat), np.nan)
            has_val = isinstance(v, (int, float)) and not np.isnan(v)
            row_z.append(v if has_val else np.nan)
            row_h.append(f"{sec} {rat}: {v}{suffix}" if has_val else f"{sec} {rat}: -")
            row_t.append(f"{v:.2f}" if has_val else "")
        z_vals.append(row_z)
        hover_text.append(row_h)
        text_vals.append(row_t)

    cs  = HEATMAP_GREEN if show_mode == '금리(%)' else HEATMAP_DIVERG
    fig = go.Figure(go.Heatmap(
        z=z_vals, x=rating_order, y=sector_order,
        text=text_vals, texttemplate="%{text}",
        hovertext=hover_text, hoverinfo='text',
        colorscale=cs, showscale=True,
        colorbar=dict(title=dict(text=suffix, side='right'), thickness=12, len=0.8)
    ))
    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        height=max(280, len(sector_order) * 44 + 80),
        title=dict(text=f"섹터 매트릭스  |  {sel_tenor_mx}  |  {show_mode}  |  기준: {dff['date'].max().strftime('%Y-%m-%d')}",
                   font=dict(color=DEEP_GREEN, size=13), x=0),
        font=dict(family="Apple SD Gothic Neo, Noto Sans KR, sans-serif", size=11),
        margin=dict(l=120, r=30, t=48, b=30),
        xaxis=dict(side='top'),
        plot_bgcolor='white', paper_bgcolor='white',
    )
    st.plotly_chart(fig, use_container_width=True)

    rows_tbl = []
    for sec in sector_order:
        row = {'섹터': sec}
        for rat in rating_order:
            v = matrix_data.get((sec, rat), np.nan)
            row[rat] = f"{v:.2f}{suffix}" if isinstance(v, (int, float)) and not np.isnan(v) else '-'
        rows_tbl.append(row)
    st.dataframe(pd.DataFrame(rows_tbl).set_index('섹터'), use_container_width=True)

    st.markdown("---")
    st.markdown("#### 투자의견")
    score_cats = st.multiselect("분석 계열 선택", all_cats,
        default=[c for c in all_cats if '회사채' in c][:4], key='score_cats')

    if score_cats:
        VIEW_CFG = {
            'OW': {'label': '비중확대', 'bg': '#EEF4EB', 'fg': '#2D3F38', 'border': '#8DC175'},
            'NW': {'label': '중립',     'bg': '#F2F4F0', 'fg': '#5A6B60', 'border': '#B0BDB4'},
            'UW': {'label': '비중축소', 'bg': '#F5EDEB', 'fg': '#8A3030', 'border': '#E0A898'},
        }
        cols = st.columns(min(len(score_cats), 3))
        for i, cc in enumerate(score_cats):
            s = dff[(dff['category'] == cc) & (dff['tenor'] == sel_tenor_mx)]
            if len(s) == 0: continue
            ys  = s.set_index('date')['yield'].sort_index()
            sc  = compute_score(ys)
            cfg = VIEW_CFG.get(sc['view'], VIEW_CFG['NW'])
            with cols[i % 3]:
                st.markdown(f"""
<div style="border:1px solid {cfg['border']};border-radius:5px;padding:14px 16px;margin:6px 0;background:{cfg['bg']}">
  <div style="font-size:12px;color:#6B7B6E;font-weight:500;margin-bottom:4px">{cc}</div>
  <div style="font-size:18px;font-weight:700;color:{cfg['fg']};margin-bottom:8px">{cfg['label']}</div>
  <div style="font-size:11px;color:#555;line-height:1.9">
    금리 레벨&nbsp;&nbsp;{sc['rate_pct']*100:.0f}%ile &nbsp;({sc['rate_score']:+d})<br>
    스프레드&nbsp;&nbsp;&nbsp;{sc['spread_pct']*100:.0f}%ile &nbsp;({sc['spread_score']:+d})<br>
    모멘텀 Z&nbsp;&nbsp;&nbsp;{sc['momentum_z']:.2f} &nbsp;({sc['momentum_score']:+d})<br>
    변동성&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;({sc['vol_score']:+d})<br>
    <span style="font-weight:600">합계&nbsp;&nbsp;{sc['total_score']:+d}</span>
  </div>
  <div style="font-size:10px;color:#888;margin-top:8px;padding-top:6px;border-top:1px solid {cfg['border']}">{sc['comment']}</div>
</div>""", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("#### 카테고리 x 만기 히트맵")
    hm_cats = st.multiselect("계열", all_cats, default=all_cats[:8], key='hm_cats')
    hm_mode = st.radio("값", ['금리(%)', '1M 변화(bp)'], horizontal=True, key='hm_mode')

    if hm_cats:
        hm_z, hm_text = [], []
        for cc in hm_cats:
            rz, rt = [], []
            for tn in TENOR_LABELS:
                s = dff[(dff['category'] == cc) & (dff['tenor'] == tn)]
                if len(s) == 0:
                    rz.append(np.nan); rt.append(''); continue
                if hm_mode == '금리(%)':
                    v = s.sort_values('date').iloc[-1]['yield']
                    rz.append(v); rt.append(f"{v:.3f}%")
                else:
                    ys2 = s.set_index('date')['yield'].sort_index()
                    v   = (ys2.iloc[-1] - ys2.iloc[-22]) * 100 if len(ys2) >= 22 else np.nan
                    rz.append(v); rt.append(f"{v:.1f}bp" if not np.isnan(v) else '')
            hm_z.append(rz); hm_text.append(rt)

        cs2 = HEATMAP_GREEN if hm_mode == '금리(%)' else HEATMAP_DIVERG
        fig_hm = go.Figure(go.Heatmap(
            z=hm_z, x=TENOR_LABELS, y=hm_cats,
            text=hm_text, texttemplate="%{text}",
            hovertemplate="%{y} %{x}: %{text}<extra></extra>",
            colorscale=cs2, showscale=True,
        ))
        fig_hm.update_layout(
            template=PLOTLY_TEMPLATE,
            height=max(280, len(hm_cats) * 34 + 90),
            title=dict(text=f"카테고리 x 만기  |  {hm_mode}",
                       font=dict(color=DEEP_GREEN, size=13), x=0),
            font=dict(family="Apple SD Gothic Neo, Noto Sans KR, sans-serif", size=10),
            margin=dict(l=190, r=30, t=48, b=30),
            xaxis=dict(side='top'),
            plot_bgcolor='white', paper_bgcolor='white',
        )
        st.plotly_chart(fig_hm, use_container_width=True)