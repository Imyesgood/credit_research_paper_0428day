"""
크레딧 스코어링 엔진
base_score = rate_level + spread_level + momentum + vol
→ OW / NW / UW
"""
import numpy as np
import pandas as pd


def _percentile_rank(series: pd.Series, window=252) -> float:
    recent = series.dropna()
    if len(recent) < 10:
        return 0.5
    tail = recent.iloc[-window:] if len(recent) >= window else recent
    last = tail.iloc[-1]
    return float((tail < last).sum() / len(tail))


def _zscore(series: pd.Series, window=21) -> float:
    recent = series.dropna().iloc[-window:]
    if len(recent) < 5:
        return 0.0
    diff = recent.diff().dropna()
    if diff.std() == 0:
        return 0.0
    return float(diff.mean() / diff.std())


def score_rate_level(pct: float) -> int:
    if pct > 0.75:
        return +1
    elif pct < 0.25:
        return -1
    return 0


def score_spread_level(pct: float) -> int:
    if pct > 0.75:
        return +1
    elif pct < 0.25:
        return -1
    return 0


def score_momentum(z: float) -> int:
    if z > 1.0:
        return -1
    elif z < -1.0:
        return +1
    return 0


def score_vol(std_val: float, threshold: float) -> int:
    if std_val > threshold:
        return -1
    return 0


def compute_vol_threshold(series: pd.Series, window=252, multiplier=1.5) -> float:
    std_20 = series.rolling(20).std()
    hist = std_20.dropna().iloc[-window:]
    return float(hist.quantile(0.75)) * multiplier if len(hist) > 0 else 0.01


def compute_score(yield_series: pd.Series, spread_series: pd.Series = None) -> dict:
    result = {}

    rate_pct = _percentile_rank(yield_series)
    rate_sc = score_rate_level(rate_pct)
    result['rate_pct'] = round(rate_pct, 3)
    result['rate_score'] = rate_sc

    if spread_series is not None and len(spread_series.dropna()) > 10:
        sp = spread_series
    else:
        sp = yield_series

    spread_pct = _percentile_rank(sp)
    spread_sc = score_spread_level(spread_pct)
    result['spread_pct'] = round(spread_pct, 3)
    result['spread_score'] = spread_sc

    mom_z = _zscore(sp)
    mom_sc = score_momentum(mom_z)
    result['momentum_z'] = round(mom_z, 3)
    result['momentum_score'] = mom_sc

    std_20 = float(yield_series.dropna().diff().iloc[-20:].std()) if len(yield_series.dropna()) >= 20 else 0
    threshold = compute_vol_threshold(yield_series)
    vol_sc = score_vol(std_20, threshold)
    result['vol_std'] = round(std_20, 5)
    result['vol_threshold'] = round(threshold, 5)
    result['vol_score'] = vol_sc

    total = rate_sc + spread_sc + mom_sc + vol_sc
    result['total_score'] = total

    if total >= 2:
        result['view'] = 'OW'
    elif total <= -2:
        result['view'] = 'UW'
    else:
        result['view'] = 'NW'

    result['comment'] = _build_comment(rate_sc, spread_sc, mom_sc, vol_sc, result['view'])
    return result


def _build_comment(rate, spread, mom, vol, view) -> str:
    parts = []
    if rate == 1:
        parts.append("금리 레벨은 carry 관점에서 유효")
    elif rate == -1:
        parts.append("금리 매력은 제한적")
    else:
        parts.append("금리 레벨 중립")

    if spread == 1:
        parts.append("스프레드 밸류에이션 양호")
    elif spread == -1:
        parts.append("스프레드 밸류에이션 부담")
    else:
        parts.append("스프레드 중립")

    if mom == -1:
        parts.append("스프레드 확대 흐름 지속")
    elif mom == 1:
        parts.append("스프레드 축소 흐름")
    else:
        parts.append("스프레드 안정")

    if vol == -1:
        parts.append("변동성 주의")

    return " / ".join(parts) + f" → 전략: {view}"


def view_color(view: str) -> str:
    return {'OW': '#2E7D32', 'NW': '#9E9E9E', 'UW': '#C62828'}.get(view, '#000')
