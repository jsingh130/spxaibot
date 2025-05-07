import os
import json
import pandas as pd
import yfinance as yf
from datetime import datetime
from ta.trend import EMAIndicator
from ta.volatility import AverageTrueRange
from google.oauth2 import service_account
from googleapiclient.discovery import build

# === SETTINGS ===
SHEET_ID = "1hn8Bb9SFEmDTyoMJkCshlGUST2ME49oTALtL36b5SVE"
TICKER = "AAPL"

# === AUTHENTICATE GOOGLE SHEETS ===
creds_data = json.loads(os.getenv("GOOGLE_CREDENTIALS_JSON"))

credentials = service_account.Credentials.from_service_account_info(
    creds_data,
    scopes=["https://www.googleapis.com/auth/spreadsheets"]
)
sheet_service = build("sheets", "v4", credentials=credentials)

# === DOWNLOAD MARKET DATA ===
print(f"🟡 Downloading data for {TICKER}...")
df = yf.download(TICKER, interval="5m", period="5d")
print(f"✅ Downloaded {len(df)} rows")
print(df.head())

if df.empty:
    print("⚠️ No data returned from yfinance. Exiting.")
    exit()

# === CLEAN AND PREP DATA ===
close = pd.Series(df["Close"].values.flatten())
high = pd.Series(df["High"].values.flatten())
low = pd.Series(df["Low"].values.flatten())

df["EMA9"] = EMAIndicator(close, 9).ema_indicator()
df["EMA21"] = EMAIndicator(close, 21).ema_indicator()
df["ATR"] = AverageTrueRange(high, low, close).average_true_range()

# 🔧 TEMPORARY: Skip dropna to test
# df.dropna(inplace=True)

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

# === SEND TO GOOGLE SHEETS ===
sheet_service.spreadsheets().values().append(
    spreadsheetId=SHEET_ID,
    range="Live Signals!A1",
    valueInputOption="USER_ENTERED",
    insertDataOption="INSERT_ROWS",
    body={"values": row}
).execute()

print("✅ Signal sent to Google Sheet.")
