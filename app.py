import io
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st
from bs4 import BeautifulSoup

st.set_page_config(
    page_title="台股分點融資斷頭雷達 | Streamlit",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# -----------------------------------------------------------------------------
# Built-in Demo Datasets (Fallback when external portals are unreachable)
# -----------------------------------------------------------------------------
DEMO_STOCKS: Dict[str, dict] = {
    "2330": {
        "name": "台積電",
        "market": "上市",
        "default_ratio": 60,
        "close": 1035.0,
        "branches": [
            {"分點名稱": "凱基-台北", "買進張數": 4820, "賣出張數": 1650, "買進均價": 1068.5},
            {"分點名稱": "元大-總公司", "買進張數": 3940, "賣出張數": 1420, "買進均價": 1052.0},
            {"分點名稱": "摩根大通", "買進張數": 6250, "賣出張數": 2100, "買進均價": 1044.5},
            {"分點名稱": "富邦-建國", "買進張數": 2180, "賣出張數": 640, "買進均價": 1082.0},
            {"分點名稱": "群益-大安", "買進張數": 1950, "賣出張數": 720, "買進均價": 1028.0},
            {"分點名稱": "永豐金-敦南", "買進張數": 1760, "賣出張數": 510, "買進均價": 1095.0},
            {"分點名稱": "國泰-綜合", "買進張數": 2450, "賣出張數": 1180, "買進均價": 1015.5},
            {"分點名稱": "美林", "買進張數": 5120, "賣出張數": 2890, "買進均價": 1060.0},
            {"分點名稱": "統一-敦南", "買進張數": 1480, "賣出張數": 490, "買進均價": 1074.5},
            {"分點名稱": "兆豐-大同", "買進張數": 1120, "賣出張數": 380, "買進均價": 998.0},
        ],
    },
    "2317": {
        "name": "鴻海",
        "market": "上市",
        "default_ratio": 60,
        "close": 208.5,
        "branches": [
            {"分點名稱": "凱基-市政", "買進張數": 6850, "賣出張數": 2120, "買進均價": 218.5},
            {"分點名稱": "元大-土城", "買進張數": 5420, "賣出張數": 1850, "買進均價": 214.0},
            {"分點名稱": "富邦-仁愛", "買進張數": 4210, "賣出張數": 1150, "買進均價": 222.0},
            {"分點名稱": "摩根士丹利", "買進張數": 8900, "賣出張數": 4100, "買進均價": 209.5},
            {"分點名稱": "永豐金-竹科", "買進張數": 3150, "賣出張數": 980, "買進均價": 216.5},
            {"分點名稱": "群益-東門", "買進張數": 2740, "賣出張數": 840, "買進均價": 204.0},
        ],
    },
    "8299": {
        "name": "群聯",
        "market": "上櫃",
        "default_ratio": 50,
        "close": 518.0,
        "branches": [
            {"分點名稱": "凱基-竹北", "買進張數": 1240, "賣出張數": 390, "買進均價": 548.0},
            {"分點名稱": "元大-新竹", "買進張數": 980, "賣出張數": 310, "買進均價": 535.0},
            {"分點名稱": "富邦-竹科", "買進張數": 820, "賣出張數": 240, "買進均價": 562.0},
            {"分點名稱": "永豐金-竹北", "買進張數": 690, "賣出張數": 210, "買進均價": 521.0},
        ],
    },
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}

PLOTLY_MOBILE_CONFIG = {
    "displayModeBar": False,
    "scrollZoom": False,
}


def _parse_float(val: object) -> Optional[float]:
    s = str(val or "").replace(",", "").strip()
    if not s or s in ("--", "---", "----", "N/A"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


@st.cache_data(ttl=1800)
def load_all_tw_stocks() -> List[dict]:
    """
    Load all TWSE (上市) and TPEx (上櫃) stock codes, company names, and latest closing prices.
    """
    catalog: List[dict] = []
    seen = set()

    # 1. TWSE OpenAPI (上市)
    try:
        resp = requests.get("https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL", headers=HEADERS, timeout=10)
        resp.raise_for_status()
        for row in resp.json():
            code = str(row.get("Code", "")).strip()
            name = str(row.get("Name", "")).strip()
            price = _parse_float(row.get("ClosingPrice"))
            if code and name and code not in seen:
                seen.add(code)
                catalog.append({"code": code, "name": name, "market": "上市", "close": price})
    except Exception:
        pass

    # 2. TPEx OpenAPI (上櫃)
    try:
        resp = requests.get(
            "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_daily_close_quotes",
            headers=HEADERS,
            timeout=12,
        )
        resp.raise_for_status()
        for row in resp.json():
            code = str(row.get("SecuritiesCompanyCode", "")).strip()
            name = str(row.get("CompanyName", "")).strip()
            price = _parse_float(row.get("Close"))
            if code and name and code not in seen:
                seen.add(code)
                catalog.append({"code": code, "name": name, "market": "上櫃", "close": price})
    except Exception:
        pass

    # Ensure demo stocks are always present as fallback
    for code, info in DEMO_STOCKS.items():
        if code not in seen:
            catalog.append(
                {"code": code, "name": info["name"], "market": info["market"], "close": info["close"]}
            )

    return catalog


def resolve_stock_query(query: str, catalog: List[dict]) -> List[dict]:
    """Match user query by exact stock code, exact name, or substring."""
    q = query.strip()
    if not q:
        return [c for c in catalog if c["code"] == "2330"] or catalog[:1]

    # Support "2330 台積電" format
    first_token = q.split()[0]

    exact_code = [c for c in catalog if c["code"].lower() == first_token.lower()]
    if exact_code:
        return exact_code

    exact_name = [c for c in catalog if c["name"].lower() == q.lower()]
    if exact_name:
        return exact_name

    partial = [
        c for c in catalog
        if q.lower() in c["code"].lower() or q.lower() in c["name"].lower()
    ]
    return partial[:20]


def _parse_fubon_dj_page(html_text: str, fallback_price: float) -> Tuple[List[dict], float]:
    """Parse a single Fubon DJ zco.djhtm page for net-buy branches and平均買超成本."""
    soup = BeautifulSoup(html_text, "lxml")
    page_text = soup.get_text(" ", strip=True)

    avg_cost = fallback_price
    m = re.search(r"平均買超成本\s*([\d,]+\.\d+|[\d,]+)", page_text)
    if m:
        parsed = _parse_float(m.group(1))
        if parsed and parsed > 0:
            avg_cost = parsed

    rows: List[dict] = []
    for tr in soup.find_all("tr"):
        tds = [td.get_text(strip=True) for td in tr.find_all("td")]
        if len(tds) >= 5:
            broker = tds[0]
            if not broker or broker in ("買超券商", "合計", "總計"):
                continue
            try:
                buy_lots = int(tds[1].replace(",", ""))
                sell_lots = int(tds[2].replace(",", ""))
                net_lots = int(tds[3].replace(",", ""))
                if net_lots > 0:
                    rows.append(
                        {
                            "分點名稱": broker,
                            "買進張數": buy_lots,
                            "賣出張數": sell_lots,
                            "買超張數": net_lots,
                        }
                    )
            except ValueError:
                continue

    return rows, avg_cost


@st.cache_data(ttl=600)
def fetch_fubon_dj_branches(stock_id: str, fallback_price: float, lookback_days: int = 5) -> Tuple[pd.DataFrame, str]:
    """
    Fetch recent N trading days of broker net-buy tables from Fubon DJ (公開免費網頁)
    and compute each broker branch's volume-weighted average buy cost across those days.
    """
    agg: Dict[str, dict] = {}
    days_found = 0
    cursor = datetime.now()
    checked = 0

    while days_found < lookback_days and checked < lookback_days * 3:
        checked += 1
        if cursor.weekday() < 5:
            d_str = f"{cursor.year}-{cursor.month}-{cursor.day}"
            url = f"https://fubon-ebrokerdj.fbs.com.tw/z/zc/zco/zco.djhtm?a={stock_id}&e={d_str}&f={d_str}"
            try:
                resp = requests.get(url, headers=HEADERS, timeout=10)
                if resp.status_code == 200:
                    resp.encoding = resp.apparent_encoding or "big5"
                    day_rows, day_cost = _parse_fubon_dj_page(resp.text, fallback_price)
                    if day_rows:
                        days_found += 1
                        for r in day_rows:
                            name = r["分點名稱"]
                            if name not in agg:
                                agg[name] = {"buy": 0, "sell": 0, "value": 0.0}
                            agg[name]["buy"] += r["買進張數"]
                            agg[name]["sell"] += r["賣出張數"]
                            agg[name]["value"] += r["買進張數"] * day_cost
            except Exception:
                pass
        cursor -= timedelta(days=1)

    if agg:
        result_rows = []
        for name, v in agg.items():
            if v["buy"] - v["sell"] > 0 and v["buy"] > 0:
                result_rows.append(
                    {
                        "分點名稱": name,
                        "買進張數": v["buy"],
                        "賣出張數": v["sell"],
                        "買進均價": round(v["value"] / v["buy"], 2),
                    }
                )
        if result_rows:
            df = pd.DataFrame(result_rows).sort_values(by="買進張數", ascending=False).head(30)
            return df.reset_index(drop=True), f"近 {days_found} 個交易日加權"

    # Fallback: default single summary page
    default_url = f"https://fubon-ebrokerdj.fbs.com.tw/z/zc/zco/zco.djhtm?a={stock_id}&e="
    resp = requests.get(default_url, headers=HEADERS, timeout=12)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding or "big5"
    day_rows, day_cost = _parse_fubon_dj_page(resp.text, fallback_price)
    if not day_rows:
        raise ValueError("無法從免費券商網頁解析到買超分點，可能為非交易日、無分點明細或連線受限。")

    df = pd.DataFrame(
        [
            {
                "分點名稱": r["分點名稱"],
                "買進張數": r["買進張數"],
                "賣出張數": r["賣出張數"],
                "買進均價": round(day_cost, 2),
            }
            for r in day_rows
        ]
    )
    return df, "單日彙總"


@st.cache_data(ttl=600)
def fetch_finmind_branches(stock_id: str, token: str, days: int = 10) -> Tuple[pd.DataFrame, float]:
    """Fetch exact broker branch buy/sell & weighted avg cost via FinMind Sponsor API."""
    end_dt = datetime.now()
    start_dt = end_dt - timedelta(days=max(days * 2, 14))
    fmt = "%Y-%m-%d"

    price_resp = requests.get(
        "https://api.finmindtrade.com/api/v4/data",
        params={
            "dataset": "TaiwanStockPrice",
            "data_id": stock_id,
            "start_date": start_dt.strftime(fmt),
            "end_date": end_dt.strftime(fmt),
            "token": token,
        },
        timeout=15,
    ).json()

    chip_resp = requests.get(
        "https://api.finmindtrade.com/api/v4/data",
        params={
            "dataset": "TaiwanStockTradingDailyReport",
            "data_id": stock_id,
            "start_date": start_dt.strftime(fmt),
            "end_date": end_dt.strftime(fmt),
            "token": token,
        },
        timeout=20,
    ).json()

    if chip_resp.get("status") != 200 or not chip_resp.get("data"):
        raise ValueError(chip_resp.get("msg", "FinMind 查無分點資料或 Token 權限不足（需 Sponsor 方案）"))

    latest_close = 100.0
    if price_resp.get("data"):
        latest_close = float(price_resp["data"][-1]["close"])

    df_chip = pd.DataFrame(chip_resp["data"])
    df_chip["buy"] = pd.to_numeric(df_chip["buy"], errors="coerce").fillna(0)
    df_chip["sell"] = pd.to_numeric(df_chip["sell"], errors="coerce").fillna(0)
    df_chip["price"] = pd.to_numeric(df_chip["price"], errors="coerce").fillna(latest_close)
    df_chip["buy_value"] = df_chip["buy"] * df_chip["price"]

    grouped = (
        df_chip.groupby("securities_trader", as_index=False)
        .agg({"buy": "sum", "sell": "sum", "buy_value": "sum"})
    )
    grouped["買進張數"] = (grouped["buy"] / 1000).round(0).astype(int)
    grouped["賣出張數"] = (grouped["sell"] / 1000).round(0).astype(int)
    grouped = grouped[(grouped["買進張數"] - grouped["賣出張數"] > 0) & (grouped["buy"] > 0)].copy()
    grouped["買進均價"] = (grouped["buy_value"] / grouped["buy"]).round(2)
    grouped = grouped.rename(columns={"securities_trader": "分點名稱"})

    result = grouped[["分點名稱", "買進張數", "賣出張數", "買進均價"]].sort_values(
        by="買進張數", ascending=False
    ).head(40)
    return result.reset_index(drop=True), latest_close


def calculate_margin_table(
    df: pd.DataFrame, sim_price: float, margin_ratio_pct: float, maint_threshold_pct: float
) -> pd.DataFrame:
    out = df.copy()
    ratio = margin_ratio_pct / 100.0
    threshold = maint_threshold_pct / 100.0

    out["淨買超(張)"] = (out["買進張數"] - out["賣出張數"]).clip(lower=0)
    out = out[out["淨買超(張)"] > 0].copy()

    out["推估融資金額(萬)"] = ((out["淨買超(張)"] * 1000 * out["買進均價"] * ratio) / 10000).round(0)
    out["斷頭價位(元)"] = (out["買進均價"] * ratio * threshold).round(2)

    denom = out["買進均價"] * ratio
    out["目前維持率(%)"] = ((sim_price / denom.replace(0, pd.NA)) * 100).round(1)
    out["距斷頭空間(%)"] = (
        ((sim_price - out["斷頭價位(元)"]) / sim_price * 100) if sim_price > 0 else 0.0
    ).round(1)

    def classify(m: float) -> str:
        if pd.isna(m):
            return "未知"
        if m < maint_threshold_pct:
            return "🔴 已破斷頭線"
        if m < maint_threshold_pct + 15:
            return "🟡 高風險警戒"
        return "🟢 安全"

    out["風險狀態"] = out["目前維持率(%)"].apply(classify)
    return out.sort_values(by="斷頭價位(元)", ascending=False).reset_index(drop=True)


# -----------------------------------------------------------------------------
# Main Page Header & Search Bar (Supports Stock Code or Company Name)
# -----------------------------------------------------------------------------
st.title("📡 台股分點融資斷頭雷達")

catalog = load_all_tw_stocks()

search_col1, search_col2 = st.columns([3, 2])
with search_col1:
    user_query = st.text_input(
        "🔍 搜尋個股（支援輸入股號或公司名稱，例如：2330、台積電、群聯）",
        value="2330",
        placeholder="輸入股號或公司名稱後按 Enter...",
    )

matches = resolve_stock_query(user_query, catalog)
if not matches:
    st.warning(f"找不到符合「{user_query}」的上市櫃個股，已改顯示 2330 台積電。")
    selected_stock = {"code": "2330", "name": "台積電", "market": "上市", "close": 1035.0}
elif len(matches) == 1:
    selected_stock = matches[0]
    with search_col2:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        st.success(f"已鎖定：**{selected_stock['code']} {selected_stock['name']}** ({selected_stock['market']})")
else:
    options_map = {f"{m['code']} {m['name']} ({m['market']})": m for m in matches}
    with search_col2:
        chosen_label = st.selectbox("找到多筆符合標的，請選擇：", list(options_map.keys()))
        selected_stock = options_map[chosen_label]

stock_id = selected_stock["code"]
detected_name = selected_stock["name"]
detected_market = selected_stock["market"]
detected_close = selected_stock["close"]

# -----------------------------------------------------------------------------
# Sidebar Advanced Settings
# -----------------------------------------------------------------------------
st.sidebar.title("⚙️ 進階參數設定")

data_source = st.sidebar.radio(
    "資料來源",
    ["免費即時抓取 (富邦網頁 + 證交所/櫃買)", "範例模擬數據 (Demo)", "上傳 CSV 檔案", "FinMind API (需 Sponsor)"],
    index=0,
)

lookback_days = st.sidebar.slider("分點成本統計天數（免費即時模式）", min_value=1, max_value=10, value=5, step=1)

market_options = ["自動偵測", "上市 (60%)", "上櫃 (50%)", "自訂"]
market_type = st.sidebar.selectbox("市場別 / 融資成數預設", market_options, index=0)

if market_type == "自動偵測":
    default_ratio = 50 if detected_market == "上櫃" else 60
elif market_type.startswith("上市"):
    default_ratio = 60
elif market_type.startswith("上櫃"):
    default_ratio = 50
else:
    default_ratio = 60

margin_ratio_pct = st.sidebar.slider("融資成數 (%)", min_value=10, max_value=80, value=default_ratio, step=5)
maint_threshold_pct = st.sidebar.number_input("斷頭/追繳維持率門檻 (%)", min_value=100, max_value=170, value=130, step=1)

# Load Data based on selected source
raw_df = pd.DataFrame()
base_price = 100.0
stock_label = f"{stock_id} {detected_name} ({detected_market})".strip()
source_note = ""

if data_source.startswith("免費即時"):
    fallback_close = st.sidebar.number_input(
        "若抓不到收盤價，手動輸入基準價 (元)",
        min_value=1.0,
        value=float(detected_close) if detected_close else 100.0,
        step=1.0,
    )
    base_price = float(detected_close) if detected_close else fallback_close
    try:
        raw_df, window_label = fetch_fubon_dj_branches(stock_id, base_price, lookback_days=lookback_days)
        price_src = "櫃買中心 OpenAPI" if detected_market == "上櫃" else "證交所 OpenAPI"
        source_note = (
            f"已從**{price_src}**取得收盤價 `{base_price:,.1f} 元`，並彙總**{window_label}**各日分點買進張數與每日平均買超成本"
            "（若仍需微調個別分點成本，可在下方表格直接編輯）。"
        )
    except Exception as e:
        st.warning(f"免費即時抓取失敗（{e}），已自動切換為範例數據。")
        preset = DEMO_STOCKS.get(stock_id, DEMO_STOCKS["2330"])
        stock_label = f"{stock_id if stock_id in DEMO_STOCKS else '2330'} {preset['name']} (備援範例)"
        base_price = preset["close"]
        raw_df = pd.DataFrame(preset["branches"])

elif data_source.startswith("範例"):
    preset = DEMO_STOCKS.get(stock_id, DEMO_STOCKS["2330"])
    if stock_id not in DEMO_STOCKS:
        stock_label = f"2330 {DEMO_STOCKS['2330']['name']} (範例)"
    base_price = preset["close"]
    raw_df = pd.DataFrame(preset["branches"])
    source_note = "目前顯示內建範例模擬數據，可供直接體驗壓力測試。"

elif data_source.startswith("上傳"):
    uploaded = st.sidebar.file_uploader("上傳 CSV（欄位：分點名稱,買進張數,賣出張數,買進均價）", type=["csv"])
    base_price = st.sidebar.number_input("個股目前收盤價 (元)", min_value=1.0, value=100.0, step=0.5)
    if uploaded is not None:
        raw_df = pd.read_csv(io.BytesIO(uploaded.read()))
        source_note = f"已載入自訂 CSV：{uploaded.name}"
    else:
        st.info("請在左側上傳 CSV 檔案，格式：`分點名稱,買進張數,賣出張數,買進均價`。")
        raw_df = pd.DataFrame(DEMO_STOCKS["2330"]["branches"])
        base_price = DEMO_STOCKS["2330"]["close"]

else:
    fm_token = st.sidebar.text_input("FinMind API Token", type="password")
    fm_days = st.sidebar.selectbox("統計天數", [5, 10, 20], index=1)
    if fm_token:
        try:
            raw_df, base_price = fetch_finmind_branches(stock_id, fm_token, fm_days)
            source_note = f"已從 FinMind 載入 {stock_id} 近 {fm_days} 日分點加權成本。"
        except Exception as e:
            st.error(f"FinMind 讀取失敗：{e}")
            raw_df = pd.DataFrame(DEMO_STOCKS["2330"]["branches"])
            base_price = DEMO_STOCKS["2330"]["close"]
    else:
        st.info("請在左側輸入 FinMind Sponsor Token，或切換至「免費即時抓取」。")
        raw_df = pd.DataFrame(DEMO_STOCKS["2330"]["branches"])
        base_price = DEMO_STOCKS["2330"]["close"]

# -----------------------------------------------------------------------------
# Dashboard Body
# -----------------------------------------------------------------------------
st.caption(f"查詢標的：**{stock_label}** ｜ 基準價：**{base_price:,.1f} 元** ｜ 融資成數：**{margin_ratio_pct}%** ｜ 追繳門檻：**{maint_threshold_pct}%**")
if source_note:
    st.info(source_note)

sim_price = st.slider(
    "📉 模擬現價（左右拖動進行下跌斷頭壓力測試）",
    min_value=max(1.0, round(base_price * 0.5, 1)),
    max_value=round(base_price * 1.3, 1),
    value=float(base_price),
    step=0.5 if base_price < 200 else 1.0,
)

with st.expander("✏️ 編輯或微調分點買進均價 / 張數（即時重算）", expanded=False):
    edited_df = st.data_editor(raw_df, num_rows="dynamic", use_container_width=True)

calc_df = calculate_margin_table(edited_df, sim_price, margin_ratio_pct, maint_threshold_pct)

# KPI Metrics
total_lots = int(calc_df["淨買超(張)"].sum()) if not calc_df.empty else 0
danger_df = calc_df[calc_df["目前維持率(%)"] < maint_threshold_pct]
danger_lots = int(danger_df["淨買超(張)"].sum()) if not danger_df.empty else 0
avg_call_price = (
    (calc_df["斷頭價位(元)"] * calc_df["淨買超(張)"]).sum() / total_lots if total_lots > 0 else 0.0
)
diff_pct = ((sim_price - base_price) / base_price * 100) if base_price > 0 else 0.0

c1, c2, c3, c4 = st.columns(4)
c1.metric("目前模擬股價", f"{sim_price:,.1f} 元", f"{diff_pct:+.1f}% vs 基準價")
c2.metric("加權平均斷頭價", f"{avg_call_price:,.1f} 元")
c3.metric("已破斷頭線分點", f"{len(danger_df)} / {len(calc_df)} 家")
c4.metric("潛在斷頭賣壓", f"{danger_lots:,} 張", f"佔追蹤買超 {(danger_lots / total_lots * 100):.1f}%" if total_lots else "0.0%")

# Charts (Mobile-friendly: dragmode=False & fixedrange=True prevent accidental zoom/pan on touchscreens)
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("各價位區間斷頭賣壓牆")
    if not calc_df.empty:
        min_call = float(calc_df["斷頭價位(元)"].min())
        max_call = float(calc_df["斷頭價位(元)"].max())
        if max_call - min_call < 0.5:
            wall_df = pd.DataFrame(
                {
                    "斷頭價區間": [f"{min_call:,.1f} 元"],
                    "潛在斷頭張數": [int(calc_df["淨買超(張)"].sum())],
                    "狀態": ["已破斷頭線" if sim_price < min_call else "安全/未觸及"],
                }
            )
        else:
            bins = pd.cut(calc_df["斷頭價位(元)"], bins=5)
            grouped_wall = calc_df.groupby(bins, observed=False)["淨買超(張)"].sum().reset_index()
            wall_df = pd.DataFrame(
                {
                    "斷頭價區間": [f"{iv.left:,.0f}~{iv.right:,.0f}" for iv in grouped_wall["斷頭價位(元)"]],
                    "潛在斷頭張數": grouped_wall["淨買超(張)"].astype(int),
                    "狀態": [
                        "已破斷頭線" if sim_price <= iv.right else "安全/未觸及"
                        for iv in grouped_wall["斷頭價位(元)"]
                    ],
                }
            )

        fig_wall = px.bar(
            wall_df,
            x="斷頭價區間",
            y="潛在斷頭張數",
            color="狀態",
            color_discrete_map={"已破斷頭線": "#f43f5e", "安全/未觸及": "#38bdf8"},
        )
        fig_wall.update_layout(
            height=340,
            margin=dict(l=10, r=10, t=30, b=10),
            dragmode=False,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            xaxis=dict(fixedrange=True, title="斷頭價位區間 (元)"),
            yaxis=dict(fixedrange=True, title="淨買超 (張)"),
        )
        st.plotly_chart(fig_wall, use_container_width=True, config=PLOTLY_MOBILE_CONFIG)

with col_right:
    st.subheader("前十大買超分點：買進均價 vs 斷頭價")
    if not calc_df.empty:
        top10 = calc_df.sort_values(by="淨買超(張)", ascending=False).head(10)
        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(name="買進均價", x=top10["分點名稱"], y=top10["買進均價"], marker_color="#64748b"))
        fig_bar.add_trace(go.Bar(name="斷頭價位", x=top10["分點名稱"], y=top10["斷頭價位(元)"], marker_color="#f59e0b"))
        fig_bar.add_hline(y=sim_price, line_dash="dash", line_color="#38bdf8", annotation_text="模擬現價")
        fig_bar.update_layout(
            barmode="group",
            height=340,
            margin=dict(l=10, r=10, t=30, b=10),
            dragmode=False,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            xaxis=dict(fixedrange=True),
            yaxis=dict(fixedrange=True),
        )
        st.plotly_chart(fig_bar, use_container_width=True, config=PLOTLY_MOBILE_CONFIG)

# Detailed Table
st.subheader("📋 分點融資斷頭風險明細")
st.dataframe(calc_df, use_container_width=True, hide_index=True)

with st.expander("📐 計算公式與資料限制說明"):
    st.markdown(
        """
        - **單筆融資維持率** $= \\frac{\\text{目前股價}}{\\text{買進均價} \\times \\text{融資成數}} \\times 100\\%$
        - **斷頭／追繳價位** $= \\text{買進均價} \\times \\text{融資成數} \\times \\text{維持率門檻（預設 } 130\\%\\text{）}$
        - **實務提醒**：證交所與櫃買中心並未公開各券商分點的實際融資使用比例，本工具係以多日分點買進張數搭配當日平均買超成本推算加權成本，實際斷頭與否仍以投資人整戶擔保維持率為準。
        """
    )