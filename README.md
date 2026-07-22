# BEI Trading Bot V4.2 — Daily + Swing Trading

Tambahan dari V4.1:
- Mode Daily Trading dan Swing Trading
- Swing Score terpisah
- Trend EMA20/50/200
- RSI, MACD, volume, breakout 20/50 hari
- Momentum 20/60 hari
- Entry, TP1, TP2, Stop Loss khusus swing berbasis ATR harian
- Holding Plan estimasi
- Technical + Fundamental Combined Score
- Laporan Excel

Install:
py -m pip install -r requirements.txt

Run:
py -m streamlit run app.py

Swing mode menggunakan data harian (1d), sehingga lebih cocok untuk horizon beberapa hari hingga beberapa minggu.
Score adalah model rule-based dan bukan jaminan keuntungan.
