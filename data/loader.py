"""
크레딧 데이터 로더
Wide-format Excel → Long-format DataFrame

파일 구조:
  row 0: 카테고리 헤더 (col 0, 11, 22, ...)
  row 1: 컬럼명 (일자, 3월이하(당일), ...)
  row 2~: 데이터 (날짜 내림차순)

  col 220: 한국 기준금리 (1col)
  col 221: 단위 레이블 (무시)
  col 222+: 국고채 (date, yield 쌍 × N)
"""
import pandas as pd
import re
import streamlit as st

TENORS = [
    '3월이하', '6월이하', '9월이하', '1년이하',
    '1.5년이하', '2년이하', '2.5년이하', '3년이하', '4년이하', '5년이하'
]
TENOR_LABELS = ['3M', '6M', '9M', '1Y', '1.5Y', '2Y', '2.5Y', '3Y', '4Y', '5Y']
TENOR_MAP = dict(zip(TENORS, TENOR_LABELS))

# 실제 컬럼명에 '(당일)' 붙어있으므로 양쪽 모두 지원
_TENOR_MAP_FULL = {**TENOR_MAP, **{f'{k}(당일)': v for k, v in TENOR_MAP.items()}}

KTB_TENOR_MAP = {
    '국고채권(1년)': '1Y',
    '국고채권(2년)': '2Y',
    '국고채권(3년)': '3Y',
    '국고채권(5년)': '5Y',
    '국고채권(10년)': None,
    '국고채권(20년)': None,
    '국고채권(30년)': None,
    '국고채권(50년)': None,
}
KTB_TENOR_VALID = {'1Y', '2Y', '3Y', '5Y'}


def parse_category(raw: str):
    raw = raw.strip()
    for prefix in ['시가평가 3사평균', '금투협 최종호가', '금투협최종호가', '시가평가3사평균']:
        raw = raw.replace(prefix, '').strip()
    raw = raw.replace('(공모/무보증)', '').strip()
    raw = raw.replace('AA0', 'AA')

    if '국고채' in raw:
        sector = '국고채'
        rating = re.sub(r'국고채권?', '', raw).strip()
        rating = re.sub(r'\(.*?\)', '', rating).strip()

    elif '통안채' in raw or '통화안정' in raw:
        sector = '통안채'
        rating = re.sub(r'통화안정증권|통안채', '', raw).strip()
        rating = re.sub(r'\(.*?\)', '', rating).strip()

    elif '공사/공단채' in raw:
        sector = '공사/공단채'
        rating = raw.replace('공사/공단채', '').strip()

    elif '공사채' in raw:
        sector = '공사/공단채'
        rating = raw.replace('공사채', '').strip()

    elif '금융채' in raw and '은행채' in raw:
        sector = '은행채'
        rating = re.sub(r'금융채\s*은행채', '', raw).strip()

    elif '금융채' in raw and '카드채' in raw:
        sector = '카드채'
        rating = re.sub(r'금융채\s*카드채', '', raw).strip()

    elif '은행채' in raw:
        sector = '은행채'
        rating = raw.replace('은행채', '').strip()

    elif '카드채' in raw:
        sector = '카드채'
        rating = raw.replace('카드채', '').strip()

    elif '기타금융채' in raw:
        sector = '기타금융채'
        rating = raw.replace('기타금융채', '').strip()

    elif '여전채' in raw:
        sector = '기타금융채'
        rating = raw.replace('여전채', '').strip()

    elif '회사채' in raw:
        sector = '회사채'
        rating = raw.replace('회사채', '').strip()

    else:
        sector = raw
        rating = ''

    rating = re.sub(r'\s+', '', rating)
    return sector, rating


def _parse_ktb_blocks(raw: pd.DataFrame) -> list[pd.DataFrame]:
    """
    국고채 블록 파싱.
    구조: row0=헤더(헤더는 짝수 col에만), row1='일자'/'대표수익률', row2+=데이터
    각 KTB 만기: (date_col, yield_col) = (222+2k, 223+2k)
    """
    frames = []
    ktb_start = 222
    for col in range(ktb_start, raw.shape[1] - 1, 2):
        header = str(raw.iloc[0, col]).strip()
        if '국고채권' not in header:
            continue

        m = re.search(r'국고채권\((.+?)\)', header)
        if not m:
            continue
        tenor_raw = f'국고채권({m.group(1)})'
        tenor = KTB_TENOR_MAP.get(tenor_raw)
        if tenor not in KTB_TENOR_VALID:
            continue

        date_col = col
        yield_col = col + 1
        if yield_col >= raw.shape[1]:
            continue

        # row 1에 '일자', '대표수익률' 확인
        r1_date  = str(raw.iloc[1, date_col]).strip()
        r1_yield = str(raw.iloc[1, yield_col]).strip()
        if '일자' not in r1_date:
            continue  # 예상 구조가 아니면 건너뜀

        block = raw.iloc[2:, [date_col, yield_col]].copy()
        block.columns = ['date', 'yield']
        block['date'] = pd.to_datetime(block['date'], errors='coerce')
        block = block.dropna(subset=['date'])
        block['yield'] = pd.to_numeric(block['yield'], errors='coerce')
        block = block.dropna(subset=['yield'])

        if len(block) == 0:
            continue

        block['sector'] = '국고채'
        block['rating'] = ''
        block['category'] = '국고채'
        block['tenor'] = tenor
        frames.append(block[['date', 'sector', 'rating', 'category', 'tenor', 'yield']])

    return frames


@st.cache_data(show_spinner=False)
def load_excel(file_bytes: bytes) -> pd.DataFrame:
    import io
    raw = pd.read_excel(io.BytesIO(file_bytes), sheet_name=0, header=None)

    frames = []

    # ── 1) 11컬럼 블록 파싱 (col0 ~ col219) ─────────────────
    # col 220 = 한국기준금리, 221 = 단위레이블 → 220까지만
    max_block_col = 220
    n_blocks = max_block_col // 11  # 20블록

    for b in range(n_blocks):
        base = b * 11
        cat_raw = str(raw.iloc[0, base]).strip()
        if cat_raw in ('nan', ''):
            continue

        sector, rating = parse_category(cat_raw)

        block = raw.iloc[2:, base:base + 11].copy()

        # 컬럼명 동적 감지 (row1에서 읽거나 기본값 사용)
        sub_cols = [str(raw.iloc[1, base + i]).strip() for i in range(11)]
        # 첫 번째는 날짜, 나머지 10개는 만기
        block.columns = ['date'] + TENORS  # 위치 기반 할당 (파일 컬럼명 무관)

        block = block.dropna(subset=['date'])
        block['date'] = pd.to_datetime(block['date'], errors='coerce')
        block = block.dropna(subset=['date'])

        melted = block.melt(id_vars='date', var_name='tenor_raw', value_name='yield')
        melted['tenor'] = melted['tenor_raw'].map(TENOR_MAP)
        melted['sector'] = sector
        melted['rating'] = rating
        melted['category'] = f"{sector} {rating}".strip()
        melted = melted.dropna(subset=['yield', 'tenor'])
        melted['yield'] = pd.to_numeric(melted['yield'], errors='coerce')
        melted = melted.dropna(subset=['yield'])

        if len(melted) == 0:
            continue

        frames.append(melted[['date', 'sector', 'rating', 'category', 'tenor', 'yield']])

    # ── 2) 국고채 블록 파싱 (col222+) ───────────────────────
    ktb_frames = _parse_ktb_blocks(raw)
    frames.extend(ktb_frames)

    if not frames:
        raise ValueError("파싱된 데이터가 없습니다. 파일 형식을 확인하세요.")

    df = pd.concat(frames, ignore_index=True)
    df = df.sort_values('date').reset_index(drop=True)

    # ── 검증 출력 (개발 확인용) ──────────────────────────────
    _validate(df)

    return df


def _validate(df: pd.DataFrame):
    """데이터 정합성 간단 체크 (로딩 시 1회)"""
    issues = []
    # 금리 범위: 0~20% 사이여야 정상
    out_of_range = df[(df['yield'] < 0) | (df['yield'] > 20)]
    if len(out_of_range) > 0:
        issues.append(f"이상 금리 {len(out_of_range)}건 (0~20% 범위 벗어남)")

    # 카테고리별 최신 날짜 확인
    max_date = df['date'].max()
    stale_cats = []
    for cat in df['category'].unique():
        cat_max = df[df['category'] == cat]['date'].max()
        lag = (max_date - cat_max).days
        if lag > 30:
            stale_cats.append(f"{cat}({lag}일 지연)")
    if stale_cats:
        issues.append(f"데이터 지연 계열: {', '.join(stale_cats[:3])}")

    if issues:
        import streamlit as st
        for msg in issues:
            st.warning(f"⚠️ 데이터 검증: {msg}")


def get_spread(df: pd.DataFrame, cat_a: str, cat_b: str, tenor: str) -> pd.DataFrame:
    a = df[(df['category'] == cat_a) & (df['tenor'] == tenor)].set_index('date')['yield']
    b = df[(df['category'] == cat_b) & (df['tenor'] == tenor)].set_index('date')['yield']
    spread = ((a - b) * 100).rename('spread')
    return spread.dropna().reset_index()


def get_curve(df: pd.DataFrame, category: str, date: pd.Timestamp) -> pd.DataFrame:
    sub = df[(df['category'] == category) & (df['date'] == date)].copy()
    sub['tenor_order'] = sub['tenor'].map({t: i for i, t in enumerate(TENOR_LABELS)})
    return sub.sort_values('tenor_order')


def get_mom_change(df: pd.DataFrame, category: str, tenor: str) -> pd.Series:
    sub = df[(df['category'] == category) & (df['tenor'] == tenor)].set_index('date')['yield']
    sub = sub.sort_index()
    mom = (sub - sub.shift(21)) * 100
    return mom.dropna()