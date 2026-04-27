"""Page 2: Sector Matrix — 드래그&드롭 순서 변경"""
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from data.loader import TENOR_LABELS
from scoring.engine import compute_score
from assets.styles import (DEEP_GREEN, LEAF_GREEN, GRAY, OLIVE,
                            HEATMAP_GREEN, HEATMAP_DIVERG, PLOTLY_TEMPLATE)

try:
    from streamlit_sortables import sort_items
    HAS_SORTABLES = True
except ImportError:
    HAS_SORTABLES = False

ALL_RATINGS = ['AAA', 'AA+', 'AA', 'AA-', 'A+', 'A', 'A-']


def _init_order(df):
    sectors_in_data = sorted(df['sector'].unique().tolist())
    if 'mx_sector_order' not in st.session_state:
        st.session_state['mx_sector_order'] = sectors_in_data
    else:
        existing = st.session_state['mx_sector_order']
        for s in sectors_in_data:
            if s not in existing:
                existing.append(s)
        st.session_state['mx_sector_order'] = [s for s in existing if s in sectors_in_data]

    if 'mx_rating_order' not in st.session_state:
        st.session_state['mx_rating_order'] = ALL_RATINGS[:]


def _arrow_reorder(state_key, prefix):
    items = list(st.session_state[state_key])
    for i, item in enumerate(items):
        c1, c2, c3 = st.columns([4, 1, 1])
        c1.text(item)
        if i > 0 and c2.button("▲", key=f'{prefix}_up_{i}'):
            items[i], items[i-1] = items[i-1], items[i]
            st.session_state[state_key] = items
            st.rerun()
        if i < len(items)-1 and c3.button("▼", key=f'{prefix}_dn_{i}'):
            items[i], items[i+1] = items[i+1], items[i]
            st.session_state[state_key] = items
            st.rerun()


def _order_panel():
    with st.expander("순서 변경", expanded=False):
        col_s, col_r = st.columns(2)
        with col_s:
            st.caption("섹터 순서")
            if HAS_SORTABLES:
                new_s = sort_items(st.session_state['mx_sector_order'], key='sort_sector')
                st.session_state['mx_sector_order'] = new_s
            else:
                _arrow_reorder('mx_sector_order', 'sec')
        with col_r:
            st.caption("신용등급 순서")
            if HAS_SORTABLES:
                new_r = sort_items(st.session_state['mx_rating_order'], key='sort_rating')
                st.session_state['mx_rating_order'] = new_r
            else:
                _arrow_reorder('mx_rating_order', 'rat')


def render(df: pd.DataFrame):
    st.header("Sector Matrix")
    _init_order(df)

    all_cats = sorted(df['category'].unique().tolist())
    default_base = next((c for c in all_cats if '국고채' in c or '공사/공단채 AAA' in c), all_cats[0])

    mf1, mf2, mf3 = st.columns([1, 2, 3])
    with mf1:
        sel_tenor_mx = st.selectbox("기준 만기", TENOR_LABELS, index=TENOR_LABELS.index('3Y'), key='mx_tenor')
    with mf2:
        show_mode = st.radio("표시 값", ['금리(%)', '스프레드(bp)'], horizontal=True, key='mx_mode')
    with mf3:
        sp_base = st.selectbox("스프레드 기준 계열", all_cats,
                               index=all_cats.index(default_base) if default_base in all_cats else 0,
                               key='mx_base')

    _order_panel()

    sector_order = st.session_state['mx_sector_order']
    rating_order = st.session_state['mx_rating_order']

    # 매트릭스 빌드
    matrix_data = {}
    base_yield_cache = None
    if show_mode == '스프레드(bp)':
        base_s = df[(df['category'] == sp_base) & (df['tenor'] == sel_tenor_mx)]
        base_yield_cache = base_s.sort_values('date').iloc[-1]['yield'] if len(base_s) > 0 else np.nan

    for cat in all_cats:
        sub = df[df['category'] == cat]
        if len(sub) == 0: continue
        sec = sub['sector'].iloc[0]
        rat = sub['rating'].iloc[0]
        s = df[(df['category'] == cat) & (df['tenor'] == sel_tenor_mx)]
        if len(s) == 0: continue
        last_yield = s.sort_values('date').iloc[-1]['yield']
        if show_mode == '스프레드(bp)':
            val = round((last_yield - base_yield_cache) * 100, 1) \
                if base_yield_cache is not None and not np.isnan(base_yield_cache) and not np.isnan(last_yield) \
                else np.nan
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

    cs = HEATMAP_GREEN if show_mode == '금리(%)' else HEATMAP_DIVERG

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
        title=dict(text=f"섹터 매트릭스  |  {sel_tenor_mx}  |  {show_mode}",
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
            s = df[(df['category'] == cc) & (df['tenor'] == sel_tenor_mx)]
            if len(s) == 0: continue
            ys = s.set_index('date')['yield'].sort_index()
            sc = compute_score(ys)
            cfg = VIEW_CFG.get(sc['view'], VIEW_CFG['NW'])
            with cols[i % 3]:
                st.markdown(f"""
<div style="border:1px solid {cfg['border']};border-radius:5px;padding:14px 16px;
            margin:6px 0;background:{cfg['bg']}">
  <div style="font-size:12px;color:#6B7B6E;font-weight:500;margin-bottom:4px">{cc}</div>
  <div style="font-size:18px;font-weight:700;color:{cfg['fg']};margin-bottom:8px">{cfg['label']}</div>
  <div style="font-size:11px;color:#555;line-height:1.9">
    금리 레벨&nbsp;&nbsp;{sc['rate_pct']*100:.0f}%ile &nbsp;({sc['rate_score']:+d})<br>
    스프레드&nbsp;&nbsp;&nbsp;{sc['spread_pct']*100:.0f}%ile &nbsp;({sc['spread_score']:+d})<br>
    모멘텀 Z&nbsp;&nbsp;&nbsp;{sc['momentum_z']:.2f} &nbsp;({sc['momentum_score']:+d})<br>
    변동성&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;({sc['vol_score']:+d})<br>
    <span style="font-weight:600">합계&nbsp;&nbsp;{sc['total_score']:+d}</span>
  </div>
  <div style="font-size:10px;color:#888;margin-top:8px;padding-top:6px;
              border-top:1px solid {cfg['border']}">{sc['comment']}</div>
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
                s = df[(df['category'] == cc) & (df['tenor'] == tn)]
                if len(s) == 0:
                    rz.append(np.nan); rt.append(''); continue
                if hm_mode == '금리(%)':
                    v = s.sort_values('date').iloc[-1]['yield']
                    rz.append(v); rt.append(f"{v:.3f}%")
                else:
                    ys2 = s.set_index('date')['yield'].sort_index()
                    v = (ys2.iloc[-1] - ys2.iloc[-22]) * 100 if len(ys2) >= 22 else np.nan
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
            title=dict(text=f"카테고리 x 만기  |  {hm_mode}", font=dict(color=DEEP_GREEN, size=13), x=0),
            font=dict(family="Apple SD Gothic Neo, Noto Sans KR, sans-serif", size=10),
            margin=dict(l=190, r=30, t=48, b=30),
            xaxis=dict(side='top'),
            plot_bgcolor='white', paper_bgcolor='white',
        )
        st.plotly_chart(fig_hm, use_container_width=True)
