import io
import re
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple

import pandas as pd
import plotly.express as px
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


def _roc_to_date(roc_str: str) -> Optional[date]:
    parts = roc_str.strip().split("/")
    if len(parts) != 3:
        return None
    try:
        return date(int(parts[0]) + 1911, int(parts[1]), int(parts[2]))
    except ValueError:
        return None


@st.cache_data(ttl=1800)
def load_all_tw_stocks() -> List[dict]:
    """Load all TWSE (上市) and TPEx (上櫃) stock codes, company names, and latest closing prices."""
    catalog: List[dict] = []
    seen = set()

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

    for code, info in DEMO_STOCKS.items():
        if code not in seen:
            catalog.append(
                {"code": code, "name": info["name"], "market": info["market"], "close": info["close"]}
            )

    return catalog


def resolve_stock_query(query: str, catalog: List[dict]) -> List[dict]:
    q = query.strip()
    if not q:
        return [c for c in catalog if c["code"] == "2330"] or catalog[:1]

    first_token = q.split()[0]
    exact_code = [c for c in catalog if c["code"].lower() == first_token.lower()]
    if exact_code:
        return exact_code

    exact_name = [c for c in catalog if c["name"].lower() == q.lower()]
    if exact_name:
        return exact_name

    partial = [c for c in catalog if q.lower() in c["code"].lower() or q.lower() in c["name"].lower()]
    return partial[:20]


@st.cache_data(ttl=1800)
def fetch_official_daily_closes(stock_id: str, market: str) -> pd.DataFrame:
    """
    Fetch recent ~3 months of official daily closing prices from TWSE STOCK_DAY
    (or TPEx) so we can sanity-check any parsed broker cost against real prices.
    """
    rows = []
    now = datetime.now()
    for m_offset in (0, 1, 2):
        target = (now.replace(day=1) - timedelta(days=m_offset * 28)).replace(day=1)
        try:
            if market == "上市":
                url = (
                    f"https://www.twse.com.tw/rwd/zh/afterTrading/STOCK_DAY"
                    f"?date={target.strftime('%Y%m%d')}&stockNo={stock_id}&response=json"
                )
                resp = requests.get(url, headers=HEADERS, timeout=10).json()
                for r in resp.get("data", []):
                    dt = _roc_to_date(r[0])
                    close_p = _parse_float(r[6])
                    if dt and close_p:
                        rows.append({"日期": dt, "收盤價": close_p})
            else:
                url = (
                    f"https://www.tpex.org.tw/www/zh-tw/afterTrading/tradingStock"
                    f"?date={target.strftime('%Y/%m/%d')}&code={stock_id}&response=json"
                )
                resp = requests.get(url, headers=HEADERS, timeout=10).json()
                for table in resp.get("tables", []):
                    for r in table.get("data", []):
                        dt = _roc_to_date(r[0])
                        close_p = _parse_float(r[6])
                        if dt and close_p:
                            rows.append({"日期": dt, "收盤價": close_p})
        except Exception:
            continue

    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).drop_duplicates("日期").sort_values("日期").reset_index(drop=True)


@st.cache_data(ttl=900)
def fetch_margin_history(stock_id: str) -> pd.DataFrame:
    """Fetch recent ~40 trading days of margin balance & daily change from Fubon DJ zcn.djhtm."""
    url = f"https://fubon-ebrokerdj.fbs.com.tw/z/zc/zcn/zcn.djhtm?a={stock_id}&b=3"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code != 200:
            return pd.DataFrame()
        resp.encoding = resp.apparent_encoding or "big5"
        soup = BeautifulSoup(resp.text, "lxml")

        rows = []
        for tr in soup.find_all("tr"):
            tds = [td.get_text(strip=True) for td in tr.find_all("td")]
            if len(tds) >= 6:
                dt = _roc_to_date(tds[0])
                if dt is None:
                    continue
                bal = _parse_float(tds[4])
                chg = _parse_float(tds[5])
                if bal is not None and chg is not None:
                    rows.append({"日期": dt, "融資餘額": int(bal), "融資增減": int(chg)})

        if not rows:
            return pd.DataFrame()
        return pd.DataFrame(rows).sort_values("日期").reset_index(drop=True)
    except Exception:
        return pd.DataFrame()


def detect_turning_points(margin_df: pd.DataFrame) -> dict:
    today = date.today()
    info = {
        "min_bal_date": today - timedelta(days=30),
        "max_spike_date": today - timedelta(days=20),
        "latest_date": today,
    }
    if margin_df.empty:
        return info

    latest_dt = margin_df["日期"].iloc[-1]
    info["latest_date"] = latest_dt

    # 1) 融資波段最低點（若距離今日不足 7 日曆日，保底往前抓 14 日曆日）
    min_idx = margin_df["融資餘額"].idxmin()
    min_bal_dt = margin_df.loc[min_idx, "日期"]
    if (latest_dt - min_bal_dt).days < 7:
        min_bal_dt = latest_dt - timedelta(days=14)
    info["min_bal_date"] = min_bal_dt

    # 2) 波段融資爆量轉折日：排除最近 3 個交易日，找出前段單日融資大增日；
    # 若沒有或距離過近，保底抓近 20 日曆日以上
    earlier_df = margin_df.iloc[:-3] if len(margin_df) > 6 else margin_df
    pos_df = earlier_df[earlier_df["融資增減"] > 0]
    if not pos_df.empty:
        spike_idx = pos_df["融資增減"].idxmax()
        spike_dt = earlier_df.loc[spike_idx, "日期"]
    else:
        spike_dt = latest_dt - timedelta(days=28)

    if (latest_dt - spike_dt).days < 10:
        spike_dt = latest_dt - timedelta(days=20)
    info["max_spike_date"] = spike_dt

    return info


def _parse_fubon_dj_page(html_text: str, fallback_price: float) -> Tuple[List[dict], Optional[float]]:
    soup = BeautifulSoup(html_text, "lxml")
    page_text = soup.get_text(" ", strip=True)

    avg_cost: Optional[float] = None
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
                        }
                    )
            except ValueError:
                continue

    return rows, avg_cost


def _window_price_reference(
    price_df: pd.DataFrame, w_start: date, w_end: date, fallback_price: float
) -> Tuple[float, float, float]:
    """Return (avg_close, min_close, max_close) for [w_start, w_end] from official price history."""
    if not price_df.empty:
        sub = price_df[(price_df["日期"] >= w_start) & (price_df["日期"] <= w_end)]
        if not sub.empty:
            return float(sub["收盤價"].mean()), float(sub["收盤價"].min()), float(sub["收盤價"].max())
    return fallback_price, fallback_price * 0.75, fallback_price * 1.25


@st.cache_data(ttl=600)
def fetch_fubon_dj_range_weighted(
    stock_id: str,
    start_dt: date,
    end_dt: date,
    fallback_price: float,
    price_df: pd.DataFrame,
    chunks: int = 4,
) -> Tuple[pd.DataFrame, str]:
    """
    Split [start_dt, end_dt] into `chunks` sub-windows on Fubon DJ zco.djhtm.
    Each window's cost is validated against official TWSE/TPEx daily closes so
    parsing glitches or stale outliers cannot distort liquidation prices.
    """
    if start_dt > end_dt:
        start_dt = end_dt - timedelta(days=20)

    total_days = max(1, (end_dt - start_dt).days + 1)
    actual_chunks = min(chunks, total_days)
    step = total_days / actual_chunks

    agg: Dict[str, dict] = {}
    for i in range(actual_chunks):
        w_start = start_dt + timedelta(days=int(round(i * step)))
        w_end = end_dt if i == actual_chunks - 1 else start_dt + timedelta(days=int(round((i + 1) * step)) - 1)
        if w_start > w_end:
            w_end = w_start

        e_str = f"{w_start.year}-{w_start.month}-{w_start.day}"
        f_str = f"{w_end.year}-{w_end.month}-{w_end.day}"
        url = f"https://fubon-ebrokerdj.fbs.com.tw/z/zc/zco/zco.djhtm?a={stock_id}&e={e_str}&f={f_str}"

        avg_ref, min_ref, max_ref = _window_price_reference(price_df, w_start, w_end, fallback_price)

        try:
            resp = requests.get(url, headers=HEADERS, timeout=10)
            if resp.status_code == 200:
                resp.encoding = resp.apparent_encoding or "big5"
                win_rows, parsed_cost = _parse_fubon_dj_page(resp.text, avg_ref)
                # Sanity check parsed cost against official window price range
                if parsed_cost is not None and (min_ref * 0.85 <= parsed_cost <= max_ref * 1.15):
                    win_cost = parsed_cost
                else:
                    win_cost = avg_ref

                for r in win_rows:
                    name = r["分點名稱"]
                    if name not in agg:
                        agg[name] = {"buy": 0, "sell": 0, "value": 0.0}
                    agg[name]["buy"] += r["買進張數"]
                    agg[name]["sell"] += r["賣出張數"]
                    agg[name]["value"] += r["買進張數"] * win_cost
        except Exception:
            pass

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
            return df.reset_index(drop=True), f"{start_dt.strftime('%Y/%m/%d')} ~ {end_dt.strftime('%Y/%m/%d')}"

    # Fallback: default single summary page
    default_url = f"https://fubon-ebrokerdj.fbs.com.tw/z/zc/zco/zco.djhtm?a={stock_id}&e="
    resp = requests.get(default_url, headers=HEADERS, timeout=12)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding or "big5"
    day_rows, parsed_cost = _parse_fubon_dj_page(resp.text, fallback_price)
    if not day_rows:
        raise ValueError("無法從免費券商網頁解析到買超分點，可能為非交易日、無分點明細或連線受限。")

    day_cost = parsed_cost if (parsed_cost and fallback_price * 0.85 <= parsed_cost <= fallback_price * 1.15) else fallback_price
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
    return df, "單日預設彙總"


@st.cache_data(ttl=600)
def fetch_finmind_branches(stock_id: str, token: str, days: int = 20) -> Tuple[pd.DataFrame, float]:
    end_dt = datetime.now()
    start_dt = end_dt - timedelta(days=max(days * 2, 20))
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


def calculate_margin_metrics(
    df: pd.DataFrame, current_price: float, margin_ratio_pct: float, maint_threshold_pct: float
) -> Tuple[pd.DataFrame, dict]:
    if df.empty:
        return df, {}

    out = df.copy()
    ratio = margin_ratio_pct / 100.0
    threshold = maint_threshold_pct / 100.0

    out["淨買超(張)"] = (out["買進張數"] - out["賣出張數"]).clip(lower=0)
    out = out[out["淨買超(張)"] > 0].copy()
    if out.empty:
        return out, {}

    out["斷頭價位(元)"] = (out["買進均價"] * ratio * threshold).round(2)
    denom = out["買進均價"] * ratio
    out["目前維持率(%)"] = ((current_price / denom.replace(0, pd.NA)) * 100).round(1)
    out["距斷頭跌幅(%)"] = (((out["斷頭價位(元)"] - current_price) / current_price) * 100).round(1)

    def classify(m: float) -> str:
        if pd.isna(m):
            return "未知"
        if m < maint_threshold_pct:
            return "🔴 已破斷頭線"
        if m < maint_threshold_pct + 15:
            return "🟡 高風險警戒"
        return "🟢 安全"

    out["風險狀態"] = out["目前維持率(%)"].apply(classify)
    out = out.sort_values(by="斷頭價位(元)", ascending=False).reset_index(drop=True)

    first_row = out.iloc[0]
    first_price = float(first_row["斷頭價位(元)"])
    first_buy_price = float(first_row["買進均價"])
    first_drop_pct = ((first_price - current_price) / current_price) * 100.0

    min_call = float(out["斷頭價位(元)"].min())
    max_call = float(out["斷頭價位(元)"].max())
    if max_call - min_call < 0.5:
        peak_label = f"{min_call:,.1f} 元"
        peak_trigger_price = min_call
        peak_lots = int(out["淨買超(張)"].sum())
        wall_df = pd.DataFrame(
            {
                "斷頭價區間": [peak_label],
                "潛在斷頭張數": [peak_lots],
                "狀態": ["已觸發" if current_price <= min_call else "未觸發"],
            }
        )
    else:
        bins = pd.cut(out["斷頭價位(元)"], bins=5)
        grouped_wall = out.groupby(bins, observed=False)["淨買超(張)"].sum().reset_index()
        peak_idx = grouped_wall["淨買超(張)"].idxmax()
        peak_iv = grouped_wall.loc[peak_idx, "斷頭價位(元)"]
        peak_lots = int(grouped_wall.loc[peak_idx, "淨買超(張)"])
        peak_trigger_price = float(peak_iv.right)
        peak_label = f"{peak_iv.left:,.0f}~{peak_iv.right:,.0f} 元"

        wall_df = pd.DataFrame(
            {
                "斷頭價區間": [f"{iv.left:,.0f}~{iv.right:,.0f}" for iv in grouped_wall["斷頭價位(元)"]],
                "潛在斷頭張數": grouped_wall["淨買超(張)"].astype(int),
                "狀態": [
                    "已觸發" if current_price <= iv.right else "未觸發"
                    for iv in grouped_wall["斷頭價位(元)"]
                ],
            }
        )

    peak_drop_pct = ((peak_trigger_price - current_price) / current_price) * 100.0
    total_lots = int(out["淨買超(張)"].sum())
    weighted_call = float((out["斷頭價位(元)"] * out["淨買超(張)"]).sum() / total_lots) if total_lots else 0.0
    weighted_buy = float((out["買進均價"] * out["淨買超(張)"]).sum() / total_lots) if total_lots else 0.0

    summary = {
        "first_broker": str(first_row["分點名稱"]),
        "first_price": first_price,
        "first_buy_price": first_buy_price,
        "first_drop_pct": first_drop_pct,
        "peak_label": peak_label,
        "peak_trigger_price": peak_trigger_price,
        "peak_drop_pct": peak_drop_pct,
        "peak_lots": peak_lots,
        "weighted_call": weighted_call,
        "weighted_buy": weighted_buy,
        "wall_df": wall_df,
    }
    return out, summary


def fmt_drop_delta(drop_pct: float, suffix: str) -> str:
    """Format delta with leading '-' for un-triggered drops so Streamlit displays down-arrow."""
    if drop_pct >= 0:
        return f"+{drop_pct:.1f}% 已觸發 · {suffix}"
    return f"{drop_pct:.1f}% 再跌至此觸發 · {suffix}"


# -----------------------------------------------------------------------------
# Main Page Header & Search Bar
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

# -----------------------------------------------------------------------------
# Compute All 3 Methods Simultaneously
# -----------------------------------------------------------------------------
stock_label = f"{stock_id} {detected_name} ({detected_market})".strip()
fallback_close = float(detected_close) if detected_close else 100.0
if data_source.startswith("免費即時"):
    fallback_close = st.sidebar.number_input("若抓不到收盤價，手動輸入現價 (元)", min_value=1.0, value=fallback_close, step=1.0)

current_price = fallback_close
margin_hist_df = pd.DataFrame()
official_price_df = pd.DataFrame()
methods_raw: Dict[str, Tuple[pd.DataFrame, str]] = {}

if data_source.startswith("免費即時"):
    official_price_df = fetch_official_daily_closes(stock_id, detected_market)
    if not official_price_df.empty and (detected_close is None or detected_close <= 0):
        current_price = float(official_price_df["收盤價"].iloc[-1])

    margin_hist_df = fetch_margin_history(stock_id)
    tp = detect_turning_points(margin_hist_df)
    end_dt = tp["latest_date"]

    targets = [
        ("融資起增日", tp["min_bal_date"], end_dt),
        ("波段爆量起算", tp["max_spike_date"], end_dt),
        ("近60日波段", end_dt - timedelta(days=84), end_dt),
    ]

    live_ok = True
    for label, s_dt, e_dt in targets:
        try:
            df_m, rng_str = fetch_fubon_dj_range_weighted(
                stock_id, s_dt, e_dt, current_price, official_price_df, chunks=4
            )
            methods_raw[label] = (df_m, rng_str)
        except Exception:
            live_ok = False
            break

    if not live_ok:
        st.warning("免費即時抓取受限或無分點資料，已自動切換為內建範例數據供參考。")
        preset = DEMO_STOCKS.get(stock_id, DEMO_STOCKS["2330"])
        current_price = preset["close"]
        base_df = pd.DataFrame(preset["branches"])
        methods_raw = {
            "融資起增日": (base_df.copy(), "範例起增日"),
            "波段爆量起算": (base_df.assign(買進均價=(base_df["買進均價"] * 1.015).round(1)), "範例爆量日"),
            "近60日波段": (base_df.assign(買進均價=(base_df["買進均價"] * 0.97).round(1)), "範例60日"),
        }

elif data_source.startswith("範例"):
    preset = DEMO_STOCKS.get(stock_id, DEMO_STOCKS["2330"])
    current_price = preset["close"]
    base_df = pd.DataFrame(preset["branches"])
    methods_raw = {
        "融資起增日": (base_df.copy(), "範例起增日"),
        "波段爆量起算": (base_df.assign(買進均價=(base_df["買進均價"] * 1.015).round(1)), "範例爆量日"),
        "近60日波段": (base_df.assign(買進均價=(base_df["買進均價"] * 0.97).round(1)), "範例60日"),
    }

elif data_source.startswith("上傳"):
    uploaded = st.sidebar.file_uploader("上傳 CSV（欄位：分點名稱,買進張數,賣出張數,買進均價）", type=["csv"])
    current_price = st.sidebar.number_input("個股目前收盤價 (元)", min_value=1.0, value=100.0, step=0.5)
    if uploaded is not None:
        u_df = pd.read_csv(io.BytesIO(uploaded.read()))
        methods_raw = {"自訂匯入": (u_df, uploaded.name)}
    else:
        st.info("請在左側上傳 CSV 檔案，目前暫以範例顯示。")
        base_df = pd.DataFrame(DEMO_STOCKS["2330"]["branches"])
        current_price = DEMO_STOCKS["2330"]["close"]
        methods_raw = {"自訂匯入": (base_df, "範例")}

else:
    fm_token = st.sidebar.text_input("FinMind API Token", type="password")
    if fm_token:
        try:
            for label, d_cnt in [("近20日", 20), ("近40日", 40), ("近60日", 60)]:
                df_m, current_price = fetch_finmind_branches(stock_id, fm_token, d_cnt)
                methods_raw[label] = (df_m, f"FinMind 近 {d_cnt} 日")
        except Exception as e:
            st.error(f"FinMind 讀取失敗：{e}")
            base_df = pd.DataFrame(DEMO_STOCKS["2330"]["branches"])
            current_price = DEMO_STOCKS["2330"]["close"]
            methods_raw = {"備援範例": (base_df, "範例")}
    else:
        st.info("請在左側輸入 FinMind Sponsor Token，或切換至「免費即時抓取」。")
        base_df = pd.DataFrame(DEMO_STOCKS["2330"]["branches"])
        current_price = DEMO_STOCKS["2330"]["close"]
        methods_raw = {"備援範例": (base_df, "範例")}

# Run margin calculations for every method
methods_calc: Dict[str, Tuple[pd.DataFrame, dict, str]] = {}
for label, (raw_df, rng_str) in methods_raw.items():
    calc_df, summary = calculate_margin_metrics(raw_df, current_price, margin_ratio_pct, maint_threshold_pct)
    methods_calc[label] = (calc_df, summary, rng_str)

# -----------------------------------------------------------------------------
# Dashboard Body: Current Price & 3-Method Summary Cards
# -----------------------------------------------------------------------------
st.caption(
    f"查詢標的：**{stock_label}** ｜ 目前基準收盤價：**{current_price:,.1f} 元** ｜ "
    f"融資成數：**{margin_ratio_pct}%** ｜ 追繳門檻：**{maint_threshold_pct}%**"
)

st.subheader("📊 三大基準斷頭預警總覽（對照目前股價）")
cols = st.columns(len(methods_calc))
for col, (label, (calc_df, summary, rng_str)) in zip(cols, methods_calc.items()):
    with col:
        with st.container(border=True):
            st.markdown(f"#### {label}")
            st.caption(f"統計區間：{rng_str}")
            if summary:
                st.metric(
                    "① 開始有分點斷頭",
                    f"{summary['first_price']:,.1f} 元",
                    fmt_drop_delta(summary["first_drop_pct"], summary["first_broker"]),
                    delta_color="normal",
                )
                st.metric(
                    "② 最大波斷頭潮區間",
                    f"{summary['peak_label']}",
                    fmt_drop_delta(summary["peak_drop_pct"], f"約 {summary['peak_lots']:,} 張"),
                    delta_color="normal",
                )
                st.caption(
                    f"加權買進均價：**{summary['weighted_buy']:,.1f} 元** ｜ 加權斷頭價：**{summary['weighted_call']:,.1f} 元**"
                )
            else:
                st.info("無淨買超分點資料")

# -----------------------------------------------------------------------------
# Unified Broker Comparison Table Across the 3 Methods
# -----------------------------------------------------------------------------
if len(methods_calc) > 1:
    st.subheader("🏦 各分點三種基準斷頭價對照表")
    merged_df: Optional[pd.DataFrame] = None
    for label, (calc_df, _, _) in methods_calc.items():
        if calc_df.empty:
            continue
        sub = calc_df[["分點名稱", "淨買超(張)", "斷頭價位(元)", "距斷頭跌幅(%)"]].rename(
            columns={
                "淨買超(張)": f"{label}_買超(張)",
                "斷頭價位(元)": f"{label}_斷頭價",
                "距斷頭跌幅(%)": f"{label}_距斷頭%",
            }
        )
        if merged_df is None:
            merged_df = sub
        else:
            merged_df = pd.merge(merged_df, sub, on="分點名稱", how="outer")

    if merged_df is not None and not merged_df.empty:
        first_price_col = [c for c in merged_df.columns if c.endswith("_斷頭價")][0]
        merged_df = merged_df.sort_values(by=first_price_col, ascending=False).reset_index(drop=True)
        st.dataframe(merged_df, use_container_width=True, hide_index=True)

# -----------------------------------------------------------------------------
# Detailed Tabs: Pressure Wall & Full Table per Method
# -----------------------------------------------------------------------------
st.subheader("📉 各基準斷頭賣壓牆與分點明細")
tabs = st.tabs(list(methods_calc.keys()))
for tab, (label, (calc_df, summary, rng_str)) in zip(tabs, methods_calc.items()):
    with tab:
        if calc_df.empty or not summary:
            st.info("此區間查無淨買超分點資料。")
            continue

        wall_df = summary["wall_df"]
        fig_wall = px.bar(
            wall_df,
            x="斷頭價區間",
            y="潛在斷頭張數",
            color="狀態",
            color_discrete_map={"已觸發": "#f43f5e", "未觸發": "#38bdf8"},
            title=f"{label}（{rng_str}）— 各價位斷頭賣壓分佈",
        )
        fig_wall.update_layout(
            height=320,
            margin=dict(l=10, r=10, t=40, b=10),
            dragmode=False,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            xaxis=dict(fixedrange=True, title="斷頭價位區間 (元)"),
            yaxis=dict(fixedrange=True, title="潛在斷頭張數 (張)"),
        )
        st.plotly_chart(fig_wall, use_container_width=True, config=PLOTLY_MOBILE_CONFIG)

        st.dataframe(calc_df, use_container_width=True, hide_index=True)

if not margin_hist_df.empty:
    with st.expander("📈 查看近期融資餘額走勢（轉折偵測依據）", expanded=False):
        fig_margin = px.line(
            margin_hist_df,
            x="日期",
            y="融資餘額",
            markers=True,
            labels={"日期": "交易日", "融資餘額": "融資餘額 (張)"},
        )
        fig_margin.update_layout(
            height=260,
            margin=dict(l=10, r=10, t=25, b=10),
            dragmode=False,
            xaxis=dict(fixedrange=True),
            yaxis=dict(fixedrange=True),
        )
        st.plotly_chart(fig_margin, use_container_width=True, config=PLOTLY_MOBILE_CONFIG)

with st.expander("📐 計算公式與實務說明"):
    st.markdown(
        f"""
        - **單筆融資維持率** $= \\frac{{\\text{{目前股價}}}}{{\\text{{買進均價}} \\times \\text{{融資成數}}}} \\times 100\\%$
        - **斷頭／追繳價位** $= \\text{{買進均價}} \\times \\text{{融資成數}} \\times \\text{{維持率門檻（{maint_threshold_pct}%）}}$
        - **價位校驗**：系統會抓取[證交所](https://www.twse.com.tw/)/[櫃買中心](https://www.tpex.org.tw/)近 3 個月官方每日收盤價，自動校驗各區間抓取到的平均買超成本，避免網頁解析異常導致斷頭價偏離真實區間。
        """
    )