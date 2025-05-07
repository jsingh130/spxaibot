import os
import json
import yfinance as yf
import pandas as pd
from datetime import datetime
from ta.trend import EMAIndicator
from ta.volatility import AverageTrueRange
from google.oauth2 import service_account
from googleapiclient.discovery import build

# === SETTINGS ===
TICKER = "AAPL"  # Change to "^GSPC" for SPX
SHEET_ID = "1hn8Bb9SFEmDTyoMJkCshlGUST2ME49oTALtL36b5SVE"
SHEET_RANGE = "Live Signals!A1"
CREDS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON")

# === AUTHENTICATE GOOGLE SHEETS ===
if not CREDS_JSON:
    raise ValueError("Missing GOOGLE_CREDENTIALS_JSON in environment variables")

creds_data = json.loads(CREDS_JSON)
credentials = service_account.Credentials.from_service_account_info(
    creds_data, scopes=["https://www.googleapis.com/auth/spreadsheets"]
)
sheet_service = build("sheets", "v4", credentials=credentials)

# === DOWNLOAD MARKET DATA ===
print(f"🟡 Downloading data for {TICKER}...")
df = yf.download(TICKER, interval="5m", period="5d")

# Drop ticker level from multi-index columns if present
if isinstance(df.columns, pd.MultiIndex):
    df.columns = df.columns.droplevel(0)

# Rename columns safely
standard_names = ["Open", "High", "Low", "Close", "Adj Close", "Volume"]
df.columns = standard_names[:len(df.columns)]

print("📋 Final columns:", df.columns.tolist())
print(f"✅ Downloaded {len(df)} rows")

# === CALCULATE INDICATORS ===
df["EMA9"] = EMAIndicator(close=df["Close"], window=9).ema_indicator()
df["EMA21"] = EMAIndicator(close=df["Close"], window=21).ema_indicator()
df["ATR"] = AverageTrueRange(high=df["High"], low=df["Low"], close=df["Close"]).average_true_range()

df.dropna(inplace=True)
if df.empty:
    print("⚠️ DataFrame is empty after indicator calculations. Exiting.")
    exit()

# === GENERATE SIGNAL ===
latest = df.iloc[-1]
direction = "UP" if latest["Close"] > latest["EMA9"] > latest["EMA21"] else "DOWN"
confidence = 85 if direction == "UP" else 75
entry = round(latest["Close"], 2)
sl = round(entry - latest["ATR"], 2) if direction == "UP" else round(entry + latest["ATR"], 2)
tp = round(entry + 2 * latest["ATR"], 2) if direction == "UP" else round(entry - 2 * latest["ATR"], 2)
strike = int(round(entry / 5) * 5)
option_type = "CALL" if direction == "UP" else "PUT"

row = [[
    datetime.now().strftime("%Y-%m-%d %H:%M"),
    TICKER,
    direction,
    confidence,
    entry,
    sl,
    tp,
    option_type,
    strike,
    "0DTE Signal"
]]

# === CHECK HEADERS & SEND DATA ===
sheet = sheet_service.spreadsheets()
existing = sheet.values().get(spreadsheetId=SHEET_ID, range=SHEET_RANGE).execute()
if not existing.get("values"):
    headers = ["Timestamp", "Ticker", "Direction", "Confidence", "Entry", "Stop", "Target", "Option Type", "Strike", "Notes"]
    sheet.values().append(
        spreadsheetId=SHEET_ID,
        range=SHEET_RANGE,
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body={"values": [headers]}
    ).execute()

sheet.values().append(
    spreadsheetId=SHEET_ID,
    range=SHEET_RANGE,
    valueInputOption="USER_ENTERED",
    insertDataOption="INSERT_ROWS",
    body={"values": row}
).execute()

print("✅ Signal sent to Google Sheet.")