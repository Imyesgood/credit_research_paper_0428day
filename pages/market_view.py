"""Page 1: Market View"""
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from data.loader import TENOR_LABELS
from assets.styles import DEEP_GREEN, OLIVE, LEAF_GREEN, SAGE_LIGHT, CREAM, CORAL, FILL_PRIMARY, FILL_NEUTRAL, HEATMAP_DIVERG, PLOTLY_TEMPLATE

COLORS_LINE = ['#2D3F38','#4A5E35','#9A7085','#005F73','#8A3030','#4E9B5A']
GREEN_SHADES = ['#2D3F38','#4A5E35','#4E9B5A','#8DC175','#8DD5C8','#DDE8C0','#8DB8A5','#9A7085','#8A9E96','#B0BDB4']
TENOR_ORDER_MAP = {t: i for i, t in enumerate(TENOR_LABELS)}


def _base_layout(fig, title="", height=420):
    fig.update_layout(
        template=PLOTLY_TEMPLATE, height=height,
        title=dict(text=title, font=dict(color=DEEP_GREEN, size=13), x=0),
        font=dict(family="Apple SD Gothic Neo, Noto Sans KR, sans-serif", size=11),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1, font=dict(size=10)),
        margin=dict(l=60, r=70, t=60, b=40),
        plot_bgcolor='white', paper_bgcolor='white', hovermode='x unified',
    )
    fig.update_xaxes(showgrid=True, gridcolor='#E8F5E9', gridwidth=1, showline=True, linecolor='#C8E6C9')
    return fig


def _date_filter(key, df, default_days=365):
    min_d = df['date'].min().date()
    max_d = df['date'].max().date()
    presets = {'1개월': 30, '3개월': 90, '6개월': 180, '1년': 365, '2년': 730, '전체': None}
    c1, c2 = st.columns([1, 2])
    with c1:
        preset = st.selectbox("기간", list(presets.keys()), index=list(presets.keys()).index('1년'), key=f'{key}_preset')
    with c2:
        days = presets[preset]
        dv = (min_d, max_d) if days is None else (max_d - pd.Timedelta(days=days), max_d)
        dr = st.date_input("직접 지정", value=dv, min_value=min_d, max_value=max_d, key=f'{key}_dr')
    return (pd.Timestamp(dr[0]), pd.Timestamp(dr[1])) if len(dr) == 2 else (pd.Timestamp(min_d), pd.Timestamp(max_d))


def _nearest(df, cat, dt):
    avail = df[df['category'] == cat]['date'].unique()
    return min(avail, key=lambda x: abs((pd.Timestamp(x) - pd.Timestamp(dt)).days)) if len(avail) > 0 else None


def _render_summary_table(df):
    st.markdown("#### 채권 금리 및 스프레드 변동 요약")
    all_cats = sorted(df["category"].unique().tolist())
    target_tenors = ["6M","1Y","2Y","3Y","5Y"]

    cf1, cf2 = st.columns([4, 2])
    with cf1:
        sel_cats = st.multiselect("표시 계열", all_cats,
            default=[c for c in all_cats if any(x in c for x in ["공사/공단채 AAA","은행채 AAA","카드채 AA","회사채 AA-","회사채 AA"])][:6],
            key="table_cats")
    with cf2:
        ref_cat = st.selectbox("스프레드 기준 계열", all_cats,
            index=next((i for i,c in enumerate(all_cats) if "국고채" in c or "공사/공단채 AAA" in c), 0),
            key="table_ref")

    if not sel_cats:
        st.info("계열을 선택하세요"); return

    ref_y, ref_y1m = {}, {}
    for tn in target_tenors:
        s = df[(df["category"]==ref_cat) & (df["tenor"]==tn)].sort_values("date")
        ref_y[tn] = s.iloc[-1]["yield"] if len(s) > 0 else np.nan
        ref_y1m[tn] = s.iloc[-22]["yield"] if len(s) >= 22 else np.nan

    rows = []
    for cat in sel_cats:
        sub = df[df["category"]==cat]
        row = {"섹터": sub["sector"].iloc[0] if len(sub)>0 else "", "등급": sub["rating"].iloc[0] if len(sub)>0 else ""}
        for tn in target_tenors:
            s = df[(df["category"]==cat) & (df["tenor"]==tn)].sort_values("date")
            cur = s.iloc[-1]["yield"] if len(s)>0 else np.nan
            cur1m = s.iloc[-22]["yield"] if len(s)>=22 else np.nan
            row[f"금리_{tn}"] = round(cur,2) if not np.isnan(cur) else None
            sp = (cur - ref_y[tn])*100 if not np.isnan(cur) and not np.isnan(ref_y[tn]) else None
            row[f"sp_{tn}"] = round(sp,1) if sp is not None else None
            if sp is not None and not np.isnan(cur1m) and not np.isnan(ref_y1m[tn]):
                row[f"mom_{tn}"] = round(sp - (cur1m - ref_y1m[tn])*100, 1)
            else:
                row[f"mom_{tn}"] = None
        rows.append(row)

    html = ("""<style>
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
+ "".join(f'<th class="sub">{t}</th>' for _ in range(3) for t in target_tenors)
+ "</tr></thead><tbody>")

    for r in rows:
        html += f'<tr><td class="cat">{r["섹터"]}</td><td class="cat">{r["등급"]}</td>'
        for tn in target_tenors:
            v=r.get(f"금리_{tn}"); html += f"<td>{v:.2f}</td>" if v is not None else "<td>-</td>"
        for tn in target_tenors:
            v=r.get(f"sp_{tn}"); html += f"<td>{v:.1f}</td>" if v is not None else "<td>-</td>"
        for tn in target_tenors:
            v=r.get(f"mom_{tn}")
            if v is None: html += "<td>-</td>"
            elif v < 0: html += f'<td class="neg">({abs(v):.1f})</td>'
            else: html += f'<td class="pos">{v:.1f}</td>'
        html += "</tr>"
    html += "</tbody></table>"
    st.markdown(html, unsafe_allow_html=True)


def _render_spread_chart(df):
    st.markdown("#### 크레딧 스프레드")
    all_cats = sorted(df["category"].unique().tolist())

    c1, c2, c3 = st.columns([2, 2, 1])
    with c1:
        cat_a = st.selectbox("계열 A (주계열)", all_cats,
            index=next((i for i,c in enumerate(all_cats) if "카드채 AA" in c), 0), key="sp_cat_a")
    with c2:
        cat_b = st.selectbox("계열 B (기준)", all_cats,
            index=next((i for i,c in enumerate(all_cats) if "국고채" in c or "공사/공단채 AAA" in c), 0), key="sp_cat_b")
    with c3:
        sel_tenor = st.selectbox("만기", TENOR_LABELS, index=TENOR_LABELS.index("2Y"), key="sp_tenor")

    o1, o2, o3 = st.columns(3)
    show_fill  = o1.toggle("스프레드 그림자 영역", value=True, key="sp_fill")
    show_cat_b = o2.toggle("계열 B 금리선 표시", value=True, key="sp_show_b")
    show_avg   = o3.toggle("스프레드 평균선", value=True, key="sp_avg")

    d_start, d_end = _date_filter("sp", df)
    dff = df[(df["date"] >= d_start) & (df["date"] <= d_end)]

    s_a = dff[(dff["category"]==cat_a) & (dff["tenor"]==sel_tenor)].sort_values("date")
    s_b = dff[(dff["category"]==cat_b) & (dff["tenor"]==sel_tenor)].sort_values("date")
    merged = pd.merge(s_a[["date","yield"]].rename(columns={"yield":"y_a"}),
                      s_b[["date","yield"]].rename(columns={"yield":"y_b"}), on="date", how="inner")
    merged["spread_bp"] = (merged["y_a"] - merged["y_b"]) * 100

    if len(merged) == 0:
        st.warning("공통 날짜 데이터 없음"); return

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    if show_fill:
        fig.add_trace(go.Scatter(x=merged["date"], y=merged["spread_bp"], name="스프레드 (bp, 우축)",
            fill="tozeroy", fillcolor="rgba(221,232,192,0.35)",
            line=dict(color="rgba(141,193,117,0.5)", width=1),
            hovertemplate="스프레드: %{y:.1f}bp<extra></extra>"), secondary_y=True)

    if show_fill and show_avg:
        avg_sp = merged["spread_bp"].mean()
        fig.add_trace(go.Scatter(x=[merged["date"].min(), merged["date"].max()], y=[avg_sp, avg_sp],
            name=f"평균 {avg_sp:.1f}bp",
            line=dict(color="rgba(100,100,100,0.6)", width=1.2, dash="dash"),
            hoverinfo="skip"), secondary_y=True)

    if show_cat_b:
        fig.add_trace(go.Scatter(x=s_b["date"], y=s_b["yield"], name=f"{cat_b} {sel_tenor} (좌축)",
            line=dict(color="#9E9E9E", width=1.5, dash="dot"),
            hovertemplate="%{y:.3f}%<extra></extra>"), secondary_y=False)

    fig.add_trace(go.Scatter(x=s_a["date"], y=s_a["yield"], name=f"{cat_a} {sel_tenor} (좌축)",
        line=dict(color="#2D3F38", width=2.2),
        hovertemplate="%{y:.3f}%<extra></extra>"), secondary_y=False)

    _base_layout(fig, f"{cat_a} {sel_tenor} 금리 및 스프레드", 450)
    fig.update_yaxes(title_text="금리 (%)", ticksuffix="%", secondary_y=False,
                     showgrid=True, gridcolor="#E8F5E9", showline=True, linecolor="#C8E6C9")
    fig.update_yaxes(title_text="스프레드 (bp)", ticksuffix="bp", secondary_y=True,
                     showgrid=False, showline=True, linecolor="#C8E6C9", rangemode="tozero")
    st.plotly_chart(fig, use_container_width=True)

    last_sp = merged["spread_bp"].iloc[-1]
    avg_sp  = merged["spread_bp"].mean()
    pct_rk  = (merged["spread_bp"] < last_sp).sum() / len(merged) * 100
    prev    = merged[merged["date"] <= merged["date"].max() - pd.Timedelta(days=21)]
    mom_sp  = last_sp - prev["spread_bp"].iloc[-1] if len(prev) > 0 else np.nan
    m1,m2,m3,m4,m5 = st.columns(5)
    m1.metric("현재 스프레드", f"{last_sp:.1f}bp")
    m2.metric("기간 평균", f"{avg_sp:.1f}bp")
    m3.metric("1M 변화", f"{mom_sp:+.1f}bp" if not np.isnan(mom_sp) else "-", delta_color="inverse")
    m4.metric("Percentile", f"{pct_rk:.0f}%")
    m5.metric("최대/최소", f"{merged['spread_bp'].max():.0f}/{merged['spread_bp'].min():.0f}bp")

    st.markdown("---")
    st.markdown("##### 스프레드 다중 비교 (기준 동일)")
    extra = st.multiselect("추가 계열 A 선택", [c for c in all_cats if c != cat_a], default=[], max_selections=4, key="sp_extra")
    if extra:
        fig2 = go.Figure()
        for i, cc in enumerate([cat_a] + extra):
            se = dff[(dff["category"]==cc) & (dff["tenor"]==sel_tenor)].sort_values("date")
            m2df = pd.merge(se[["date","yield"]].rename(columns={"yield":"y_e"}),
                            s_b[["date","yield"]].rename(columns={"yield":"y_b"}), on="date", how="inner")
            m2df["sp"] = (m2df["y_e"] - m2df["y_b"]) * 100
            fig2.add_trace(go.Scatter(x=m2df["date"], y=m2df["sp"],
                name=f"{cc} vs {cat_b.split()[-1]}",
                line=dict(color=COLORS_LINE[i % len(COLORS_LINE)], width=2, dash="solid" if i==0 else "dot"),
                hovertemplate="%{y:.1f}bp<extra></extra>"))
        _base_layout(fig2, f"스프레드 비교 | 기준: {cat_b} {sel_tenor}", 380)
        fig2.update_yaxes(ticksuffix="bp")
        st.plotly_chart(fig2, use_container_width=True)


def _single_curve_mom(df, cat, d1_str, d2_str):
    d1, d2 = pd.Timestamp(d1_str), pd.Timestamp(d2_str)

    def get_cv(dt):
        s = df[(df["category"]==cat) & (df["date"]==dt)]
        if len(s) == 0:
            nd = _nearest(df, cat, dt)
            if nd is None: return pd.DataFrame()
            s = df[(df["category"]==cat) & (df["date"]==nd)]
        s = s.copy(); s["t_ord"] = s["tenor"].map(TENOR_ORDER_MAP)
        return s.sort_values("t_ord")

    cv1, cv2 = get_cv(d1), get_cv(d2)
    common_t = [t for t in TENOR_LABELS if t in cv1["tenor"].values and t in cv2["tenor"].values]
    m1_map = cv1.set_index("tenor")["yield"]
    m2_map = cv2.set_index("tenor")["yield"]
    mom_bp = [(m1_map[t] - m2_map[t]) * 100 for t in common_t]
    bar_colors = ["#4A5E35" if v >= 0 else "#E87070" for v in mom_bp]

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(x=common_t, y=mom_bp, name="전월대비 변동(bp, 좌축)",
        marker_color=bar_colors, opacity=0.72,
        text=[f"{v:+.1f}" for v in mom_bp], textposition="outside",
        textfont=dict(size=9, color="#333"),
        hovertemplate="%{x}: %{y:+.1f}bp<extra></extra>"), secondary_y=False)

    if len(cv1) > 0:
        cv1f = cv1[cv1["tenor"].isin(TENOR_LABELS)]
        fig.add_trace(go.Scatter(x=cv1f["tenor"], y=cv1f["yield"], name=f"{d1_str} (우축)",
            mode="lines+markers", line=dict(color="#4A5E35", width=2),
            marker=dict(size=7, color="#4A5E35"),
            hovertemplate="%{x}: %{y:.3f}%<extra></extra>"), secondary_y=True)

    if len(cv2) > 0:
        cv2f = cv2[cv2["tenor"].isin(TENOR_LABELS)]
        fig.add_trace(go.Scatter(x=cv2f["tenor"], y=cv2f["yield"], name=f"{d2_str} (우축)",
            mode="lines+markers", line=dict(color="#9E9E9E", width=1.8, dash="dot"),
            marker=dict(size=6, color="#9E9E9E", symbol="circle-open"),
            hovertemplate="%{x}: %{y:.3f}%<extra></extra>"), secondary_y=True)

    _base_layout(fig, f"{cat} 커브 및 월간 금리 변동", 420)
    fig.update_yaxes(title_text="전월대비 변동(bp)", ticksuffix="bp", secondary_y=False,
                     showgrid=True, gridcolor="#E8F5E9",
                     zeroline=True, zerolinecolor="#BDBDBD", zerolinewidth=1.5, showline=True, linecolor="#C8E6C9")
    fig.update_yaxes(title_text="금리(%)", ticksuffix="%", secondary_y=True,
                     showgrid=False, showline=True, linecolor="#C8E6C9")
    fig.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=9)),
                      margin=dict(l=55, r=65, t=65, b=40))
    st.plotly_chart(fig, use_container_width=True)


def _render_curve_mom(df):
    st.markdown("#### 커브 및 월간 금리 변동")
    all_cats = sorted(df["category"].unique().tolist())
    avail_dates = sorted(df["date"].dropna().unique(), reverse=True)
    date_strs = [pd.Timestamp(d).strftime("%Y-%m-%d") for d in avail_dates]

    n_panels = st.radio("패널 수", [1, 2], index=1, horizontal=True, key="cv_npanels")
    cols = st.columns(n_panels)
    panel_defaults = [
        next((c for c in all_cats if "국고채" in c or "공사/공단채 AAA" in c), all_cats[0]),
        next((c for c in all_cats if "카드채 AA" in c), all_cats[0]),
    ]

    for idx, col in enumerate(cols):
        with col:
            st.markdown(f"**패널 {idx+1} 설정**")
            r1, r2 = st.columns(2)
            with r1:
                cv_cat = st.selectbox("계열", all_cats,
                    index=all_cats.index(panel_defaults[idx]) if panel_defaults[idx] in all_cats else 0,
                    key=f"cv_cat_{idx}")
            with r2:
                d1_str = st.selectbox("기준일", date_strs, index=0, key=f"cv_d1_{idx}")
            d2_str = st.selectbox("비교일", date_strs, index=min(21, len(date_strs)-1), key=f"cv_d2_{idx}")
            _single_curve_mom(df, cv_cat, d1_str, d2_str)


def _render_timeseries(df):
    st.markdown("#### 금리 시계열")
    all_cats = sorted(df["category"].unique().tolist())

    fc1, fc2 = st.columns([3, 1])
    with fc1:
        ts_cats = st.multiselect("계열 선택 (최대 6개)", all_cats, default=all_cats[:3], max_selections=6, key="ts_cats")
    with fc2:
        ts_tenor = st.selectbox("만기", TENOR_LABELS, index=TENOR_LABELS.index("3Y"), key="ts_tenor")

    d_start, d_end = _date_filter("ts", df)
    dff = df[(df["date"] >= d_start) & (df["date"] <= d_end)]

    if not ts_cats:
        st.info("계열을 선택하세요"); return

    fig = go.Figure()
    for i, cc in enumerate(ts_cats):
        s = dff[(dff["category"]==cc) & (dff["tenor"]==ts_tenor)]
        if len(s) == 0: continue
        fig.add_trace(go.Scatter(x=s["date"], y=s["yield"], name=f"{cc} ({ts_tenor})",
            line=dict(color=COLORS_LINE[i % len(COLORS_LINE)], width=2),
            hovertemplate=f"{cc}: %{{y:.3f}}%<extra></extra>"))
    _base_layout(fig, f"금리 시계열 | {ts_tenor}", 430)
    fig.update_yaxes(ticksuffix="%")
    st.plotly_chart(fig, use_container_width=True)

    lv = [{"계열": cc, "금리": dff[(dff["category"]==cc)&(dff["tenor"]==ts_tenor)].iloc[-1]["yield"]}
          for cc in ts_cats if len(dff[(dff["category"]==cc)&(dff["tenor"]==ts_tenor)]) > 0]
    if lv:
        lv_df = pd.DataFrame(lv).sort_values("금리")
        fig2 = go.Figure(go.Bar(x=lv_df["금리"], y=lv_df["계열"], orientation="h",
            marker_color=DEEP_GREEN,
            text=[f"{v:.3f}%" for v in lv_df["금리"]], textposition="outside",
            hovertemplate="%{y}: %{x:.3f}%<extra></extra>"))
        _base_layout(fig2, f"최신 금리 비교 | {ts_tenor}", max(200, len(lv)*42+80))
        fig2.update_xaxes(ticksuffix="%")
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown("---")
    st.markdown("##### 만기별 금리 추이")
    mc1, mc2 = st.columns([2, 2])
    with mc1:
        mt_cat = st.selectbox("계열", all_cats, key="mt_cat")
    with mc2:
        mt_tenors = st.multiselect("만기", TENOR_LABELS, default=["1Y","2Y","3Y","5Y"], key="mt_tenors")
    d_s2, d_e2 = _date_filter("mt", df)
    dff2 = df[(df["date"] >= d_s2) & (df["date"] <= d_e2)]
    fig3 = go.Figure()
    for i, tn in enumerate(mt_tenors or ["1Y","3Y"]):
        s = dff2[(dff2["category"]==mt_cat) & (dff2["tenor"]==tn)]
        if len(s) > 0:
            fig3.add_trace(go.Scatter(x=s["date"], y=s["yield"], name=tn,
                line=dict(color=GREEN_SHADES[i % len(GREEN_SHADES)], width=1.8),
                hovertemplate=f"{tn}: %{{y:.3f}}%<extra></extra>"))
    _base_layout(fig3, f"만기별 금리 | {mt_cat}", 400)
    fig3.update_yaxes(ticksuffix="%")
    st.plotly_chart(fig3, use_container_width=True)


def render(df: pd.DataFrame):
    st.header("Market View")
    tab1, tab2, tab3, tab4 = st.tabs(["금리·스프레드 변동표", "크레딧 스프레드", "커브·월간변동", "금리 시계열"])
    with tab1: _render_summary_table(df)
    with tab2: _render_spread_chart(df)
    with tab3: _render_curve_mom(df)
    with tab4: _render_timeseries(df)
