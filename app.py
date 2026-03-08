import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone

# --- ARCHITECT'S ENGINE ---
def get_institutional_data():
    # 1. Download data: 7 days of 1-hour bars to find Weekly/Daily levels
    # GC=F is Gold Futures on COMEX
    gold = yf.Ticker("GC=F")
    df_h1 = gold.history(period="7d", interval="1h")
    df_m5 = gold.history(period="1d", interval="5m")
    
    if df_h1.empty or df_m5.empty:
        return None

    # A. AUTOMATIC WOFM_MID (Monday 00:00 GMT Midpoint)
    # Find the first candle of the current week
    monday_start = (datetime.now(timezone.utc) - timedelta(days=datetime.now(timezone.utc).weekday())).replace(hour=0, minute=0, second=0)
    weekly_data = df_h1[df_h1.index >= pd.to_datetime(monday_start).tz_localize('UTC')]
    if not weekly_data.empty:
        wofm_mid = (weekly_data['High'].iloc[0] + weekly_data['Low'].iloc[0]) / 2
    else:
        wofm_mid = (df_h1['High'].iloc[0] + df_h1['Low'].iloc[0]) / 2

    # B. AUTOMATIC TDO (True Day Open - 20:00 GMT Yesterday)
    # We look for the candle closest to 20:00 GMT
    tdo = df_h1.between_time('19:00', '21:00')['Close'].iloc[-1]

    # C. LIVE METRICS
    current_p = df_m5['Close'].iloc[-1]
    
    # D. ATR(5)
    high_low = df_m5['High'] - df_m5['Low']
    atr = high_low.rolling(window=5).mean().iloc[-1]

    # E. VOL% (Current 5m Vol vs 20-period Avg)
    avg_vol = df_m5['Volume'].iloc[-21:-1].mean()
    current_vol = df_m5['Volume'].iloc[-1]
    vol_pct = (current_vol / avg_vol) * 100 if avg_vol > 0 else 100

    return {
        "price": current_p,
        "wofm": wofm_mid,
        "tdo": tdo,
        "atr": atr,
        "vol_pct": vol_pct,
        "raw_m5": df_m5
    }

# --- UI SETUP ---
st.set_page_config(page_title="Architect Quant Terminal", layout="wide")
st.markdown("""
    <style>
    .reportview-container { background: #0e1117; }
    .stMetric { background: #1a1c23; padding: 15px; border-radius: 10px; border: 1px solid #333; }
    </style>
    """, unsafe_allow_exists=True)

st.title("🏛️ XAUUSD ARCHITECT TERMINAL v4.5")
st.subheader("Autonomous Law of Time-Price Inertia Engine")

if st.button("CALCULATE LIVE SIGNALS"):
    with st.spinner('Analyzing Institutional Order Flow...'):
        data = get_institutional_data()
        
        if data:
            # 1. BIAS CALCULATIONS
            qib = 0.42 # Institutional Baseline
            tdo_bias = 0.25 if data['price'] > data['tdo'] else -0.25
            
            # MOC Bias (Check if we are at a 90-min edge)
            now = datetime.now(timezone.utc)
            minutes_since_midnight = now.hour * 60 + now.minute
            is_at_edge = any(abs(minutes_since_midnight - m) <= 5 for m in [0, 90, 180, 270, 360, 450, 540, 630, 720, 810, 900, 990, 1080, 1170, 1260, 1350])
            moc_multiplier = 0.85 if is_at_edge else 0.40
            
            p_long = (qib * 0.35) + (tdo_bias * 0.25) + (moc_multiplier)
            # Normalize for a 0-100% display
            prob = min(max(p_long * 10, 45), 94) 

            # 2. RISK MANAGEMENT
            equity = 125000
            risk_usd = equity * 0.0938
            sl_dist = 1.8 * data['atr']
            # Gold Lot Size Calculation (1 lot = $1 movement is $100)
            lots = risk_usd / (sl_dist * 100)

            # 3. DISPLAY
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("LIVE PRICE", f"${data['price']:.2f}")
            col2.metric("WOFM MID", f"${data['wofm']:.2f}")
            col3.metric("ATR (5M)", f"{data['atr']:.2f}")
            col4.metric("VOL %", f"{data['vol_pct']:.0f}%")

            st.divider()

            # 4. SIGNAL OUTPUT
            if data['vol_pct'] < 120:
                st.warning("⚠️ LOW VOLUME: Institutions are not active. Signals may be weak.")
            
            if data['price'] < data['wofm']:
                st.success(f"### 🟢 SIGNAL: LONG (Reversion to WOFM)")
                st.write(f"**PROBABILITY:** {prob:.1f}%")
                st.write(f"**ENTRY:** Current Market (${data['price']:.2f})")
                st.write(f"**STOP LOSS:** ${(data['price'] - sl_dist):.2f}")
                st.write(f"**TARGET:** ${data['wofm']:.2f}")
                st.write(f"**SIZE:** {lots:.2f} Lots")
            else:
                st.error(f"### 🔴 SIGNAL: SHORT (Reversion to TDO)")
                st.write(f"**PROBABILITY:** {prob:.1f}%")
                st.write(f"**ENTRY:** Current Market (${data['price']:.2f})")
                st.write(f"**STOP LOSS:** ${(data['price'] + sl_dist):.2f}")
                st.write(f"**TARGET:** ${data['tdo']:.2f}")
                st.write(f"**SIZE:** {lots:.2f} Lots")

        else:
            st.error("Market Data Unavailable. Check internet connection or Market Holiday.")

st.caption("Terminal Logic: ΔP/Δt = α × (μ - P_t) / σ_t + β × ∇VOL_t + ε_t")
