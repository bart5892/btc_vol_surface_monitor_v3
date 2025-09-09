# BTC Vol Surface Arbitrage Monitor (Streamlit)

Compares implied volatility by **delta** across:
- US spot BTC ETF options (IBIT, FBTC, ARKB, BRRR, HODL)
- Deribit BTC options (mark IV + greeks)
- InvestDEFY BTC vol surface (delta × tenor-floating, 8am UTC grid)

## Deploy on Streamlit Cloud
- Include `runtime.txt` (Python 3.11)
- Add secret:
```toml
[investdefy]
api_key = "YOUR_INVESTDEFY_API_KEY"
```
- `pip` installs from `requirements.txt`

## Local Dev
```
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
streamlit run app.py
```
