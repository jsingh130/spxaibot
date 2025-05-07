# SPX AI Bot Deployment (Railway + Google Sheets)

This bot:
- Downloads 5-minute candle data from Yahoo Finance
- Calculates EMA9, EMA21, and ATR
- Determines direction (UP/DOWN), builds signal
- Sends the signal to your Google Sheet

### ✅ How to Deploy on Railway

1. Fork this repo
2. Upload your `credentials.json` from Google Cloud
3. Set the environment variable:
   - `GOOGLE_CREDENTIALS_JSON` → paste contents of your credentials.json as a string
4. Deploy using Railway (Worker)