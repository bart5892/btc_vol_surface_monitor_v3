
import os, requests
from typing import Dict, Any, List, Tuple
from datetime import datetime, timezone, timedelta

def _get_api_key():
    try:
        import streamlit as st
        return st.secrets["investdefy"]["api_key"]
    except Exception:
        return os.environ.get("INVESTDEFY_API_KEY", "")

def fetch_surface() -> Dict[str, Any]:
    url = "https://api.investdefy.com/v1/data/volatility-surface"
    params = {
        "asset": "BTC",
        "x_type": "delta",
        "y_type": "tenor-floating",
        "floating_ref": "8am-utc",
    }
    headers = {"accept": "application/json", "X-API-KEY": _get_api_key()}
    r = requests.get(url, params=params, headers=headers, timeout=20)
    r.raise_for_status()
    return r.json()

def parse_cross_section(surface: Dict[str, Any], target_ts: int) -> Tuple[List[str], List[float]]:
    data = surface.get("data", {})
    xinfo = data.get("x", {})
    yinfo = data.get("y", {})
    Z = data.get("data", [])

    x_type = str(xinfo.get("type", "")).lower()
    y_type = str(yinfo.get("type", "")).lower()
    x_vals = xinfo.get("values", [])
    y_vals = yinfo.get("values", [])

    def nearest_idx(arr, target):
        return min(range(len(arr)), key=lambda i: abs(arr[i] - target))

    if len(Z) == 0:
        return [], []

    if ("tenor" in y_type or (len(y_vals) > 0 and isinstance(y_vals[0], int))):
        idx = nearest_idx(y_vals, target_ts) if y_vals else 0
        x_labels = x_vals if x_vals else [f"idx{i}" for i in range(len(Z))]
        labels = []
        for lab in x_labels:
            if isinstance(lab, (int, float)):
                d = abs(int(round(float(lab)*100)))
                labels.append(f"{d}D {'Call' if lab>0 else ('Put' if lab<0 else '')}".strip())
            else:
                labels.append(str(lab))
        ivs = [row[idx] if idx < len(row) else None for row in Z]
        return labels, ivs
    else:
        idx = nearest_idx(x_vals, target_ts) if x_vals else 0
        y_labels = y_vals if y_vals else [f"idx{j}" for j in range(len(Z[0]))]
        labels = []
        for lab in y_labels:
            if isinstance(lab, (int, float)):
                d = abs(int(round(float(lab)*100)))
                labels.append(f"{d}D {'Call' if lab>0 else ('Put' if lab<0 else '')}".strip())
            else:
                labels.append(str(lab))
        ivs = [Z[i][idx] if idx < len(Z[i]) else None for i in range(len(Z))]
        return labels, ivs

def nearest_daily_timestamp(dt_utc) -> int:
    ref = dt_utc.replace(hour=8, minute=0, second=0, microsecond=0)
    if dt_utc.hour >= 8:
        return int(ref.timestamp())
    else:
        return int((ref - timedelta(days=1)).timestamp())
