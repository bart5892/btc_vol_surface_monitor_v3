
import requests
from datetime import datetime, timezone
from typing import List, Dict, Any
import math

DERIBIT = "https://www.deribit.com/api/v2/"

def _get(endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
    r = requests.get(DERIBIT + endpoint, params=params, timeout=20)
    r.raise_for_status()
    j = r.json()
    return j.get("result", j)

def list_instruments(currency: str = "BTC", kind: str = "option") -> List[Dict[str, Any]]:
    return _get("public/get_instruments", {"currency": currency, "kind": kind, "expired": False})

def nearest_expiry(instruments: List[Dict[str, Any]], target_date: datetime) -> List[Dict[str, Any]]:
    by_date = {}
    for ins in instruments:
        dt = datetime.fromtimestamp(ins["expiration_timestamp"]/1000, tz=timezone.utc)
        by_date.setdefault(dt.date(), []).append(ins)
    best_date = min(by_date.keys(), key=lambda d: abs(datetime(d.year, d.month, d.day, tzinfo=timezone.utc) - target_date))
    return by_date[best_date]

def fetch_mark_greeks(instrument_name: str) -> Dict[str, Any]:
    return _get("public/ticker", {"instrument_name": instrument_name})

def build_delta_buckets(instruments: List[Dict[str, Any]], targets=(0.10,0.25,0.50)) -> Dict[str, float]:
    from collections import defaultdict
    buckets = defaultdict(list)
    for ins in instruments:
        name = ins["instrument_name"]
        data = fetch_mark_greeks(name)
        mark_iv = data.get("mark_iv")
        g = data.get("greeks", {})
        delta = g.get("delta")
        if mark_iv is None or delta is None:
            continue
        absd = abs(delta)
        if abs(absd - 0.5) < 0.05:
            key = "50D"
        else:
            nearest = min(targets, key=lambda t: abs(absd - t))
            if delta < 0:
                key = f"{int(round(nearest*100))}D Put"
            else:
                key = f"{int(round(nearest*100))}D Call"
        buckets[key].append(mark_iv)
    return {k: sum(v)/len(v) for k,v in buckets.items() if v}
