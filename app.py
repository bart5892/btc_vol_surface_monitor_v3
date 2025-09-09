
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from dateutil import parser as dateparser
import sys, os
sys.path.append(os.path.dirname(__file__))

from providers.investdefy import fetch_surface, parse_cross_section
from providers.deribit import list_instruments, nearest_expiry, build_delta_buckets
from providers.yahoo_etf import list_expirations, compute_iv_by_delta

st.set_page_config(page_title="BTC Vol Surface Arbitrage Monitor", layout="wide")

st.title("BTC Vol Surface Arbitrage Monitor")
st.caption("Cross-market IV by delta: Spot BTC ETFs vs Deribit vs InvestDEFY surface")

with st.sidebar:
    st.header("Settings")
    etf = st.selectbox("Spot BTC ETF", ["IBIT", "FBTC", "ARKB", "BRRR", "HODL"], index=0)
    try:
        exp_list = list_expirations(etf)
    except Exception as e:
        exp_list = []
        st.error(f"Failed to load ETF expirations: {e}")
    expiry = st.selectbox("ETF Expiry", exp_list, index=0 if exp_list else None)
    delta_targets = st.multiselect(
        "Delta Buckets",
        ["10D Put","25D Put","50D","25D Call","10D Call"],
        default=["10D Put","25D Put","50D","25D Call","10D Call"]
    )
    spread_threshold = st.slider("Alert threshold (IV pts vs InvestDEFY)", 0.0, 0.5, 0.05, 0.01)
    run_btn = st.button("Run / Refresh", type="primary")

if run_btn and expiry:
    cols = st.columns(3)
    with cols[0]:
        st.subheader(f"{etf} options (Yahoo)")
        try:
            etf_iv = compute_iv_by_delta(etf, expiry)
            st.write(etf_iv)
        except Exception as e:
            st.error(f"ETF calc failed: {e}")
            etf_iv = {}

    with cols[1]:
        st.subheader("Deribit (mark IV by delta)")
        try:
            ins = list_instruments("BTC", "option")
            exp_dt = dateparser.parse(expiry).replace(tzinfo=timezone.utc)
            ins_exp = nearest_expiry(ins, exp_dt)
            deribit_iv = build_delta_buckets(ins_exp, targets=(0.10,0.25,0.50))
            st.write(deribit_iv)
        except Exception as e:
            st.error(f"Deribit fetch failed: {e}")
            deribit_iv = {}

    with cols[2]:
        st.subheader("InvestDEFY Surface (delta cross-section)")
        try:
            surface = fetch_surface()
            exp_dt = dateparser.parse(expiry).replace(tzinfo=timezone.utc)
            target_ts = int(exp_dt.timestamp())
            labels, ivs = parse_cross_section(surface, target_ts)
            investdefy_cs = dict(zip(labels, ivs))
            st.write(investdefy_cs)
        except Exception as e:
            st.error(f"InvestDEFY fetch failed: {e}")
            investdefy_cs = {}

    st.markdown("---")
    st.subheader("Comparison Table (IV)")
    rows = []
    for label in delta_targets:
        rows.append({
            "Delta Bucket": label,
            f"{etf}": etf_iv.get(label, np.nan),
            "Deribit": deribit_iv.get(label, np.nan),
            "InvestDEFY": investdefy_cs.get(label, np.nan),
        })
    df = pd.DataFrame(rows)
    st.dataframe(df.set_index("Delta Bucket"), height=260, use_container_width=True)

    st.subheader("Spreads vs InvestDEFY (IV pts)")
    for col in [f"{etf}", "Deribit"]:
        df[f"{col} - InvestDEFY"] = df[col] - df["InvestDEFY"]
    st.dataframe(df[["Delta Bucket", f"{etf} - InvestDEFY", "Deribit - InvestDEFY"]].set_index("Delta Bucket"),
                 height=240, use_container_width=True)

    st.subheader("Large Divergences")
    alerts = []
    for _, r in df.iterrows():
        for col in [f"{etf} - InvestDEFY", "Deribit - InvestDEFY"]:
            val = r.get(col, np.nan)
            if pd.notna(val) and abs(val) >= spread_threshold:
                alerts.append({"Delta Bucket": r["Delta Bucket"], "Leg": col, "Spread": float(val)})
    if alerts:
        st.success(f"Found {len(alerts)} divergences ≥ {spread_threshold:.2f} IV pts")
        st.dataframe(pd.DataFrame(alerts).set_index("Delta Bucket"), use_container_width=True)
    else:
        st.info("No spreads above threshold.")
else:
    st.info("Select an ETF expiry and click **Run / Refresh**.")
