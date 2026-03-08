import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timezone

# --- THE ARCHITECT ENGINE ---
def get_data():
    gold = yf.Ticker("GC=F")
    df = gold.history(period="5d", interval="1h")
    m5 = gold.history(period="1d", interval="5m")
    if df.empty or m5.empty: return None
    
    # Auto-Calculations
    wofm = (df['High'].iloc[0] + df['Low'].iloc[0]) / 2
    tdo = df['Close'].iloc[-1]
    current_p = m5['Close'].iloc[-1]
    atr = (m5['High'] - m5['Low']).rolling(5).mean().iloc[-1]
    return {"p": current_p, "wofm": wofm, "tdo": tdo, "atr": atr}

st.set_page_config(page_title="XAUUSD Architect", layout="wide")
st.title("🏛️ XAUUSD ARCHITECT TERMINAL")

if st.button("CALCULATE LIVE SIGNAL"):
    data = get_data()
    if data:
        # The Math
        risk_per_trade = 125000 * 0.0938
        sl_dist = 1.8 * data['atr']
        lots = risk_per_trade / (sl_dist * 100)
        
        # Display
        st.metric("LIVE PRICE", f"${data['p']:.2f}")
        
        if data['p'] < data['wofm']:
            st.success(f"### 🟢 SIGNAL: LONG (BUY)")
            st.write(f"**ENTRY:** ${data['p']:.2f} | **SL:** ${(data['p']-sl_dist):.2f} | **TP:** ${data['wofm']:.2f}")
        else:
            st.error(f"### 🔴 SIGNAL: SHORT (SELL)")
            st.write(f"**ENTRY:** ${data['p']:.2f} | **SL:** ${(data['p']+sl_dist):.2f} | **TP:** ${data['tdo']:.2f}")
        
        st.write(f"**POSITION SIZE:** {lots:.2f} Lots")
    else:
        st.error("Market Data Offline. Wait for market open.")
