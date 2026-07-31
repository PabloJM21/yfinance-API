import yfinance as yf
import datetime

t = yf.Ticker("AAPL")

# Force Yahoo to return fresh metadata
t.history(period="1d", interval="1m")

ts = t.history_metadata["regularMarketTime"]
meta = t.history_metadata
ts = meta.get("regularMarketTime")

print(ts)
print(datetime.datetime.fromtimestamp(ts, datetime.UTC))
