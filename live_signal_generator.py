import yfinance as yf
import pandas as pd
from ta.trend import EMAIndicator
from ta.volatility import AverageTrueRange
from google.oauth2.service_account import Credentials
import gspread
from datetime import datetime

# Constants
TICKER = "AAPL"
SHEET_ID = "1hn8Bb9SFEmDTyoXJkCh1sGU1ZME49oTALtL36b5SVE"
SHEET_NAME = "Live Signals"

# Google Sheets Setup
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_file("google_creds.json", scopes=SCOPES)
gc = gspread.authorize(creds)
sheet = gc.open_by_key(SHEET_ID).worksheet(SHEET_NAME)

# Download market data
print(f"📉 Downloading data for {TICKER}...")
df = yf.download(tickers=TICKER, period="5d", interval="5m")

if df.empty:
    print("⚠️ DataFrame is empty after download.")
    exit()

# Clean up and calculate indicators
df = df[['Open', 'High', 'Low', 'Close', 'Adj Close']]

df["EMA9"] = EMAIndicator(close=df["Close"], window=9).ema_indicator()
df["EMA21"] = EMAIndicator(close=df["Close"], window=21).ema_indicator()
df["ATR"] = AverageTrueRange(df["High"], df["Low"], df["Close"]).average_true_range()

df.dropna(inplace=True)

if df.empty:
    print("⚠️ DataFrame is empty after indicator calculations.")
    exit()

# Get latest row
latest = df.iloc[-1]

# Signal logic
direction = "UP" if latest["Close"] > latest["EMA9"] > latest["EMA21"] else "DOWN"
option_type = "CALL" if direction == "UP" else "PUT"
confidence = 75
entry = round(latest["Close"], 2)
stop = round(entry + latest["ATR"], 2) if direction == "UP" else round(entry - latest["ATR"], 2)
target = round(entry + (latest["ATR"] * 2), 2) if direction == "UP" else round(entry - (latest["ATR"] * 2), 2)
strike = round(entry)
notes = "0DTE Signal"
timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# Append header row if sheet is empty
if not sheet.get_all_values():
    sheet.append_row(["Timestamp", "Ticker", "Direction", "Confidence", "Entry", "Stop", "Target", "Option Type", "Strike", "Notes"])

# Create and send the row
row = [timestamp, TICKER, direction, confidence, entry, stop, target, option_type, strike, notes]
sheet.append_row(row)
print("✅ Signal sent to Google Sheet.")
