import io
import re
import pandas as pd

TENORS = ['3월이하', '6월이하', '9월이하', '1년이하', '1.5년이하', '2년이하', '2.5년이하', '3년이하', '4년이하', '5년이하']
TENOR_LABELS = ['3M', '6M', '9M', '1Y', '1.5Y', '2Y', '2.5Y', '3Y', '4Y', '5Y']
TENOR_MAP = dict(zip(TENORS, TENOR_LABELS))


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
        sector, rating = '공사/공단채', raw.replace('공사/공단채', '').strip()
    elif '공사채' in raw:
        sector, rating = '공사/공단채', raw.replace('공사채', '').strip()
    elif '은행채' in raw:
        sector, rating = '은행채', raw.replace('은행채', '').strip()
    elif '카드채' in raw:
        sector, rating = '카드채', raw.replace('카드채', '').strip()
    elif '기타금융채' in raw:
        sector, rating = '기타금융채', raw.replace('기타금융채', '').strip()
    elif '여전채' in raw:
        sector, rating = '기타금융채', raw.replace('여전채', '').strip()
    elif '회사채' in raw:
        sector, rating = '회사채', raw.replace('회사채', '').strip()
    else:
        sector, rating = raw, ''
    rating = re.sub(r'\s+', '', rating)
    return sector, rating


def load_excel(file_bytes: bytes) -> pd.DataFrame:
    raw = pd.read_excel(io.BytesIO(file_bytes), sheet_name=0, header=None)
    n_blocks = raw.shape[1] // 11
    frames = []
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
    if not frames:
        raise ValueError("파싱된 데이터가 없습니다. 파일 형식을 확인하세요.")
    return pd.concat(frames, ignore_index=True).sort_values('date')


def get_spread(df: pd.DataFrame, cat_a: str, cat_b: str, tenor: str) -> pd.DataFrame:
    a = df[(df['category'] == cat_a) & (df['tenor'] == tenor)].set_index('date')['yield']
    b = df[(df['category'] == cat_b) & (df['tenor'] == tenor)].set_index('date')['yield']
    return ((a - b) * 100).rename('spread').dropna().reset_index()


def get_curve(df: pd.DataFrame, category: str, date: pd.Timestamp) -> pd.DataFrame:
    sub = df[(df['category'] == category) & (df['date'] == date)].copy()
    sub['tenor_order'] = sub['tenor'].map({t: i for i, t in enumerate(TENOR_LABELS)})
    return sub.sort_values('tenor_order')


def get_mom_change(df: pd.DataFrame, category: str, tenor: str) -> pd.Series:
    sub = df[(df['category'] == category) & (df['tenor'] == tenor)].set_index('date')['yield'].sort_index()
    return (sub - sub.shift(21)) * 100

# market_view.py 호환용 상수 및 함수
POLICY_RATE_TENOR = '1Y'
POLICY_RATE_SECTOR = '국고채'


def get_policy_rate(df: pd.DataFrame) -> pd.Series:
    """국고채 1Y 금리 시계열 반환 (기준금리 프록시)"""
    sub = df[(df['sector'] == POLICY_RATE_SECTOR) & (df['tenor'] == POLICY_RATE_TENOR)]
    if len(sub) == 0:
        # fallback: 첫 번째 sector의 첫 번째 tenor
        sub = df.groupby(['date']).first().reset_index()
        return sub.set_index('date')['yield'].sort_index()
    return sub.set_index('date')['yield'].sort_index()


def get_bond_data(df: pd.DataFrame, category: str, tenor: str) -> pd.Series:
    """특정 계열·만기의 금리 시계열 반환"""
    sub = df[(df['category'] == category) & (df['tenor'] == tenor)]
    return sub.set_index('date')['yield'].sort_index()