import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import yfinance as yf
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings("ignore")

# ─── Page Config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="XAUUSD Analyzer",
    page_icon="🥇",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── Custom CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Rajdhani:wght@400;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Rajdhani', sans-serif;
    }
    .main {
        background-color: #0a0e1a;
    }
    .stApp {
        background: linear-gradient(135deg, #0a0e1a 0%, #0f1628 100%);
    }
    h1, h2, h3 {
        font-family: 'Rajdhani', sans-serif;
        color: #f0c040 !important;
        letter-spacing: 2px;
    }
    .metric-card {
        background: linear-gradient(135deg, #111827, #1e2535);
        border: 1px solid #f0c04044;
        border-radius: 8px;
        padding: 16px;
        text-align: center;
        margin: 6px 0;
    }
    .metric-card .value {
        font-family: 'Share Tech Mono', monospace;
        font-size: 1.6rem;
        font-weight: bold;
    }
    .metric-card .label {
        font-size: 0.85rem;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .buy-signal {
        background: linear-gradient(135deg, #052e16, #14532d);
        border: 1px solid #22c55e88;
        border-radius: 8px;
        padding: 16px;
        margin: 8px 0;
    }
    .sell-signal {
        background: linear-gradient(135deg, #2d0a0a, #7f1d1d);
        border: 1px solid #ef444488;
        border-radius: 8px;
        padding: 16px;
        margin: 8px 0;
    }
    .neutral-signal {
        background: linear-gradient(135deg, #1c1a05, #3d3600);
        border: 1px solid #eab30888;
        border-radius: 8px;
        padding: 16px;
        margin: 8px 0;
    }
    .signal-title {
        font-size: 1.3rem;
        font-weight: 700;
        letter-spacing: 2px;
    }
    .stSelectbox label, .stSlider label, .stNumberInput label {
        color: #f0c040 !important;
        font-weight: 600;
        letter-spacing: 1px;
    }
    .sidebar .sidebar-content {
        background: #0f1628;
    }
    div[data-testid="metric-container"] {
        background: #111827;
        border: 1px solid #f0c04033;
        border-radius: 6px;
        padding: 10px;
    }
    div[data-testid="metric-container"] label {
        color: #94a3b8 !important;
    }
    div[data-testid="metric-container"] div[data-testid="stMetricValue"] {
        color: #f0c040 !important;
        font-family: 'Share Tech Mono', monospace;
    }
    .footer-bar {
        text-align: center;
        color: #475569;
        font-size: 0.75rem;
        padding-top: 20px;
        border-top: 1px solid #1e2535;
        margin-top: 30px;
    }
</style>
""", unsafe_allow_html=True)


# ─── Indicator Functions ──────────────────────────────────────────────────────

def compute_rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def compute_macd(series, fast=12, slow=26, signal=9):
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram

def compute_bollinger(series, period=20, std=2):
    sma = series.rolling(period).mean()
    std_dev = series.rolling(period).std()
    upper = sma + std * std_dev
    lower = sma - std * std_dev
    return upper, sma, lower

def compute_atr(high, low, close, period=14):
    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def compute_ema(series, period):
    return series.ewm(span=period, adjust=False).mean()

def compute_stochastic(high, low, close, k_period=14, d_period=3):
    low_min = low.rolling(k_period).min()
    high_max = high.rolling(k_period).max()
    k = 100 * (close - low_min) / (high_max - low_min)
    d = k.rolling(d_period).mean()
    return k, d

def compute_support_resistance(df, lookback=50):
    recent = df.tail(lookback)
    pivots_high = []
    pivots_low = []
    closes = recent['Close'].values
    highs = recent['High'].values
    lows = recent['Low'].values

    for i in range(2, len(closes) - 2):
        if highs[i] > highs[i-1] and highs[i] > highs[i-2] and highs[i] > highs[i+1] and highs[i] > highs[i+2]:
            pivots_high.append(highs[i])
        if lows[i] < lows[i-1] and lows[i] < lows[i-2] and lows[i] < lows[i+1] and lows[i] < lows[i+2]:
            pivots_low.append(lows[i])

    resistance = np.mean(sorted(pivots_high)[-3:]) if len(pivots_high) >= 3 else recent['High'].max()
    support = np.mean(sorted(pivots_low)[:3]) if len(pivots_low) >= 3 else recent['Low'].min()
    return round(support, 2), round(resistance, 2)


def generate_signal(df, rsi_ob=70, rsi_os=30):
    latest = df.iloc[-1]
    prev = df.iloc[-2]

    score = 0
    reasons = []

    # RSI
    rsi = latest['RSI']
    if rsi < rsi_os:
        score += 2
        reasons.append(f"🟢 RSI oversold ({rsi:.1f}) → BUY pressure")
    elif rsi > rsi_ob:
        score -= 2
        reasons.append(f"🔴 RSI overbought ({rsi:.1f}) → SELL pressure")
    else:
        reasons.append(f"⚪ RSI neutral ({rsi:.1f})")

    # MACD
    if latest['MACD'] > latest['MACD_Signal'] and prev['MACD'] <= prev['MACD_Signal']:
        score += 3
        reasons.append("🟢 MACD bullish crossover → BUY")
    elif latest['MACD'] < latest['MACD_Signal'] and prev['MACD'] >= prev['MACD_Signal']:
        score -= 3
        reasons.append("🔴 MACD bearish crossover → SELL")
    elif latest['MACD'] > latest['MACD_Signal']:
        score += 1
        reasons.append("🟢 MACD above signal → Bullish")
    else:
        score -= 1
        reasons.append("🔴 MACD below signal → Bearish")

    # EMA trend
    if latest['EMA_20'] > latest['EMA_50'] and latest['Close'] > latest['EMA_20']:
        score += 2
        reasons.append("🟢 Price above EMA20 > EMA50 → Uptrend")
    elif latest['EMA_20'] < latest['EMA_50'] and latest['Close'] < latest['EMA_20']:
        score -= 2
        reasons.append("🔴 Price below EMA20 < EMA50 → Downtrend")

    # Bollinger Bands
    if latest['Close'] < latest['BB_Lower']:
        score += 1
        reasons.append("🟢 Price below lower BB → Potential reversal up")
    elif latest['Close'] > latest['BB_Upper']:
        score -= 1
        reasons.append("🔴 Price above upper BB → Potential reversal down")

    # Stochastic
    stoch_k = latest['Stoch_K']
    stoch_d = latest['Stoch_D']
    if stoch_k < 20 and stoch_k > stoch_d:
        score += 1
        reasons.append(f"🟢 Stochastic oversold crossover ({stoch_k:.1f}) → BUY")
    elif stoch_k > 80 and stoch_k < stoch_d:
        score -= 1
        reasons.append(f"🔴 Stochastic overbought crossover ({stoch_k:.1f}) → SELL")

    # Determine signal
    if score >= 3:
        signal = "BUY 🟢"
        signal_class = "buy-signal"
        signal_color = "#22c55e"
    elif score <= -3:
        signal = "SELL 🔴"
        signal_class = "sell-signal"
        signal_color = "#ef4444"
    else:
        signal = "NEUTRAL ⚪"
        signal_class = "neutral-signal"
        signal_color = "#eab308"

    return signal, signal_class, signal_color, score, reasons


def calculate_sl_tp(df, signal, atr_mult_sl=1.5, rr_ratio=2.0):
    latest = df.iloc[-1]
    entry = latest['Close']
    atr = latest['ATR']
    support, resistance = compute_support_resistance(df)

    sl_atr = atr * atr_mult_sl

    if "BUY" in signal:
        sl = round(entry - sl_atr, 2)
        sl_support = round(support - atr * 0.3, 2)
        sl = min(sl, sl_support)  # Use tighter of the two
        tp1 = round(entry + sl_atr * rr_ratio, 2)
        tp2 = round(entry + sl_atr * rr_ratio * 1.6, 2)
        tp3 = round(resistance, 2)
    elif "SELL" in signal:
        sl = round(entry + sl_atr, 2)
        sl_resistance = round(resistance + atr * 0.3, 2)
        sl = max(sl, sl_resistance)  # Use tighter of the two
        tp1 = round(entry - sl_atr * rr_ratio, 2)
        tp2 = round(entry - sl_atr * rr_ratio * 1.6, 2)
        tp3 = round(support, 2)
    else:
        sl = round(entry - sl_atr, 2)
        tp1 = round(entry + sl_atr * rr_ratio, 2)
        tp2 = round(entry + sl_atr * rr_ratio * 1.6, 2)
        tp3 = round(resistance, 2)

    sl_pips = round(abs(entry - sl), 2)
    tp1_pips = round(abs(entry - tp1), 2)
    rr = round(tp1_pips / sl_pips, 2) if sl_pips > 0 else 0

    return {
        "entry": round(entry, 2),
        "sl": sl,
        "tp1": tp1,
        "tp2": tp2,
        "tp3": tp3,
        "sl_pips": sl_pips,
        "tp1_pips": tp1_pips,
        "rr": rr,
        "support": support,
        "resistance": resistance,
        "atr": round(atr, 2)
    }


# ─── Data Fetching ────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
def fetch_data(timeframe):
    tf_map = {
        "15m": ("15m", 7),
        "1h":  ("1h",  30),
        "4h":  ("4h",  90),
    }
    interval, days = tf_map[timeframe]
    end = datetime.now()
    start = end - timedelta(days=days)
    df = yf.download("GC=F", start=start, end=end, interval=interval, progress=False)
    if df.empty:
        df = yf.download("GLD", start=start, end=end, interval=interval, progress=False)
    df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
    df.dropna(inplace=True)
    return df


def enrich(df):
    df['RSI'] = compute_rsi(df['Close'])
    df['MACD'], df['MACD_Signal'], df['MACD_Hist'] = compute_macd(df['Close'])
    df['BB_Upper'], df['BB_Mid'], df['BB_Lower'] = compute_bollinger(df['Close'])
    df['ATR'] = compute_atr(df['High'], df['Low'], df['Close'])
    df['EMA_20'] = compute_ema(df['Close'], 20)
    df['EMA_50'] = compute_ema(df['Close'], 50)
    df['EMA_200'] = compute_ema(df['Close'], 200)
    df['Stoch_K'], df['Stoch_D'] = compute_stochastic(df['High'], df['Low'], df['Close'])
    return df.dropna()


# ─── Chart ────────────────────────────────────────────────────────────────────
def build_chart(df, levels, signal_str, timeframe):
    entry = levels['entry']
    sl = levels['sl']
    tp1 = levels['tp1']
    tp2 = levels['tp2']

    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.04,
        row_heights=[0.6, 0.2, 0.2],
        subplot_titles=(f"XAUUSD — {timeframe.upper()} Chart", "RSI (14)", "MACD")
    )

    # Candlestick
    fig.add_trace(go.Candlestick(
        x=df.index, open=df['Open'], high=df['High'],
        low=df['Low'], close=df['Close'],
        name="XAUUSD",
        increasing_line_color='#22c55e',
        decreasing_line_color='#ef4444',
        increasing_fillcolor='#22c55e33',
        decreasing_fillcolor='#ef444433',
    ), row=1, col=1)

    # EMAs
    for period, color, dash in [(20, '#f0c040', 'solid'), (50, '#60a5fa', 'dash'), (200, '#c084fc', 'dot')]:
        col = f'EMA_{period}'
        if col in df.columns:
            fig.add_trace(go.Scatter(
                x=df.index, y=df[col], name=f"EMA {period}",
                line=dict(color=color, width=1.2, dash=dash), opacity=0.8
            ), row=1, col=1)

    # Bollinger Bands
    fig.add_trace(go.Scatter(x=df.index, y=df['BB_Upper'], name='BB Upper',
        line=dict(color='#94a3b8', width=0.8, dash='dot'), opacity=0.5), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['BB_Lower'], name='BB Lower',
        line=dict(color='#94a3b8', width=0.8, dash='dot'),
        fill='tonexty', fillcolor='rgba(148,163,184,0.04)', opacity=0.5), row=1, col=1)

    # SL/TP Lines
    last_x = df.index[-20:]
    is_buy = "BUY" in signal_str

    def hline(y, color, label, dash='dash'):
        fig.add_shape(type='line', x0=df.index[-40], x1=df.index[-1],
                      y0=y, y1=y, line=dict(color=color, width=1.5, dash=dash), row=1, col=1)
        fig.add_annotation(x=df.index[-1], y=y, text=f" {label}: {y:.2f}",
                           showarrow=False, font=dict(color=color, size=11), xanchor='left', row=1, col=1)

    hline(entry, '#f0c040', 'ENTRY', 'solid')
    hline(sl, '#ef4444', 'SL')
    hline(tp1, '#22c55e', 'TP1')
    hline(tp2, '#86efac', 'TP2')

    # Support / Resistance
    hline(levels['support'], '#60a5fa', 'SUP', 'dot')
    hline(levels['resistance'], '#f97316', 'RES', 'dot')

    # RSI
    fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], name='RSI',
        line=dict(color='#f0c040', width=1.5)), row=2, col=1)
    for level, color in [(70, '#ef4444'), (30, '#22c55e'), (50, '#475569')]:
        fig.add_hline(y=level, line=dict(color=color, width=0.8, dash='dot'), row=2, col=1)

    # MACD
    colors = ['#22c55e' if v >= 0 else '#ef4444' for v in df['MACD_Hist']]
    fig.add_trace(go.Bar(x=df.index, y=df['MACD_Hist'], name='MACD Hist',
        marker_color=colors, opacity=0.7), row=3, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['MACD'], name='MACD',
        line=dict(color='#60a5fa', width=1.3)), row=3, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['MACD_Signal'], name='Signal',
        line=dict(color='#f97316', width=1.3)), row=3, col=1)

    fig.update_layout(
        paper_bgcolor='#0a0e1a',
        plot_bgcolor='#0f1628',
        font=dict(color='#94a3b8', family='Rajdhani'),
        legend=dict(bgcolor='#111827', bordercolor='#1e2535', borderwidth=1, font=dict(size=10)),
        xaxis_rangeslider_visible=False,
        height=720,
        margin=dict(l=10, r=80, t=40, b=10),
    )
    for i in range(1, 4):
        fig.update_xaxes(gridcolor='#1e2535', showgrid=True, row=i, col=1)
        fig.update_yaxes(gridcolor='#1e2535', showgrid=True, row=i, col=1)

    return fig


# ─── Main App ─────────────────────────────────────────────────────────────────
def main():

    # Header
    st.markdown("""
    <div style='text-align:center; padding: 16px 0 8px 0;'>
        <span style='font-size:2.6rem; font-family:Rajdhani; font-weight:700;
                     color:#f0c040; letter-spacing:4px; text-shadow: 0 0 20px #f0c04044;'>
            🥇 XAUUSD ANALYZER
        </span><br/>
        <span style='color:#64748b; font-size:0.9rem; letter-spacing:3px;'>
            GOLD / USD · AI-ASSISTED TRADE SIGNALS · SL & TP CALCULATOR
        </span>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")

    # ─── Sidebar ──────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("### ⚙️ SETTINGS")

        timeframe = st.selectbox(
            "📊 Timeframe",
            options=["15m", "1h", "4h"],
            index=1,
            format_func=lambda x: {"15m": "15 Minutes", "1h": "1 Hour", "4h": "4 Hours"}[x]
        )

        st.markdown("---")
        st.markdown("### 🎯 RISK SETTINGS")

        atr_sl_mult = st.slider(
            "ATR Multiplier (Stop Loss)", 1.0, 3.0, 1.5, 0.1,
            help="Stop Loss = ATR × multiplier. Higher = wider SL."
        )

        rr_ratio = st.slider(
            "Risk:Reward Ratio (TP1)", 1.0, 5.0, 2.0, 0.1,
            help="TP1 = SL distance × RR ratio."
        )

        rsi_ob = st.slider("RSI Overbought Level", 60, 80, 70, 1)
        rsi_os = st.slider("RSI Oversold Level", 20, 40, 30, 1)

        st.markdown("---")
        if st.button("🔄 Refresh Data", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

        st.markdown("""
        <div style='font-size:0.75rem; color:#475569; margin-top:20px;'>
        ⚠️ <b>Disclaimer</b>: This tool is for educational purposes only. Always use proper risk management. Past signals do not guarantee future results.
        </div>
        """, unsafe_allow_html=True)

    # ─── Load Data ────────────────────────────────────────────────────────────
    with st.spinner("📡 Fetching live XAUUSD data..."):
        try:
            df_raw = fetch_data(timeframe)
            df = enrich(df_raw.copy())
        except Exception as e:
            st.error(f"❌ Data fetch failed: {e}")
            st.info("💡 Check your internet connection. yfinance is used to fetch XAUUSD (GC=F) data.")
            return

    if len(df) < 50:
        st.warning("⚠️ Not enough candles loaded. Try a larger timeframe.")
        return

    # ─── Generate Signal & SL/TP ─────────────────────────────────────────────
    signal, signal_class, signal_color, score, reasons = generate_signal(df, rsi_ob, rsi_os)
    levels = calculate_sl_tp(df, signal, atr_sl_mult, rr_ratio)

    # ─── Top Row: Price + Signal ──────────────────────────────────────────────
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("💰 Current Price", f"${levels['entry']:,.2f}")
    with col2:
        st.metric("📈 ATR (14)", f"${levels['atr']:.2f}")
    with col3:
        st.metric("🛡️ Support", f"${levels['support']:,.2f}")
    with col4:
        st.metric("🚧 Resistance", f"${levels['resistance']:,.2f}")
    with col5:
        latest = df.iloc[-1]
        st.metric("📊 RSI", f"{latest['RSI']:.1f}")

    st.markdown("<br/>", unsafe_allow_html=True)

    # ─── Signal Banner ────────────────────────────────────────────────────────
    st.markdown(f"""
    <div class="{signal_class}">
        <div class="signal-title" style="color:{signal_color};">
            SIGNAL: {signal}
        </div>
        <div style="color:#94a3b8; font-size:0.85rem; margin-top:4px;">
            Composite Score: <b style="color:{signal_color};">{score:+d}</b> &nbsp;|&nbsp;
            Timeframe: <b>{timeframe.upper()}</b> &nbsp;|&nbsp;
            Updated: <b>{datetime.now().strftime('%H:%M:%S')}</b>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br/>", unsafe_allow_html=True)

    # ─── SL/TP Panel ─────────────────────────────────────────────────────────
    col_a, col_b = st.columns([1, 2])

    with col_a:
        st.markdown("#### 🎯 TRADE LEVELS")

        is_buy = "BUY" in signal

        st.markdown(f"""
        <div class="metric-card">
            <div class="label">ENTRY PRICE</div>
            <div class="value" style="color:#f0c040;">${levels['entry']:,.2f}</div>
        </div>
        <div class="metric-card">
            <div class="label">🛑 STOP LOSS</div>
            <div class="value" style="color:#ef4444;">${levels['sl']:,.2f}</div>
            <div style="font-size:0.8rem; color:#94a3b8;">Risk: ${levels['sl_pips']:.2f} / pip</div>
        </div>
        <div class="metric-card">
            <div class="label">✅ TAKE PROFIT 1</div>
            <div class="value" style="color:#22c55e;">${levels['tp1']:,.2f}</div>
            <div style="font-size:0.8rem; color:#94a3b8;">Reward: ${levels['tp1_pips']:.2f} | RR: {levels['rr']}:1</div>
        </div>
        <div class="metric-card">
            <div class="label">✅ TAKE PROFIT 2</div>
            <div class="value" style="color:#86efac;">${levels['tp2']:,.2f}</div>
        </div>
        <div class="metric-card">
            <div class="label">🏆 TAKE PROFIT 3 (Key Level)</div>
            <div class="value" style="color:#4ade80;">${levels['tp3']:,.2f}</div>
        </div>
        """, unsafe_allow_html=True)

    with col_b:
        st.markdown("#### 📡 INDICATOR ANALYSIS")
        for reason in reasons:
            st.markdown(f"- {reason}")

        st.markdown("<br/>", unsafe_allow_html=True)
        st.markdown("#### 📊 LATEST INDICATOR VALUES")
        latest = df.iloc[-1]
        ind_col1, ind_col2, ind_col3 = st.columns(3)
        with ind_col1:
            st.metric("RSI", f"{latest['RSI']:.1f}")
            st.metric("EMA 20", f"{latest['EMA_20']:.2f}")
        with ind_col2:
            st.metric("MACD", f"{latest['MACD']:.3f}")
            st.metric("EMA 50", f"{latest['EMA_50']:.2f}")
        with ind_col3:
            st.metric("Stoch %K", f"{latest['Stoch_K']:.1f}")
            st.metric("EMA 200", f"{latest['EMA_200']:.2f}")

    st.markdown("<br/>", unsafe_allow_html=True)

    # ─── Chart ────────────────────────────────────────────────────────────────
    st.markdown("#### 📈 PRICE CHART WITH SIGNALS")
    fig = build_chart(df, levels, signal, timeframe)
    st.plotly_chart(fig, use_container_width=True)

    # ─── Recent Candles Table ─────────────────────────────────────────────────
    with st.expander("📋 Recent Candle Data"):
        display_df = df[['Open','High','Low','Close','Volume','RSI','MACD','ATR','EMA_20','EMA_50']].tail(20).copy()
        display_df = display_df.round(3)
        st.dataframe(display_df.style.background_gradient(cmap='RdYlGn', subset=['RSI']), use_container_width=True)

    # ─── Footer ───────────────────────────────────────────────────────────────
    st.markdown("""
    <div class="footer-bar">
        Built with Streamlit · Data via Yahoo Finance (yfinance) · XAUUSD (GC=F) ·
        Indicators: RSI · MACD · Bollinger Bands · EMA · Stochastic · ATR<br/>
        ⚠️ Not financial advice. Trade at your own risk.
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
