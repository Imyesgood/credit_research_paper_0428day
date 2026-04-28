"""
크레딧 데이터 로더
Wide-format Excel → Long-format DataFrame
"""
import pandas as pd
import re
import streamlit as st

TENORS = ['3월이하', '6월이하', '9월이하', '1년이하', '1.5년이하', '2년이하', '2.5년이하', '3년이하', '4년이하', '5년이하']
TENOR_LABELS = ['3M', '6M', '9M', '1Y', '1.5Y', '2Y', '2.5Y', '3Y', '4Y', '5Y']
TENOR_MAP = dict(zip(TENORS, TENOR_LABELS))

# 국고채 만기 매핑 (금투협 포맷: 일자|대표수익률 쌍)
KTB_TENOR_MAP = {
    '국고채권(1년)':  '1Y',
    '국고채권(2년)':  '2Y',
    '국고채권(3년)':  '3Y',
    '국고채권(5년)':  '5Y',
    '국고채권(10년)': '3Y',   # 10년은 없으니 제외해도 되지만 일단 포함
    '국고채권(20년)': None,
    '국고채권(30년)': None,
    '국고채권(50년)': None,
}
# 실제로 TENOR_LABELS에 있는 것만
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
    """국고채 블록 파싱: col222~ 에서 (일자, 대표수익률) 쌍으로 구성"""
    frames = []
    # row0에서 '금투협 최종호가 국고채권(Ny)' 헤더 찾기
    for col in range(222, raw.shape[1], 2):
        header = str(raw.iloc[0, col]).strip()
        if '국고채권' not in header:
            continue
        # 만기 추출
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

        block = raw.iloc[2:, [date_col, yield_col]].copy()
        block.columns = ['date', 'yield']
        block['date'] = pd.to_datetime(block['date'], errors='coerce')
        block = block.dropna(subset=['date'])
        block['yield'] = pd.to_numeric(block['yield'], errors='coerce')
        block = block.dropna(subset=['yield'])

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

    # ── 1) 11컬럼 블록 파싱 (col0~219) ──
    max_block_col = 220
    n_blocks = max_block_col // 11

    for b in range(n_blocks):
        base = b * 11
        cat_raw = str(raw.iloc[0, base]).strip()
        if cat_raw in ('nan', ''):
            continue

        sector, rating = parse_category(cat_raw)

        block = raw.iloc[2:, base:base + 11].copy()
        block.columns = ['date'] + TENORS
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
        frames.append(melted[['date', 'sector', 'rating', 'category', 'tenor', 'yield']])

    # ── 2) 국고채 블록 파싱 (col222~) ──
    ktb_frames = _parse_ktb_blocks(raw)
    frames.extend(ktb_frames)

    if not frames:
        raise ValueError("파싱된 데이터가 없습니다. 파일 형식을 확인하세요.")

    df = pd.concat(frames, ignore_index=True)
    df = df.sort_values('date')
    return df


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