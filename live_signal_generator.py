import os
import json
import yfinance as yf
import pandas as pd
from ta.trend import EMAIndicator
from ta.volatility import AverageTrueRange
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Setup
TICKER = "AAPL"
SHEET_ID = "1hn8Bb9SFEmD7y0JkCh1GLSU7ME49oTALtL36b5SVE"
SHEET_RANGE = "Live Signals!A1"
CREDS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON")

if not CREDS_JSON:
    raise ValueError("Missing GOOGLE_CREDENTIALS_JSON in environment variables")

creds_data = json.loads(CREDS_JSON)
creds = service_account.Credentials.from_service_account_info(creds_data, scopes=["https://www.googleapis.com/auth/spreadsheets"])
service = build("sheets", "v4", credentials=creds)

# Download recent data
print("📉 Downloading data for", TICKER)
df = yf.download(TICKER, period="5d", interval="5m")
print(f"✅ Downloaded {len(df)} rows")

# Ensure columns are accessible
df = df[["Open", "High", "Low", "Close", "Adj Close"]]
print(f"🧩 Final columns: {list(df.columns)}")

# Add indicators
df["EMA9"] = EMAIndicator(close=df["Close"], window=9).ema_indicator()
df["EMA21"] = EMAIndicator(close=df["Close"], window=21).ema_indicator()
df["ATR"] = AverageTrueRange(high=df["High"], low=df["Low"], close=df["Close"]).average_true_range()

# Drop rows with NaNs
df.dropna(inplace=True)

# Exit if nothing left
if df.empty:
    print("⚠️ DataFrame is empty after indicator calculations. Exiting.")
    exit()

# Latest signal logic
latest = df.iloc[-1]
direction = "UP" if latest["Close"] > latest["EMA9"] > latest["EMA21"] else "DOWN"

option_type = "CALL" if direction == "UP" else "PUT"
strike = round(latest["Close"])
target = round(latest["Close"] + (2 * latest["ATR"])) if direction == "UP" else round(latest["Close"] - (2 * latest["ATR"]))
stop = round(latest["Close"] - latest["ATR"]) if direction == "UP" else round(latest["Close"] + latest["ATR"])

signal_row = [
    datetime.now().strftime("%Y-%m-%d %H:%M"),
    TICKER,
    direction,
    75,
    round(latest["Close"], 2),
    round(stop, 2),
    round(target, 2),
    option_type,
    strike,
    "0DTE Signal"
]

# Check if headers are present, if not, insert them
sheet = service.spreadsheets()
result = sheet.values().get(spreadsheetId=SHEET_ID, range=SHEET_RANGE).execute()
values = result.get("values", [])

if not values:
    headers = ["Timestamp", "Ticker", "Direction", "Expected % Move", "Entry Price", "Stop", "Target", "Option Type", "Strike", "Notes"]
    sheet.values().append(
        spreadsheetId=SHEET_ID,
        range=SHEET_RANGE,
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body={"values": [headers]}
    ).execute()

# Send signal to Google Sheet
sheet.values().append(
    spreadsheetId=SHEET_ID,
    range=SHEET_RANGE,
    valueInputOption="USER_ENTERED",
    insertDataOption="INSERT_ROWS",
    body={"values": [signal_row]}
).execute()

print("✅ Signal sent to Google Sheet.")
