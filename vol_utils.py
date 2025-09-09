
import math
from typing import Optional
import numpy as np

SQRT_2PI = math.sqrt(2.0 * math.pi)

def norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

def bs_price(call: bool, S: float, K: float, T: float, r: float, vol: float) -> float:
    if T <= 0 or vol <= 0 or S <= 0 or K <= 0:
        return max(0.0, (S - K) if call else (K - S))
    d1 = (math.log(S / K) + (r + 0.5 * vol * vol) * T) / (vol * math.sqrt(T))
    d2 = d1 - vol * math.sqrt(T)
    if call:
        return S * norm_cdf(d1) - K * math.exp(-r * T) * norm_cdf(d2)
    else:
        return K * math.exp(-r * T) * norm_cdf(-d2) - S * norm_cdf(-d1)

def bs_delta(call: bool, S: float, K: float, T: float, r: float, vol: float) -> float:
    if T <= 0 or vol <= 0 or S <= 0 or K <= 0:
        if call:
            return 1.0 if S > K else 0.0
        else:
            return -1.0 if S < K else 0.0
    d1 = (math.log(S / K) + (r + 0.5 * vol * vol) * T) / (vol * math.sqrt(T))
    return norm_cdf(d1) - (0.0 if call else 1.0)

def iv_from_price(call: bool, S: float, K: float, T: float, r: float, price: float,
                  tol: float = 1e-6, max_iter: int = 100) -> Optional[float]:
    if T <= 0 or S <= 0 or K <= 0 or price <= 0:
        return None
    intrinsic = max(0.0, (S - K) if call else (K - S))
    if price < intrinsic:
        price = intrinsic
    lo, hi = 1e-6, 5.0
    plo = bs_price(call, S, K, T, r, lo) - price
    phi = bs_price(call, S, K, T, r, hi) - price
    iters = 0
    while plo * phi > 0 and hi < 10.0 and iters < 25:
        hi *= 1.5
        phi = bs_price(call, S, K, T, r, hi) - price
        iters += 1
    if plo * phi > 0:
        return None
    for _ in range(max_iter):
        mid = 0.5 * (lo + hi)
        pm = bs_price(call, S, K, T, r, mid) - price
        if abs(pm) < tol:
            return mid
        if plo * pm <= 0:
            hi = mid
            phi = pm
        else:
            lo = mid
            plo = pm
    return 0.5 * (lo + hi)
