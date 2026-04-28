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

    # 텍스트 위치: 값이 크면 inside(흰색), 작으면 outside(검정)
    max_abs = max(abs(v) for v in mom_bp) if mom_bp else 1
    text_positions = []
    text_colors = []
    for v in mom_bp:
        if abs(v) > max_abs * 0.4:
            text_positions.append("inside")
            text_colors.append("#ffffff")
        else:
            text_positions.append("outside")
            text_colors.append("#444444")

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(
        x=common_t, y=mom_bp, name="전월대비 변동(bp, 좌축)",
        marker_color=bar_colors, opacity=0.80,
        text=[f"{v:+.1f}" for v in mom_bp],
        textposition=text_positions,
        textfont=dict(size=9),
        hovertemplate="%{x}: %{y:+.1f}bp<extra></extra>"
    ), secondary_y=False)

    # textfont color는 trace별로 못 쓰니 annotation으로 개별 색상 처리
    # → 대신 inside는 흰색, outside는 어두운색으로 두 개 트레이스로 분리
    fig.data = []  # 리셋 후 재작성

    inside_idx  = [i for i,p in enumerate(text_positions) if p == "inside"]
    outside_idx = [i for i,p in enumerate(text_positions) if p == "outside"]

    def make_bar(indices, tpos, tcolor):
        x_ = [common_t[i] for i in indices]
        y_ = [mom_bp[i] for i in indices]
        c_ = [bar_colors[i] for i in indices]
        t_ = [f"{mom_bp[i]:+.1f}" for i in indices]
        return go.Bar(
            x=x_, y=y_, marker_color=c_, opacity=0.80,
            text=t_, textposition=tpos,
            textfont=dict(size=9, color=tcolor),
            hovertemplate="%{x}: %{y:+.1f}bp<extra></extra>",
            showlegend=False,
        )

    if inside_idx:
        fig.add_trace(make_bar(inside_idx, "inside", "#ffffff"), secondary_y=False)
    if outside_idx:
        fig.add_trace(make_bar(outside_idx, "outside", "#333333"), secondary_y=False)

    # 더미 트레이스로 범례 표시
    fig.add_trace(go.Bar(x=[None], y=[None], name="전월대비 변동(bp, 좌축)",
        marker_color="#4A5E35", showlegend=True), secondary_y=False)

    if len(cv1) > 0:
        cv1f = cv1[cv1["tenor"].isin(TENOR_LABELS)]
        fig.add_trace(go.Scatter(x=cv1f["tenor"], y=cv1f["yield"], name=f"{d1_str} (우축)",
            mode="lines+markers", line=dict(color="#4A5E35", width=2),
            marker=dict(size=7), hovertemplate="%{x}: %{y:.3f}%<extra></extra>"), secondary_y=True)

    if len(cv2) > 0:
        cv2f = cv2[cv2["tenor"].isin(TENOR_LABELS)]
        fig.add_trace(go.Scatter(x=cv2f["tenor"], y=cv2f["yield"], name=f"{d2_str} (우축)",
            mode="lines+markers", line=dict(color="#9E9E9E", width=1.8, dash="dot"),
            marker=dict(size=6, symbol="circle-open"),
            hovertemplate="%{x}: %{y:.3f}%<extra></extra>"), secondary_y=True)

    _base_layout(fig, f"{cat} 커브 및 월간 금리 변동", 420)
    fig.update_layout(barmode="overlay")
    fig.update_yaxes(title_text="전월대비 변동(bp)", ticksuffix="bp", secondary_y=False,
                     showgrid=True, gridcolor="#E8F5E9",
                     zeroline=True, zerolinecolor="#BDBDBD", zerolinewidth=1.5,
                     showline=True, linecolor="#C8E6C9")
    fig.update_yaxes(title_text="금리(%)", ticksuffix="%", secondary_y=True,
                     showgrid=False, showline=True, linecolor="#C8E6C9")
    fig.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02,
                                  xanchor="right", x=1, font=dict(size=9)),
                      margin=dict(l=55, r=65, t=65, b=40))
    st.plotly_chart(fig, use_container_width=True)