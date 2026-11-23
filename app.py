import html
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
    page_title="台股個股融資維持率與分點斷頭雷達",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# -----------------------------------------------------------------------------
# Custom Dark Financial Terminal Styling
# -----------------------------------------------------------------------------
st.markdown(
    """
    <style>
      .block-container {
        padding-top: 1.1rem;
        padding-bottom: 2.5rem;
        max-width: 1200px;
      }
      .hero-box {
        background: linear-gradient(135deg, #111827 0%, #0f172a 100%);
        border: 1px solid #1e293b;
        border-radius: 16px;
        padding: 18px 22px;
        margin-bottom: 14px;
      }
      .hero-top {
        display: flex;
        flex-wrap: wrap;
        justify-content: space-between;
        align-items: center;
        gap: 12px;
      }
      .stock-title {
        font-size: 1.45rem;
        font-weight: 700;
        color: #f8fafc;
        letter-spacing: -0.01em;
      }
      .stock-sub {
        font-size: 0.82rem;
        color: #94a3b8;
        margin-top: 3px;
      }
      .price-pill {
        text-align: right;
      }
      .price-val {
        font-size: 1.75rem;
        font-weight: 800;
        color: #38bdf8;
        font-variant-numeric: tabular-nums;
        line-height: 1.1;
      }
      .price-lbl {
        font-size: 0.75rem;
        color: #94a3b8;
      }
      .official-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
        gap: 12px;
        margin-bottom: 18px;
      }
      .official-card {
        background: #111827;
        border: 1px solid #1f2937;
        border-radius: 14px;
        padding: 14px 16px;
      }
      .official-card.border-danger { border-color: #f43f5e; background: rgba(244, 63, 94, 0.08); }
      .official-card.border-warn   { border-color: #f59e0b; background: rgba(245, 158, 11, 0.08); }
      .official-card.border-safe   { border-color: #10b981; background: rgba(16, 185, 129, 0.07); }
      .o-label {
        font-size: 0.78rem;
        color: #94a3b8;
        display: flex;
        justify-content: space-between;
        align-items: center;
      }
      .o-val {
        font-size: 1.55rem;
        font-weight: 800;
        margin-top: 6px;
        font-variant-numeric: tabular-nums;
      }
      .o-sub {
        font-size: 0.78rem;
        color: #cbd5e1;
        margin-top: 4px;
        font-variant-numeric: tabular-nums;
      }
      .risk-card {
        background: #111827;
        border: 1px solid #1f2937;
        border-radius: 16px;
        padding: 16px 18px;
        height: 100%;
        box-sizing: border-box;
      }
      .risk-card-header {
        display: flex;
        justify-content: space-between;
        align-items: baseline;
        margin-bottom: 10px;
        border-bottom: 1px solid #1f2937;
        padding-bottom: 8px;
      }
      .risk-card-title {
        font-size: 1.02rem;
        font-weight: 700;
        color: #f1f5f9;
      }
      .risk-card-date {
        font-size: 0.74rem;
        color: #94a3b8;
      }
      .danger-count-bar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        background: #0f172a;
        border: 1px solid #1e293b;
        border-radius: 10px;
        padding: 8px 12px;
        margin-bottom: 10px;
        font-size: 0.84rem;
      }
      .stage-box {
        border-radius: 12px;
        padding: 12px 14px;
        margin-bottom: 10px;
        border-left: 4px solid #334155;
      }
      .stage-danger { background: rgba(244, 63, 94, 0.12); border-left-color: #f43f5e; }
      .stage-warn   { background: rgba(245, 158, 11, 0.12); border-left-color: #f59e0b; }
      .stage-safe   { background: rgba(16, 185, 129, 0.10); border-left-color: #10b981; }
      .stage-label {
        font-size: 0.76rem;
        color: #cbd5e1;
        display: flex;
        justify-content: space-between;
        align-items: center;
      }
      .stage-main {
        font-size: 1.32rem;
        font-weight: 800;
        margin-top: 4px;
        font-variant-numeric: tabular-nums;
      }
      .broker-highlight {
        font-size: 1.02rem;
        font-weight: 700;
        color: #f8fafc;
        margin-top: 5px;
      }
      .stage-sub {
        font-size: 0.80rem;
        color: #94a3b8;
        margin-top: 4px;
        font-variant-numeric: tabular-nums;
      }
      .card-footer {
        font-size: 0.75rem;
        color: #94a3b8;
        padding-top: 4px;
        display: flex;
        justify-content: space-between;
        font-variant-numeric: tabular-nums;
      }
      .text-danger { color: #fb7185; }
      .text-warn   { color: #fbbf24; }
      .text-safe   { color: #34d399; }
      .text-sky    { color: #38bdf8; }
      .badge {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 999px;
        font-size: 0.7rem;
        font-weight: 600;
      }
      .badge-danger { background: rgba(244, 63, 94, 0.22); color: #fda4af; }
      .badge-warn   { background: rgba(245, 158, 11, 0.22); color: #fcd34d; }
      .badge-safe   { background: rgba(16, 185, 129, 0.20); color: #6ee7b7; }
    </style>
    """,
    unsafe_allow_html=True,
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
    s = str(val or "").replace(",", "").replace("%", "").strip()
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


@st.cache_data(ttl=1800)
def fetch_market_margin_maintenance() -> Optional[dict]:
    """
    Automatically fetch latest Taiwan market-wide margin maintenance ratio (%)
    and margin balance change (億元) from public KGI market overview page.
    """
    url = (
        "https://www.kgi.com.tw/zh-tw/product-market/stock-market-overview/"
        "tw-stock-market/tw-stock-market-detail"
        "?a=B658010E71E243C4A1D6B5F7BE914BDC&b=5D48401A7CE148CD8ABAC965F9B5AFBF"
    )
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code != 200:
            return None
        soup = BeautifulSoup(resp.text, "lxml")
        text = soup.get_text(" ", strip=True)

        # Try matching latest summary text: e.g. "2026/11/19 融資維持率 147.90% 融資餘額 4,843.68億元"
        m_ratio = re.search(r"融資維持率\s*([\d.]+)\s*%", text)
        m_bal = re.search(r"融資餘額\s*([\d,]+\.\d+|[\d,]+)\s*億", text)
        m_date = re.search(r"(\d{4}/\d{1,2}/\d{1,2})\s*融資維持率", text)
        m_chg = re.search(r"融資增減\s*([+\-]?[\d,]+\.\d+|[+\-]?[\d,]+)\s*億", text)

        if m_ratio:
            return {
                "date": m_date.group(1) if m_date else "最新交易日",
                "ratio_pct": float(m_ratio.group(1)),
                "balance_yi": m_bal.group(1) if m_bal else "--",
                "change_yi": m_chg.group(1) if m_chg else "--",
            }

        # Fallback: parse HTML table rows (日期 | 融資增減(億) | 融資維持率(%))
        for tr in soup.find_all("tr"):
            tds = [td.get_text(strip=True) for td in tr.find_all("td")]
            if len(tds) >= 3 and re.match(r"^\d{1,2}/\d{1,2}$", tds[0]):
                ratio_v = _parse_float(tds[2])
                if ratio_v and 100 <= ratio_v <= 250:
                    return {
                        "date": tds[0],
                        "ratio_pct": ratio_v,
                        "balance_yi": "--",
                        "change_yi": tds[1],
                    }
    except Exception:
        pass
    return None


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
    rows = []
    now = datetime.now()
    for m_offset in range(6):
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


def _parse_margin_table(html_text: str) -> List[dict]:
    soup = BeautifulSoup(html_text, "lxml")
    rows = []
    for tr in soup.find_all("tr"):
        tds = [td.get_text(strip=True) for td in tr.find_all("td")]
        if len(tds) >= 8:
            dt = _roc_to_date(tds[0])
            if dt is None:
                continue
            m_buy = _parse_float(tds[1])
            m_sell = _parse_float(tds[2])
            m_repay = _parse_float(tds[3])
            bal = _parse_float(tds[4])
            chg = _parse_float(tds[5])
            usage = _parse_float(tds[7])
            if bal is not None and chg is not None:
                rows.append(
                    {
                        "日期": dt,
                        "融資買進": int(m_buy or 0),
                        "融資賣出": int(m_sell or 0),
                        "現償": int(m_repay or 0),
                        "融資餘額": int(bal),
                        "融資增減": int(chg),
                        "使用率(%)": float(usage or 0.0),
                    }
                )
    return rows


@st.cache_data(ttl=900)
def fetch_margin_history(stock_id: str, trading_days: int = 120) -> pd.DataFrame:
    """
    Fetch up to ~120 trading days (~180 calendar days) of full margin purchase/sell/
    cash-repay/balance/usage from Fubon DJ zcn.djhtm to minimize initial cost bias.
    """
    end_dt = date.today()
    start_dt = end_dt - timedelta(days=int(trading_days * 1.55))
    c_str = f"{start_dt.year}-{start_dt.month}-{start_dt.day}"
    d_str = f"{end_dt.year}-{end_dt.month}-{end_dt.day}"

    candidate_urls = [
        f"https://fubon-ebrokerdj.fbs.com.tw/z/zc/zcn/zcn.djhtm?a={stock_id}&c={c_str}&d={d_str}",
        f"https://fubon-ebrokerdj.fbs.com.tw/z/zc/zcn/zcn.djhtm?a={stock_id}&e={c_str}&f={d_str}",
        f"https://fubon-ebrokerdj.fbs.com.tw/z/zc/zcn/zcn.djhtm?a={stock_id}&b=3",
    ]

    best_rows: List[dict] = []
    for url in candidate_urls:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=12)
            if resp.status_code != 200:
                continue
            resp.encoding = resp.apparent_encoding or "big5"
            parsed = _parse_margin_table(resp.text)
            if len(parsed) > len(best_rows):
                best_rows = parsed
            if len(best_rows) >= 60:
                break
        except Exception:
            continue

    if not best_rows:
        return pd.DataFrame()
    df = pd.DataFrame(best_rows).drop_duplicates("日期").sort_values("日期").reset_index(drop=True)
    return df.tail(trading_days).reset_index(drop=True)


def compute_stock_margin_maintenance(
    margin_df: pd.DataFrame,
    price_df: pd.DataFrame,
    current_price: float,
    margin_ratio_pct: float,
    maint_threshold_pct: float,
) -> Optional[dict]:
    """
    Compute stock-level margin maintenance ratio using actual daily Margin Purchase / Sell
    aligned with official daily closing prices (moving weighted-average cost model).
    Completely free of cash/foreign-investor distortion from broker branch data.
    """
    if margin_df.empty or current_price <= 0:
        return None

    df = margin_df.copy()
    if not price_df.empty:
        df = pd.merge(df, price_df, on="日期", how="left")
        df["收盤價"] = df["收盤價"].ffill().bfill().fillna(current_price)
    else:
        df["收盤價"] = current_price

    # Initialize rolling average cost from the oldest balance in the window
    avg_cost = float(df["收盤價"].iloc[0])
    bal = float(df["融資餘額"].iloc[0])
    ratio = margin_ratio_pct / 100.0
    threshold = maint_threshold_pct / 100.0

    maint_series = []
    for _, row in df.iterrows():
        p = float(row["收盤價"])
        m_buy = float(row["融資買進"])
        m_out = float(row["融資賣出"] + row["現償"])
        end_bal = float(row["融資餘額"])

        # Reduce by sells/repayments at current avg_cost, then blend new margin buys at day's close
        rem_bal = max(0.0, bal - m_out)
        new_total = rem_bal + m_buy
        if new_total > 0:
            avg_cost = (rem_bal * avg_cost + m_buy * p) / new_total
        bal = end_bal if end_bal > 0 else new_total

        day_maint = (p / (avg_cost * ratio)) * 100.0 if (avg_cost > 0 and ratio > 0) else 0.0
        maint_series.append(round(day_maint, 1))

    df["推估融資維持率(%)"] = maint_series
    latest_row = df.iloc[-1]
    latest_bal = int(latest_row["融資餘額"])
    latest_usage = float(latest_row["使用率(%)"])
    latest_maint = (current_price / (avg_cost * ratio)) * 100.0 if (avg_cost > 0 and ratio > 0) else 0.0
    call_price = avg_cost * ratio * threshold
    drop_to_call_pct = ((call_price - current_price) / current_price) * 100.0

    return {
        "latest_date": latest_row["日期"],
        "margin_balance": latest_bal,
        "margin_usage_pct": latest_usage,
        "est_avg_cost": round(avg_cost, 2),
        "est_maint_pct": round(latest_maint, 1),
        "est_call_price": round(call_price, 2),
        "drop_to_call_pct": round(drop_to_call_pct, 1),
        "history_df": df,
    }


def detect_turning_points(margin_df: pd.DataFrame) -> dict:
    today = date.today()
    info = {
        "min_bal_date": today - timedelta(days=30),
        "max_spike_date": today - timedelta(days=20),
        "latest_date": today,
    }
    if margin_df.empty:
        return info

    recent_df = margin_df.tail(40).reset_index(drop=True)
    latest_dt = recent_df["日期"].iloc[-1]
    info["latest_date"] = latest_dt

    min_idx = recent_df["融資餘額"].idxmin()
    min_bal_dt = recent_df.loc[min_idx, "日期"]
    if (latest_dt - min_bal_dt).days < 7:
        min_bal_dt = latest_dt - timedelta(days=14)
    info["min_bal_date"] = min_bal_dt

    earlier_df = recent_df.iloc[:-3] if len(recent_df) > 6 else recent_df
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


def _parse_fubon_dj_page(html_text: str) -> Tuple[List[dict], Optional[float]]:
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
                win_rows, parsed_cost = _parse_fubon_dj_page(resp.text)
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
            return df.reset_index(drop=True), f"{start_dt.strftime('%m/%d')} ~ {end_dt.strftime('%m/%d')}"

    default_url = f"https://fubon-ebrokerdj.fbs.com.tw/z/zc/zco/zco.djhtm?a={stock_id}&e="
    resp = requests.get(default_url, headers=HEADERS, timeout=12)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding or "big5"
    day_rows, parsed_cost = _parse_fubon_dj_page(resp.text)
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
    return df, "單日預設"


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
            return "🟠 高風險警戒"
        return "🟢 安全"

    out["風險狀態"] = out["目前維持率(%)"].apply(classify)
    out = out.sort_values(by="斷頭價位(元)", ascending=False).reset_index(drop=True)

    first_row = out.iloc[0]
    first_price = float(first_row["斷頭價位(元)"])
    first_drop_pct = ((first_price - current_price) / current_price) * 100.0

    min_call = float(out["斷頭價位(元)"].min())
    max_call = float(out["斷頭價位(元)"].max())
    if max_call - min_call < 0.5:
        peak_label = f"{min_call:,.1f} 元"
        peak_trigger_price = min_call
        peak_lots = int(out["淨買超(張)"].sum())
        wall_rows = [
            {
                "價位區間": peak_label,
                "中心價": min_call,
                "潛在斷頭張數": peak_lots,
                "風險等級": "已觸發斷頭" if current_price <= min_call else ("高危警戒" if first_drop_pct > -8 else "安全緩衝"),
            }
        ]
    else:
        bins = pd.cut(out["斷頭價位(元)"], bins=5)
        grouped_wall = out.groupby(bins, observed=False)["淨買超(張)"].sum().reset_index()
        peak_idx = grouped_wall["淨買超(張)"].idxmax()
        peak_iv = grouped_wall.loc[peak_idx, "斷頭價位(元)"]
        peak_lots = int(grouped_wall.loc[peak_idx, "淨買超(張)"])
        peak_trigger_price = float(peak_iv.right)
        peak_label = f"{peak_iv.left:,.0f}~{peak_iv.right:,.0f} 元"

        wall_rows = []
        for _, row in grouped_wall.iterrows():
            iv = row["斷頭價位(元)"]
            lots = int(row["淨買超(張)"])
            if lots <= 0:
                continue
            mid = (iv.left + iv.right) / 2.0
            drop_p = ((iv.right - current_price) / current_price) * 100.0
            if drop_p >= 0:
                lvl = "已觸發斷頭"
                tag = f"{iv.left:,.0f}~{iv.right:,.0f} 元 (已破線)"
            elif drop_p > -8:
                lvl = "高危警戒"
                tag = f"{iv.left:,.0f}~{iv.right:,.0f} 元 (再跌 {abs(drop_p):.1f}%)"
            else:
                lvl = "安全緩衝"
                tag = f"{iv.left:,.0f}~{iv.right:,.0f} 元 (再跌 {abs(drop_p):.1f}%)"
            wall_rows.append(
                {
                    "價位區間": tag,
                    "中心價": mid,
                    "潛在斷頭張數": lots,
                    "風險等級": lvl,
                }
            )

    wall_df = pd.DataFrame(wall_rows).sort_values(by="中心價", ascending=True) if wall_rows else pd.DataFrame()
    peak_drop_pct = ((peak_trigger_price - current_price) / current_price) * 100.0
    total_lots = int(out["淨買超(張)"].sum())
    danger_mask = out["目前維持率(%)"] < maint_threshold_pct
    danger_count = int(danger_mask.sum())
    danger_lots = int(out.loc[danger_mask, "淨買超(張)"].sum())
    total_brokers = int(len(out))
    weighted_call = float((out["斷頭價位(元)"] * out["淨買超(張)"]).sum() / total_lots) if total_lots else 0.0
    weighted_buy = float((out["買進均價"] * out["淨買超(張)"]).sum() / total_lots) if total_lots else 0.0

    summary = {
        "danger_count": danger_count,
        "danger_lots": danger_lots,
        "total_brokers": total_brokers,
        "first_broker": str(first_row["分點名稱"]),
        "first_price": first_price,
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


def _stage_theme(drop_pct: float) -> Tuple[str, str, str, str]:
    if drop_pct >= 0:
        return "stage-danger", "text-danger", "badge-danger", "🔴 已破斷頭線"
    if drop_pct > -8.0:
        return "stage-warn", "text-warn", "badge-warn", "🟠 高危警戒"
    return "stage-safe", "text-safe", "badge-safe", "🟢 緩衝充足"


def render_risk_card(label: str, rng_str: str, summary: dict) -> str:
    safe_label = html.escape(label)
    safe_rng = html.escape(rng_str)
    if not summary:
        return f"""
        <div class="risk-card">
          <div class="risk-card-header">
            <span class="risk-card-title">{safe_label}</span>
            <span class="risk-card-date">{safe_rng}</span>
          </div>
          <div style="color:#94a3b8;font-size:0.85rem;padding:18px 0;">查無淨買超分點資料</div>
        </div>
        """

    d_cnt = summary["danger_count"]
    t_cnt = summary["total_brokers"]
    d_lots = summary["danger_lots"]
    d_color = "#fb7185" if d_cnt > 0 else "#34d399"
    d_status_txt = f"{d_cnt} / {t_cnt} 家（{d_lots:,} 張）" if d_cnt > 0 else f"0 / {t_cnt} 家（尚未斷頭）"

    f_drop = summary["first_drop_pct"]
    f_box, f_txt, f_bcls, f_btxt = _stage_theme(f_drop)
    f_headline = f"已跌破 {f_drop:.1f}%" if f_drop >= 0 else f"再跌 {abs(f_drop):.1f}% 開始斷頭"
    f_broker = html.escape(summary["first_broker"])

    p_drop = summary["peak_drop_pct"]
    p_box, p_txt, p_bcls, p_btxt = _stage_theme(p_drop)
    p_headline = f"已引爆（破線 {p_drop:.1f}%）" if p_drop >= 0 else f"再跌 {abs(p_drop):.1f}% 爆發斷頭潮"
    p_label = html.escape(summary["peak_label"])

    return f"""
    <div class="risk-card">
      <div class="risk-card-header">
        <span class="risk-card-title">{safe_label}</span>
        <span class="risk-card-date">{safe_rng}</span>
      </div>

      <div class="danger-count-bar">
        <span style="color:#94a3b8;">目前斷頭家數</span>
        <span style="font-weight:700;color:{d_color};font-variant-numeric:tabular-nums;">{d_status_txt}</span>
      </div>

      <div class="stage-box {f_box}">
        <div class="stage-label">
          <span>① 第一道防線（首波斷頭）</span>
          <span class="badge {f_bcls}">{f_btxt}</span>
        </div>
        <div class="stage-main {f_txt}">{f_headline}</div>
        <div class="broker-highlight">首波分點：{f_broker}</div>
        <div class="stage-sub">觸發斷頭價：<strong>{summary['first_price']:,.1f} 元</strong></div>
      </div>

      <div class="stage-box {p_box}">
        <div class="stage-label">
          <span>② 最大斷頭潮（主力重災區）</span>
          <span class="badge {p_bcls}">{p_btxt}</span>
        </div>
        <div class="stage-main {p_txt}">{p_headline}</div>
        <div class="stage-sub">壓力帶 <strong>{p_label}</strong> · 約 <strong>{summary['peak_lots']:,} 張</strong></div>
      </div>

      <div class="card-footer">
        <span>加權成本：{summary['weighted_buy']:,.1f} 元</span>
        <span>均斷頭價：{summary['weighted_call']:,.1f} 元</span>
      </div>
    </div>
    """


# -----------------------------------------------------------------------------
# Main Page Search Bar (Top)
# -----------------------------------------------------------------------------
catalog = load_all_tw_stocks()

search_col1, search_col2 = st.columns([3, 2])
with search_col1:
    user_query = st.text_input(
        "🔍 搜尋台股（支援股號或公司名稱，例如：2330、台積電、群聯）",
        value="2330",
        placeholder="輸入股號或公司名稱後按 Enter...",
    )

matches = resolve_stock_query(user_query, catalog)
if not matches:
    st.warning(f"找不到符合「{user_query}」的上市櫃個股，已改顯示 2330 台積電。")
    selected_stock = {"code": "2330", "name": "台積電", "market": "上市", "close": 1035.0}
elif len(matches) == 1:
    selected_stock = matches[0]
else:
    options_map = {f"{m['code']} {m['name']} ({m['market']})": m for m in matches}
    with search_col2:
        chosen_label = st.selectbox("請選擇標的：", list(options_map.keys()))
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
    ["免費即時抓取 (證交所/櫃買 + 富邦)", "範例模擬數據 (Demo)", "上傳 CSV 檔案"],
    index=0,
)

market_type = st.sidebar.selectbox("市場別 / 融資成數預設", ["自動偵測", "上市 (60%)", "上櫃 (50%)", "自訂"], index=0)
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
# Fetch Real Stock-Level Margin Data & Broker Branch Data
# -----------------------------------------------------------------------------
fallback_close = float(detected_close) if detected_close else 100.0
if data_source.startswith("免費即時"):
    fallback_close = st.sidebar.number_input("手動覆蓋現價 (元)", min_value=1.0, value=fallback_close, step=1.0)

current_price = fallback_close
margin_hist_df = pd.DataFrame()
official_price_df = pd.DataFrame()
stock_margin_stats: Optional[dict] = None
methods_raw: Dict[str, Tuple[pd.DataFrame, str]] = {}

if data_source.startswith("免費即時"):
    official_price_df = fetch_official_daily_closes(stock_id, detected_market)
    if not official_price_df.empty and (detected_close is None or detected_close <= 0):
        current_price = float(official_price_df["收盤價"].iloc[-1])

    margin_hist_df = fetch_margin_history(stock_id)
    stock_margin_stats = compute_stock_margin_maintenance(
        margin_hist_df, official_price_df, current_price, margin_ratio_pct, maint_threshold_pct
    )

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
        st.warning("免費即時抓取分點受限，分點區塊暫以內建範例數據顯示。")
        preset = DEMO_STOCKS.get(stock_id, DEMO_STOCKS["2330"])
        if detected_close is None:
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

else:
    uploaded = st.sidebar.file_uploader("上傳 CSV（欄位：分點名稱,買進張數,賣出張數,買進均價）", type=["csv"])
    current_price = st.sidebar.number_input("個股目前收盤價 (元)", min_value=1.0, value=100.0, step=0.5)
    if uploaded is not None:
        u_df = pd.read_csv(io.BytesIO(uploaded.read()))
        methods_raw = {"自訂匯入": (u_df, uploaded.name)}
    else:
        base_df = pd.DataFrame(DEMO_STOCKS["2330"]["branches"])
        current_price = DEMO_STOCKS["2330"]["close"]
        methods_raw = {"自訂匯入": (base_df, "範例")}

methods_calc: Dict[str, Tuple[pd.DataFrame, dict, str]] = {}
for label, (raw_df, rng_str) in methods_raw.items():
    calc_df, summary = calculate_margin_metrics(raw_df, current_price, margin_ratio_pct, maint_threshold_pct)
    methods_calc[label] = (calc_df, summary, rng_str)

# -----------------------------------------------------------------------------
# Hero Header Card
# -----------------------------------------------------------------------------
st.markdown(
    f"""
    <div class="hero-box">
      <div class="hero-top">
        <div>
          <div class="stock-title">📡 {html.escape(stock_id)} {html.escape(detected_name)} <span style="font-size:0.85rem;color:#94a3b8;font-weight:500;">({html.escape(detected_market)})</span></div>
          <div class="stock-sub">融資成數 {margin_ratio_pct}% · 追繳門檻 {maint_threshold_pct}% · 紅＝已破斷頭線 ｜ 橘＝再跌 8% 內觸發 ｜ 綠＝緩衝充足</div>
        </div>
        <div class="price-pill">
          <div class="price-lbl">目前基準收盤價</div>
          <div class="price-val">{current_price:,.1f} <span style="font-size:0.95rem;font-weight:500;color:#94a3b8;">元</span></div>
        </div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------------------
# Section 1 (Primary): Stock-Level Actual Margin Maintenance & Call Trigger
# -----------------------------------------------------------------------------
st.subheader("🎯 個股真實融資維持率與全體斷頭線（排除外資與現股干擾）")

if stock_margin_stats:
    m_pct = stock_margin_stats["est_maint_pct"]
    m_drop = stock_margin_stats["drop_to_call_pct"]
    m_call = stock_margin_stats["est_call_price"]
    m_cost = stock_margin_stats["est_avg_cost"]
    m_bal = stock_margin_stats["margin_balance"]
    m_usage = stock_margin_stats["margin_usage_pct"]

    if m_pct < maint_threshold_pct:
        m_border, m_tcls, m_badge_cls, m_badge_txt = "border-danger", "text-danger", "badge-danger", "🔴 已破 130%"
    elif m_pct < maint_threshold_pct + 15:
        m_border, m_tcls, m_badge_cls, m_badge_txt = "border-warn", "text-warn", "badge-warn", "🟠 接近警戒"
    else:
        m_border, m_tcls, m_badge_cls, m_badge_txt = "border-safe", "text-safe", "badge-safe", "🟢 安全水位"

    d_border = "border-danger" if m_drop >= 0 else ("border-warn" if m_drop > -8 else "border-safe")
    d_tcls = "text-danger" if m_drop >= 0 else ("text-warn" if m_drop > -8 else "text-safe")
    d_headline = f"已跌破 {m_drop:.1f}%" if m_drop >= 0 else f"再跌 {abs(m_drop):.1f}%"

    mkt_maint = fetch_market_margin_maintenance() if data_source.startswith("免費即時") else None
    if mkt_maint:
        mk_r = mkt_maint["ratio_pct"]
        mk_border = "border-danger" if mk_r < 140 else ("border-warn" if mk_r < 155 else "border-safe")
        mk_tcls = "text-danger" if mk_r < 140 else ("text-warn" if mk_r < 155 else "text-safe")
        mk_badge_cls = "badge-danger" if mk_r < 140 else ("badge-warn" if mk_r < 155 else "badge-safe")
        mk_badge_txt = "🔴 大盤警戒" if mk_r < 140 else ("🟠 偏低震盪" if mk_r < 155 else "🟢 大盤健康")
        mkt_card_html = f"""
          <div class="official-card {mk_border}">
            <div class="o-label"><span>大盤整體融資維持率</span><span class="badge {mk_badge_cls}">{mk_badge_txt}</span></div>
            <div class="o-val {mk_tcls}">{mk_r:.2f}%</div>
            <div class="o-sub">{mkt_maint['date']} · 融資增減 {mkt_maint['change_yi']} 億</div>
          </div>
        """
    else:
        mkt_card_html = """
          <div class="official-card">
            <div class="o-label"><span>大盤整體融資維持率</span><span>自動抓取中/暫不可用</span></div>
            <div class="o-val" style="color:#94a3b8;">--</div>
            <div class="o-sub">若機房連線受限可本機執行</div>
          </div>
        """

    st.markdown(
        f"""
        <div class="official-grid">
          <div class="official-card {m_border}">
            <div class="o-label"><span>個股整體融資維持率</span><span class="badge {m_badge_cls}">{m_badge_txt}</span></div>
            <div class="o-val {m_tcls}">{m_pct:.1f}%</div>
            <div class="o-sub">融資平均成本約 {m_cost:,.1f} 元</div>
          </div>
          <div class="official-card {d_border}">
            <div class="o-label"><span>全體融資 130% 斷頭線</span><span>依近 {len(stock_margin_stats["history_df"])} 日融資買賣滾動計算</span></div>
            <div class="o-val {d_tcls}">{d_headline}</div>
            <div class="o-sub">整體斷頭價約 <strong>{m_call:,.1f} 元</strong></div>
          </div>
          <div class="official-card">
            <div class="o-label"><span>個股最新融資餘額</span><span>資料日 {stock_margin_stats['latest_date'].strftime('%Y/%m/%d')}</span></div>
            <div class="o-val text-sky">{m_bal:,} <span style="font-size:0.95rem;color:#94a3b8;">張</span></div>
            <div class="o-sub">融資使用率：{m_usage:.2f}%</div>
          </div>
          {mkt_card_html}
        </div>
        """,
        unsafe_allow_html=True,
    )
else:
    st.info("目前無該股近期融資買賣明細（可能為無信用交易標的或範例模式）。")

st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# Section 2 (Secondary): 3-Method Broker Branch Reference Cards
# -----------------------------------------------------------------------------
st.subheader("🏦 輔助參考：主力買超分點推估斷頭防線")
st.caption("提醒：分點買賣超包含現股與法人部位，僅供輔助觀察主力大戶成本壓力帶；實際融資斷頭水位請以上方「個股真實融資維持率」為主。")

cols = st.columns(len(methods_calc))
for col, (label, (_, summary, rng_str)) in zip(cols, methods_calc.items()):
    with col:
        st.markdown(render_risk_card(label, rng_str, summary), unsafe_allow_html=True)

st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# Visual Price Ladder (Horizontal Liquidation Wall) + Detailed Tabs
# -----------------------------------------------------------------------------
st.subheader("📉 下跌斷頭水位圖與分點明細")
tabs = st.tabs(list(methods_calc.keys()))
for tab, (label, (calc_df, summary, rng_str)) in zip(tabs, methods_calc.items()):
    with tab:
        if calc_df.empty or not summary or summary["wall_df"].empty:
            st.info("此區間查無淨買超分點資料。")
            continue

        wall_df = summary["wall_df"]
        st.caption(f"{label}（{rng_str}）— 各價位斷頭賣壓張數（由高價往下排列）")
        fig = px.bar(
            wall_df,
            x="潛在斷頭張數",
            y="價位區間",
            orientation="h",
            color="風險等級",
            text="潛在斷頭張數",
            color_discrete_map={
                "已觸發斷頭": "#f43f5e",
                "高危警戒": "#f59e0b",
                "安全緩衝": "#10b981",
            },
        )
        fig.update_traces(texttemplate="%{text:,} 張", textposition="outside", cliponaxis=False)
        fig.update_layout(
            height=320,
            margin=dict(l=6, r=58, t=38, b=10),
            dragmode=False,
            legend=dict(orientation="h", yanchor="bottom", y=1.04, xanchor="left", x=0, title=""),
            xaxis=dict(fixedrange=True, title="潛在斷頭賣壓 (張)"),
            yaxis=dict(fixedrange=True, title=""),
        )
        st.plotly_chart(fig, use_container_width=True, config=PLOTLY_MOBILE_CONFIG)

        st.dataframe(calc_df, use_container_width=True, hide_index=True)

# -----------------------------------------------------------------------------
# Collapsible Extra Charts & Unified Comparison Table
# -----------------------------------------------------------------------------
if stock_margin_stats is not None:
    with st.expander("📈 展開：個股近期融資維持率 & 融資餘額走勢", expanded=False):
        hist_df = stock_margin_stats["history_df"]
        fig_m = px.line(
            hist_df,
            x="日期",
            y="推估融資維持率(%)",
            markers=True,
            labels={"日期": "交易日", "推估融資維持率(%)": "推估維持率 (%)"},
        )
        fig_m.add_hline(y=maint_threshold_pct, line_dash="dash", line_color="#f43f5e", annotation_text=f"{maint_threshold_pct}% 追繳線")
        fig_m.update_layout(
            height=260,
            margin=dict(l=10, r=10, t=25, b=10),
            dragmode=False,
            xaxis=dict(fixedrange=True),
            yaxis=dict(fixedrange=True),
        )
        st.plotly_chart(fig_m, use_container_width=True, config=PLOTLY_MOBILE_CONFIG)

if len(methods_calc) > 1:
    with st.expander("📋 展開：各分點三種基準斷頭價並排對照表", expanded=False):
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
            merged_df = sub if merged_df is None else pd.merge(merged_df, sub, on="分點名稱", how="outer")

        if merged_df is not None and not merged_df.empty:
            first_price_col = [c for c in merged_df.columns if c.endswith("_斷頭價")][0]
            merged_df = merged_df.sort_values(by=first_price_col, ascending=False).reset_index(drop=True)
            st.dataframe(merged_df, use_container_width=True, hide_index=True)