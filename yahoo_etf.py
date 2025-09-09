
from typing import Dict, Any, List
from datetime import datetime, timezone
import numpy as np
import pandas as pd
import yfinance as yf
from dateutil import parser as dateparser
from vol_utils import iv_from_price, bs_delta

def fetch_spot(symbol: str) -> float:
    t = yf.Ticker(symbol)
    fast = getattr(t, "fast_info", {})
    if fast and "last_price" in fast:
        return float(fast["last_price"])
    hist = t.history(period="1d")
    if hist.empty:
        raise RuntimeError("No price for symbol")
    return float(hist["Close"][-1])

def list_expirations(symbol: str) -> List[str]:
    t = yf.Ticker(symbol)
    return t.options

def load_chain(symbol: str, expiry: str) -> pd.DataFrame:
    t = yf.Ticker(symbol)
    chain = t.option_chain(expiry)
    calls = chain.calls.copy()
    puts = chain.puts.copy()
    calls["type"] = "C"
    puts["type"] = "P"
    df = pd.concat([calls, puts], ignore_index=True, sort=False)
    df["expiry"] = expiry
    return df

def compute_iv_by_delta(symbol: str, expiry: str, r: float = 0.04, targets=(0.10,0.25,0.50)) -> Dict[str, float]:
    S = fetch_spot(symbol)
    df = load_chain(symbol, expiry)
    t_exp = dateparser.parse(expiry).replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    T = max((t_exp - now).days/365.0, 0.0001)

    df["mid"] = (df["bid"].fillna(0) + df["ask"].fillna(0)) / 2.0
    df["lastPrice"] = df["lastPrice"].fillna(df["mid"])
    res = []
    for _, row in df.iterrows():
        K = float(row["strike"])
        call = row["type"] == "C"
        px = row.get("mid", np.nan)
        px = float(px) if pd.notna(px) and px > 0 else float(row.get("lastPrice", np.nan))
        if not pd.notna(px) or px <= 0:
            continue
        ivcol = row.get("impliedVolatility", np.nan)
        iv = float(ivcol) if pd.notna(ivcol) and ivcol > 0 else iv_from_price(call, S, K, T, r, px)
        if iv is None or iv <= 0:
            continue
        d = bs_delta(call, S, K, T, r, iv)
        res.append((d, iv))
    buckets = {}
    for d, iv in res:
        absd = abs(d)
        if abs(absd - 0.5) < 0.05:
            key = "50D"
        else:
            nearest = min(targets, key=lambda t: abs(absd - t))
            key = f"{int(round(nearest*100))}D {'Put' if d<0 else 'Call'}"
        buckets.setdefault(key, []).append(iv)
    return {k: float(np.nanmean(v)) for k,v in buckets.items() if v}
