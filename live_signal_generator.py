
import yfinance as yf
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# Setup Google Sheets API
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("service_account.json", scope)
client = gspread.authorize(creds)

# Spreadsheet setup
spreadsheet_id = "1hn8Bb9SFEmDTyoMJkCshlGUST2ME49oTALtL36b5SVE"
sheet = client.open_by_key(spreadsheet_id).sheet1

# Tickers to process
tickers = ["AAPL", "SPY", "QQQ", "SPX"]

def fetch_data(ticker):
    df = yf.download(ticker, period="5d", interval="5m")
    df = df[["Open", "High", "Low", "Close", "Adj Close"]]
    return df

def calculate_signal(df):
    df["EMA9"] = df["Close"].ewm(span=9, adjust=False).mean()
    df["EMA21"] = df["Close"].ewm(span=21, adjust=False).mean()
    latest = df.iloc[-1]

    direction = "UP" if latest["Close"] > latest["EMA9"] > latest["EMA21"] else "DOWN"
    signal = {
        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "Direction": direction,
        "Confidence": 75,
        "Entry": round(latest["Close"], 2),
        "Stop": round(latest["High"], 2) if direction == "DOWN" else round(latest["Low"], 2),
        "Target": round(latest["Close"] - 1.5, 2) if direction == "DOWN" else round(latest["Close"] + 1.5, 2),
        "Option Type": "PUT" if direction == "DOWN" else "CALL",
        "Strike": round(latest["Close"]),
        "Notes": "0DTE Signal"
    }
    return signal

def send_to_sheet(ticker, signal):
    row = [
        signal["Timestamp"],
        ticker,
        signal["Direction"],
        signal["Confidence"],
        signal["Entry"],
        signal["Stop"],
        signal["Target"],
        signal["Option Type"],
        signal["Strike"],
        signal["Notes"]
    ]
    sheet.append_row(row, value_input_option="USER_ENTERED")

def main():
    for ticker in tickers:
        try:
            df = fetch_data(ticker)
            if not df.empty:
                signal = calculate_signal(df)
                send_to_sheet(ticker, signal)
                print(f"✅ {ticker} signal sent.")
            else:
                print(f"⚠️ No data for {ticker}.")
        except Exception as e:
            print(f"❌ Error processing {ticker}: {e}")

if __name__ == "__main__":
    main()
