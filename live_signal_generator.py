import yfinance as yf
import pandas as pd
from ta.trend import EMAIndicator
from ta.volatility import AverageTrueRange
import datetime
import json
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# === SETTINGS ===
TICKER = "AAPL"
SHEET_ID = "1hn8Bb9SFEmDTyoXJkCh1GU5T2ME49oTALtL36b5SVE"
SHEET_NAME = "Live Signals!A1:I1"  # Sheet name + header range
JSON_KEY = os.getenv("GOOGLE_CREDENTIALS_JSON")

# === FETCH & PROCESS DATA ===
df = yf.download(TICKER, period="5d", interval="5m")

# Flatten multi-level columns if necessary
df.columns = [' '.join(col).strip() if isinstance(col, tuple) else col for col in df.columns]

# Keep only necessary columns
df = df[["Open", "High", "Low", "Close", "Adj Close"]]

# Calculate indicators
df["EMA9"] = EMAIndicator(close=df["Close"], window=9).ema_indicator()
df["EMA21"] = EMAIndicator(close=df["Close"], window=21).ema_indicator()
df["ATR"] = AverageTrueRange(high=df["High"], low=df["Low"], close=df["Close"]).average_true_range()

# Drop rows with NaN
df.dropna(inplace=True)
if df.empty:
    print("⚠️ DataFrame is empty after indicator calculations. Exiting.")
    exit()

# Get latest row
latest = df.iloc[-1]
direction = "UP" if latest["Close"] > latest["EMA9"] > latest["EMA21"] else "DOWN"
strike = round(latest["Close"] / 5) * 5
option_type = "CALL" if direction == "UP" else "PUT"

# === FORMAT DATA FOR SHEET ===
now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
row_data = [
    now,
    TICKER,
    direction,
    round(latest["ATR"], 2),
    round(latest["Low"], 2),
    round(latest["High"], 2),
    round(latest["Close"], 2),
    option_type,
    strike,
    "0DTE Signal"
]

# === SEND TO GOOGLE SHEET ===
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(JSON_KEY), scope)
client = gspread.authorize(creds)
sheet = client.open_by_key(SHEET_ID)
worksheet = sheet.worksheet("Live Signals")

# Add headers if the sheet is empty
if worksheet.acell('A1').value is None:
    worksheet.append_row([
        "Timestamp", "Ticker", "Direction", "ATR", "Low", "High",
        "Close", "Option Type", "Strike", "Note"
    ])

# Append new signal
worksheet.append_row(row_data)
print("✅ Signal sent to Google Sheet.")
