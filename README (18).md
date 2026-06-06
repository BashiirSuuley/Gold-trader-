# 🥇 XAUUSD Forex Analyzer

A professional **Gold vs USD (XAUUSD)** trading analysis tool built with **Streamlit**.
Provides real-time signals, **Stop Loss**, and **Take Profit** levels for 15m, 1h, and 4h timeframes.

---

## 📸 Features

- 📡 **Live XAUUSD data** via Yahoo Finance (GC=F)
- 🎯 **Auto-calculated Stop Loss & Take Profit** (3 TP levels)
- 📊 **Multi-indicator analysis**: RSI, MACD, Bollinger Bands, EMA 20/50/200, Stochastic, ATR
- 📈 **Interactive Plotly chart** with SL/TP lines, support & resistance
- ⚙️ **Adjustable risk settings**: ATR multiplier, RR ratio, RSI levels
- 🔄 **Auto-refresh** every 5 minutes (cached)
- 🖤 Dark theme optimized for traders

---

## 🚀 Run Locally

### 1. Clone the repo
```bash
git clone https://github.com/YOUR_USERNAME/xauusd-analyzer.git
cd xauusd-analyzer
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the app
```bash
streamlit run app.py
```

Open your browser at `http://localhost:8501`

---

## ☁️ Deploy on Streamlit Cloud (Free)

1. Push this repo to GitHub
2. Go to [streamlit.io/cloud](https://streamlit.io/cloud)
3. Click **"New app"** → Connect your GitHub repo
4. Set **Main file**: `app.py`
5. Click **Deploy** ✅

---

## 📊 Indicators Used

| Indicator | Purpose |
|-----------|---------|
| RSI (14) | Overbought/Oversold detection |
| MACD (12,26,9) | Trend momentum & crossovers |
| Bollinger Bands (20,2) | Volatility & price extremes |
| EMA 20 / 50 / 200 | Trend direction & crossovers |
| Stochastic (14,3) | Momentum oscillator |
| ATR (14) | Volatility-based SL/TP sizing |
| Support/Resistance | Pivot-based key levels |

---

## ⚙️ Settings

| Setting | Default | Description |
|---------|---------|-------------|
| Timeframe | 1h | 15m, 1h, or 4h |
| ATR Multiplier | 1.5 | Stop Loss width (1.5 = moderate) |
| RR Ratio | 2.0 | Risk:Reward for TP1 |
| RSI Overbought | 70 | Sell zone |
| RSI Oversold | 30 | Buy zone |

---

## ⚠️ Disclaimer

This tool is for **educational purposes only**. It does not constitute financial advice.
Always use proper risk management. Past signals do not guarantee future results.

---

## 📁 File Structure

```
xauusd-analyzer/
├── app.py              # Main Streamlit application
├── requirements.txt    # Python dependencies
└── README.md           # This file
```

---

Built with ❤️ using Streamlit · Plotly · yfinance
