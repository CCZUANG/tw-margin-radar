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
        padding-top: 3.4rem !important;
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
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
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
        gap: 6px;
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
    """Load real TWSE (上市) and TPEx (上櫃) stock codes and names."""
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
    if partial:
        return partial[:20]

    # If catalog failed to load but user typed a numeric stock code, allow direct lookup
    if re.match(r"^\d{4,6}[A-Za-z]?$", first_token):
        return [{"code": first_token, "name": "", "market": "上市", "close": None}]

    return []


@st.cache_data(ttl=120)
def fetch_yahoo_latest_price(stock_id: str, market: str) -> Tuple[Optional[float], Optional[str]]:
    """Fetch freshest real-time/latest closing price from Yahoo Finance Taiwan (.TW / .TWO)."""
    suffixes = [".TWO", ".TW"] if market == "上櫃" else [".TW", ".TWO"]
    for sfx in suffixes:
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{stock_id}{sfx}?interval=1d&range=5d"
            resp = requests.get(url, headers=HEADERS, timeout=8)
            if resp.status_code != 200:
                continue
            meta = resp.json()["chart"]["result"][0]["meta"]
            price = meta.get("regularMarketPrice") or meta.get("previousClose")
            ts = meta.get("regularMarketTime")
            if price and float(price) > 0:
                dt_str = (
                    (datetime.utcfromtimestamp(int(ts)) + timedelta(hours=8)).strftime("%Y/%m/%d")
                    if ts
                    else "最新"
                )
                return float(price), dt_str
        except Exception:
            continue
    return None, None


@st.cache_data(ttl=1800)
def fetch_official_daily_closes(stock_id: str, market: str) -> pd.DataFrame:
    """Fetch recent 6 months (~120+ trading days) of official daily closing prices."""
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


@st.cache_data(ttl=1800)
def fetch_market_margin_maintenance() -> Optional[dict]:
    """Fetch latest Taiwan market-wide margin maintenance ratio (%) from public KGI page."""
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

        m_ratio = re.search(r"融資維持率\s*([\d.]+)\s*%", text)
        m_date = re.search(r"(\d{4}/\d{1,2}/\d{1,2})\s*融資維持率", text)
        m_chg = re.search(r"融資增減\s*([+\-]?[\d,]+\.\d+|[+\-]?[\d,]+)\s*億", text)
        if m_ratio:
            return {
                "date": m_date.group(1) if m_date else "最新交易日",
                "ratio_pct": float(m_ratio.group(1)),
                "change_yi": m_chg.group(1) if m_chg else "--",
            }
    except Exception:
        pass
    return None


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
    """Fetch up to ~120 trading days of real daily margin purchase/sell/balance from Fubon DJ."""
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
    if margin_df.empty or current_price <= 0:
        return None

    df = margin_df.copy()
    if not price_df.empty:
        df = pd.merge(df, price_df, on="日期", how="left")
        df["收盤價"] = df["收盤價"].ffill().bfill().fillna(current_price)
    else:
        df["收盤價"] = current_price

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

    # Try static single-page URL format as last real-data attempt
    for fallback_url in (
        f"https://fubon-ebrokerdj.fbs.com.tw/z/zc/zco/zco_{stock_id}.djhtm",
        f"https://fubon-ebrokerdj.fbs.com.tw/z/zc/zco/zco.djhtm?a={stock_id}&e=",
    ):
        try:
            resp = requests.get(fallback_url, headers=HEADERS, timeout=12)
            if resp.status_code != 200:
                continue
            resp.encoding = resp.apparent_encoding or "big5"
            day_rows, parsed_cost = _parse_fubon_dj_page(resp.text)
            if day_rows:
                day_cost = (
                    parsed_cost
                    if (parsed_cost and fallback_price * 0.85 <= parsed_cost <= fallback_price * 1.15)
                    else fallback_price
                )
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
        except Exception:
            continue

    raise RuntimeError("無法取得真實分點資料（富邦公開網頁目前無回應或受雲端機房 IP 限制）")


def calculate_margin_metrics(
    df: pd.DataFrame, current_price: float, margin_ratio_pct: float, maint_threshold_pct: float
) -> Tuple[pd.DataFrame, dict]:
    if df.empty or current_price <= 0:
        return pd.DataFrame(), {}

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



@st.cache_data(ttl=1800)
def fetch_market_daily_liquidation_scan() -> Optional[dict]:
    """
    Scan all TWSE listed marginable stocks via TWSE OpenAPI (MI_MARGN + STOCK_DAY_ALL)
    to identify stocks with price drops + heavy margin reduction (suspected margin calls/washout).
    """
    try:
        m_resp = requests.get(
            "https://openapi.twse.com.tw/v1/exchangeReport/MI_MARGN", headers=HEADERS, timeout=12
        )
        p_resp = requests.get(
            "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL", headers=HEADERS, timeout=12
        )
        m_resp.raise_for_status()
        p_resp.raise_for_status()

        price_map: Dict[str, dict] = {}
        for r in p_resp.json():
            c = str(r.get("Code", "")).strip()
            close_p = _parse_float(r.get("ClosingPrice"))
            chg = _parse_float(r.get("Change"))
            if c and close_p and close_p > 0:
                prev_p = close_p - (chg or 0.0)
                chg_pct = ((chg or 0.0) / prev_p * 100.0) if prev_p > 0 else 0.0
                price_map[c] = {"close": close_p, "chg_pct": round(chg_pct, 2)}

        total_margin_stocks = 0
        total_net_chg = 0
        washout_rows: List[dict] = []

        for r in m_resp.json():
            code = str(r.get("股票代號", "")).strip()
            name = str(r.get("股票名稱", "")).strip()
            prev_bal = _parse_float(r.get("融資前日餘額")) or 0.0
            today_bal = _parse_float(r.get("融資今日餘額")) or 0.0
            m_sell = _parse_float(r.get("融資賣出")) or 0.0

            if prev_bal <= 0 and today_bal <= 0:
                continue

            total_margin_stocks += 1
            net_chg = int(round(today_bal - prev_bal))
            total_net_chg += net_chg

            p_info = price_map.get(code)
            if not p_info:
                continue

            drop_ratio_pct = (net_chg / prev_bal * 100.0) if prev_bal > 0 else 0.0

            # Suspected margin liquidation / forced washout:
            # Price dropped AND margin balance shrank noticeably (>= 3% or >= 300 lots)
            if p_info["chg_pct"] < 0 and (drop_ratio_pct <= -3.0 or net_chg <= -300) and prev_bal >= 100:
                washout_rows.append(
                    {
                        "股號": code,
                        "名稱": name,
                        "收盤價": p_info["close"],
                        "漲跌幅(%)": p_info["chg_pct"],
                        "融資淨減(張)": net_chg,
                        "融資減幅(%)": round(drop_ratio_pct, 2),
                        "融資賣出(張)": int(m_sell),
                        "融資餘額(張)": int(today_bal),
                    }
                )

        washout_df = pd.DataFrame(washout_rows)
        if not washout_df.empty:
            washout_df = washout_df.sort_values(by=["融資淨減(張)", "融資減幅(%)"], ascending=[True, True]).reset_index(drop=True)

        ratio_of_market = (len(washout_df) / total_margin_stocks * 100.0) if total_margin_stocks > 0 else 0.0
        return {
            "total_margin_stocks": total_margin_stocks,
            "washout_count": len(washout_df),
            "washout_ratio_pct": round(ratio_of_market, 2),
            "total_net_chg": total_net_chg,
            "washout_df": washout_df,
        }
    except Exception:
        return None


@st.cache_data(ttl=900)
def scan_top_sell_brokers_for_stocks(stock_codes: Tuple[str, ...]) -> pd.DataFrame:
    """Fetch latest sell-side broker branches for top washout stocks and rank heaviest sellers."""
    agg: Dict[str, dict] = {}
    for code in stock_codes:
        url = f"https://fubon-ebrokerdj.fbs.com.tw/z/zc/zco/zco_{code}.djhtm"
        try:
            resp = requests.get(url, headers=HEADERS, timeout=10)
            if resp.status_code != 200:
                continue
            resp.encoding = resp.apparent_encoding or "big5"
            soup = BeautifulSoup(resp.text, "lxml")
            for tr in soup.find_all("tr"):
                tds = [td.get_text(strip=True) for td in tr.find_all("td")]
                # Right half of table (columns 5..9) holds 賣超券商, 買進, 賣出, 賣超, 佔比
                if len(tds) >= 9:
                    broker = tds[5]
                    if not broker or broker in ("賣超券商", "合計", "總計"):
                        continue
                    try:
                        sell_net = int(tds[8].replace(",", ""))
                        if sell_net > 0:
                            if broker not in agg:
                                agg[broker] = {"賣超張數": 0, "涉及檔數": 0}
                            agg[broker]["賣超張數"] += sell_net
                            agg[broker]["涉及檔數"] += 1
                    except ValueError:
                        continue
        except Exception:
            continue

    if not agg:
        return pd.DataFrame()
    rows = [{"券商分點": k, "合計賣超(張)": v["賣超張數"], "砍倉檔數": v["涉及檔數"]} for k, v in agg.items()]
    return pd.DataFrame(rows).sort_values(by="合計賣超(張)", ascending=False).head(15).reset_index(drop=True)

# -----------------------------------------------------------------------------
# Main Page Search Bar (Top)
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# Top Market-Wide Daily Suspected Margin Liquidation Scanner
# -----------------------------------------------------------------------------
st.subheader("🚨 全台股當日融資急殺／疑似斷頭掃描（上市全市場）")
mkt_scan = fetch_market_daily_liquidation_scan()
if mkt_scan:
    sc_cnt = mkt_scan["washout_count"]
    sc_tot = mkt_scan["total_margin_stocks"]
    sc_pct = mkt_scan["washout_ratio_pct"]
    sc_net = mkt_scan["total_net_chg"]
    sc_border = "border-danger" if sc_pct >= 15 else ("border-warn" if sc_pct >= 5 else "border-safe")
    sc_tcls = "text-danger" if sc_pct >= 15 else ("text-warn" if sc_pct >= 5 else "text-safe")

    st.markdown(
        f"""
        <div class="official-grid">
          <div class="official-card {sc_border}">
            <div class="o-label"><span>當日疑似斷頭／融資急殺家數</span><span>股價跌且融資大減</span></div>
            <div class="o-val {sc_tcls}">{sc_cnt} <span style="font-size:0.95rem;color:#94a3b8;">/ {sc_tot} 檔</span></div>
            <div class="o-sub">佔全體上市融資股 <strong>{sc_pct:.2f}%</strong></div>
          </div>
          <div class="official-card">
            <div class="o-label"><span>上市全市場單日融資淨變動</span><span>TWSE MI_MARGN</span></div>
            <div class="o-val {'text-danger' if sc_net < 0 else 'text-sky'}">{sc_net:+,} <span style="font-size:0.95rem;color:#94a3b8;">張</span></div>
            <div class="o-sub">{'整體融資呈現退場減肥' if sc_net < 0 else '整體融資呈現淨增加'}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    washout_df = mkt_scan["washout_df"]
    if not washout_df.empty:
        with st.expander(f"📋 展開：當日疑似斷頭重災股排行（前 {min(15, len(washout_df))} 檔）與重災分點掃描", expanded=False):
            st.dataframe(washout_df.head(15), use_container_width=True, hide_index=True)
            top5_codes = tuple(washout_df["股號"].head(5).tolist())
            if st.button("🔍 一鍵掃描前 5 大重災股：哪家分點砍最多"):
                with st.spinner("正在掃描前 5 大重災股賣超分點..."):
                    top_sellers = scan_top_sell_brokers_for_stocks(top5_codes)
                if not top_sellers.empty:
                    st.caption(f"統計標的：{', '.join(top5_codes)}（依最新一日賣超張數加總排行）")
                    st.dataframe(top_sellers, use_container_width=True, hide_index=True)
                else:
                    st.warning("目前無法從公開分點網頁取得賣超排行（可能受雲端機房 IP 限制）。")
    else:
        st.caption("最新交易日無符合「股價下跌且單日融資大減 ≥3% 或 ≥300 張」的上市個股。")
else:
    st.caption("全市場融資掃描暫時無法連線至證交所 OpenAPI。")

catalog = load_all_tw_stocks()

search_col1, search_col2 = st.columns([3, 2])
with search_col1:
    user_query = st.text_input(
        "🔍 搜尋個股（股號或公司名稱）",
        value="2330",
        placeholder="例如：2330、台積電、群聯",
    )

matches = resolve_stock_query(user_query, catalog)
if not matches:
    st.error(f"找不到符合「{user_query}」的上市櫃個股，請確認股號或公司名稱是否正確。")
    st.stop()
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
# Sidebar Advanced Settings (Zero Demo/Fake Data)
# -----------------------------------------------------------------------------
st.sidebar.title("⚙️ 進階參數設定")

data_source = st.sidebar.radio(
    "資料來源",
    ["即時抓取真實資料 (Yahoo + 證交所/櫃買 + 富邦)", "上傳 CSV 分點檔案"],
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
# Fetch Real Price, Real Stock Margin History, and Real Broker Branches
# -----------------------------------------------------------------------------
current_price: Optional[float] = None
price_meta_label = "最新報價"
margin_hist_df = pd.DataFrame()
official_price_df = pd.DataFrame()
stock_margin_stats: Optional[dict] = None
methods_raw: Dict[str, Tuple[pd.DataFrame, str]] = {}
branch_error_msg: Optional[str] = None

# Always resolve real stock price first (never fall back to fake demo prices)
official_price_df = fetch_official_daily_closes(stock_id, detected_market)
yf_price, yf_date = fetch_yahoo_latest_price(stock_id, detected_market)

if yf_price and yf_price > 0:
    current_price = yf_price
    price_meta_label = f"最新報價（Yahoo · {yf_date}）"
elif not official_price_df.empty:
    current_price = float(official_price_df["收盤價"].iloc[-1])
    latest_d = official_price_df["日期"].iloc[-1].strftime("%Y/%m/%d")
    price_meta_label = f"官方收盤價（{latest_d}）"
elif detected_close and detected_close > 0:
    current_price = float(detected_close)
    price_meta_label = "交易所 OpenAPI 收盤價"

if current_price is None or current_price <= 0:
    st.error(f"目前無法取得 {stock_id} {detected_name} 的真實報價，請稍後重試。")
    st.stop()

if data_source.startswith("即時抓取"):
    margin_hist_df = fetch_margin_history(stock_id, trading_days=120)
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

    for label, s_dt, e_dt in targets:
        try:
            df_m, rng_str = fetch_fubon_dj_range_weighted(
                stock_id, s_dt, e_dt, current_price, official_price_df, chunks=4
            )
            methods_raw[label] = (df_m, rng_str)
        except Exception as e:
            branch_error_msg = str(e)
            break
else:
    uploaded = st.sidebar.file_uploader("上傳 CSV（欄位：分點名稱,買進張數,賣出張數,買進均價）", type=["csv"])
    if uploaded is not None:
        u_df = pd.read_csv(io.BytesIO(uploaded.read()))
        methods_raw = {"自訂匯入": (u_df, uploaded.name)}
    else:
        branch_error_msg = "請在左側側邊欄上傳分點 CSV 檔案（欄位：分點名稱,買進張數,賣出張數,買進均價）。"

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
          <div class="price-lbl">{html.escape(price_meta_label)}</div>
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
    m_days = len(stock_margin_stats["history_df"])

    if m_pct < maint_threshold_pct:
        m_border, m_tcls, m_badge_cls, m_badge_txt = "border-danger", "text-danger", "badge-danger", "🔴 已破 130%"
    elif m_pct < maint_threshold_pct + 15:
        m_border, m_tcls, m_badge_cls, m_badge_txt = "border-warn", "text-warn", "badge-warn", "🟠 接近警戒"
    else:
        m_border, m_tcls, m_badge_cls, m_badge_txt = "border-safe", "text-safe", "badge-safe", "🟢 安全水位"

    d_border = "border-danger" if m_drop >= 0 else ("border-warn" if m_drop > -8 else "border-safe")
    d_tcls = "text-danger" if m_drop >= 0 else ("text-warn" if m_drop > -8 else "text-safe")
    d_headline = f"已跌破 {m_drop:.1f}%" if m_drop >= 0 else f"再跌 {abs(m_drop):.1f}%"

    mkt_maint = fetch_market_margin_maintenance()
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
        mkt_card_html = ""

    st.markdown(
        f"""
        <div class="official-grid">
          <div class="official-card {m_border}">
            <div class="o-label"><span>個股整體融資維持率</span><span class="badge {m_badge_cls}">{m_badge_txt}</span></div>
            <div class="o-val {m_tcls}">{m_pct:.1f}%</div>
            <div class="o-sub">融資平均成本約 {m_cost:,.1f} 元</div>
          </div>
          <div class="official-card {d_border}">
            <div class="o-label"><span>全體融資 {maint_threshold_pct}% 斷頭線</span><span>近 {m_days} 日滾動</span></div>
            <div class="o-val {d_tcls}">{d_headline}</div>
            <div class="o-sub">整體斷頭價約 <strong>{m_call:,.1f} 元</strong></div>
          </div>
          <div class="official-card">
            <div class="o-label"><span>個股最新融資餘額</span><span>{stock_margin_stats['latest_date'].strftime('%Y/%m/%d')}</span></div>
            <div class="o-val text-sky">{m_bal:,} <span style="font-size:0.95rem;color:#94a3b8;">張</span></div>
            <div class="o-sub">融資使用率：{m_usage:.2f}%</div>
          </div>
          {mkt_card_html}
        </div>
        """,
        unsafe_allow_html=True,
    )
else:
    st.warning("目前無法抓取該股的融資買賣歷史明細（可能無信用交易資格或雲端連線受限）。")

st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# Section 2 (Secondary): 3-Method Broker Branch Reference Cards
# -----------------------------------------------------------------------------
st.subheader("🏦 輔助參考：主力買超分點推估斷頭防線")

if branch_error_msg or not methods_calc:
    st.error(branch_error_msg or "目前查無真實分點資料，請稍後重試或改用本機網路執行 `streamlit run app.py`。")
else:
    st.caption("提醒：分點買賣超包含現股與法人部位，僅供輔助觀察主力成本壓力帶；實際融資斷頭水位請以上方「個股真實融資維持率」為主。")
    cols = st.columns(len(methods_calc))
    for col, (label, (_, summary, rng_str)) in zip(cols, methods_calc.items()):
        with col:
            st.markdown(render_risk_card(label, rng_str, summary), unsafe_allow_html=True)

    st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)

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

if stock_margin_stats is not None:
    with st.expander("📈 展開：個股近期融資維持率走勢（120 日滾動）", expanded=False):
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