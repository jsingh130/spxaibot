import os, json
import pandas as pd
import yfinance as yf
from datetime import datetime
from ta.trend import EMAIndicator
from ta.volatility import AverageTrueRange
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Load credentials and sheet ID from env
SHEET_ID = os.getenv("SHEET_ID")
creds_data = json.loads(os.getenv("GOOGLE_CREDENTIALS_JSON"))

# Authenticate Google Sheets API
credentials = service_account.Credentials.from_service_account_info(
    creds_data,
    scopes=["https://www.googleapis.com/auth/spreadsheets"]
)
sheet_service = build("sheets", "v4", credentials=credentials)

# Download SPX 5-min data
df = yf.download("^GSPC", interval="5m", period="1d")
close = df["Close"].values.flatten()
df["EMA9"] = EMAIndicator(pd.Series(df["Close"].values.flatten()), 9).ema_indicator()
df["EMA21"] = EMAIndicator(pd.Series(df["Close"].values.flatten()), 21).ema_indicator()
df["ATR"] = AverageTrueRange(df["High"], df["Low"], df["Close"]).average_true_range()
df.dropna(inplace=True)

# Signal logic
latest = df.iloc[-1]
direction = "UP" if latest["Close"] > latest["EMA9"] > latest["EMA21"] else "DOWN"
confidence = 85 if direction == "UP" else 75
entry = round(latest["Close"], 2)
sl = round(entry - latest["ATR"], 2) if direction == "UP" else round(entry + latest["ATR"], 2)
tp = round(entry + 2 * latest["ATR"], 2) if direction == "UP" else round(entry - 2 * latest["ATR"], 2)
strike = int(round(entry / 5) * 5)
option_type = "CALL" if direction == "UP" else "PUT"

# Send to Sheet
row = [[datetime.now().strftime("%Y-%m-%d %H:%M"), "^GSPC", direction, confidence, entry, sl, tp, option_type, strike, "0DTE Signal"]]
sheet_service.spreadsheets().values().append(
    spreadsheetId="1hn8Bb9SFEmDTyoMJkCshlGUST2ME49oTALtL36b5SVE",
    range="Live Signals!A1",
    valueInputOption="USER_ENTERED",
    insertDataOption="INSERT_ROWS",
    body={"values": row}
).execute()

print("✅ Signal sent to Google Sheet.")
