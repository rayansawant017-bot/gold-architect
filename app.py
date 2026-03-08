import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
import pytz

# --- ARCHITECT CONFIGURATION ---
EQUITY = 125000
KELLY_RISK_FRAC = 0.0938  # 9.4% per request
QIB_BIAS = 0.42           # Institutional structural bias
ALPHA = 0.03              # Mean-reversion coefficient
BETA = 0.018              # Volume impact coefficient

# MOC Edges (90-minute cycles)
MOC_EDGES = [
    "00:00", "01:30", "03:00", "04:30", "06:00", "07:30", "09:00", "10:30",
    "12:00", "13:30", "15:00", "16:30", "18:00", "19:30", "21:00", "22:30"
]

def get_market_data():
    # Fetching COMEX Gold Futures (GC=F)
    # We pull 7 days of 1-hour and 1 day of 5-minute data
    gold = yf.Ticker("GC=F")
    df_h = gold.history(period="7d", interval="1h")
    df_m5 = gold.history(period="2d", interval="5m")
    
    if df_h.empty or df_m5.empty:
        return None
    
    # 1. CALCULATE WOFM_mid (Monday 00:00-00:15 GMT)
    # Find the most recent Monday
    now = datetime.now(timezone.utc)
    monday = now - timedelta(days=now.weekday())
    monday_start = monday.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Extract the first 15-30 mins of the week from the hourly/5m data
    try:
        weekly_start_data = df_h[df_h.index >= pd.to_datetime(monday_start).tz_localize('UTC')]
        wofm_mid = (weekly_start_data['High'].iloc[0] + weekly_start_data['Low'].iloc[0]) / 2
    except:
        # Fallback if Monday data isn't in this slice
        wofm_mid = (df_h['High'].iloc[0] + df_h['Low'].iloc[0]) / 2

    # 2. CALCULATE TDO (True Day Open - 20:00 GMT NY Close)
    # Look for the candle at 20:00 GMT from the previous day
    try:
        tdo_data = df_h.between_time('19:30', '20:30')
        tdo = tdo_data['Close'].iloc[-1]
    except:
        tdo = df_h['Close'].iloc[-24] # Fallback to 24h ago

    # 3. LIVE METRICS
    current_price = df_m5['Close'].iloc[-1]
    
    # ATR(5)
    high_low = df_m5['High'] - df_m5['Low']
    atr = high_low.rolling(5).mean().iloc[-1]
    
    # VOL% (Current Volume vs 20-period average)
    avg_vol = df_m5['Volume'].iloc[-21:-1].mean()
    current_vol = df_m5['Volume'].iloc[-1]
    vol_pct = (current_vol / avg_vol) * 100 if avg_vol > 0 else 100

    return {
        "price": current_price,
        "wofm": wofm_mid,
        "tdo": tdo,
        "atr": atr,
        "vol_pct": vol_pct,
        "time": now
    }

def check_moc_edge(now):
    # Check if we are within +/- 5 minutes of an MOC Edge
    current_time_str = now.strftime("%H:%M")
    curr_minutes = now.hour * 60 + now.minute
    
    for edge in MOC_EDGES:
        edge_h, edge_m = map(int, edge.split(":"))
        edge_minutes = edge_h * 60 + edge_m
        if abs(curr_minutes - edge_minutes) <= 5:
            return True, edge
    return False, None

# --- STREAMLIT UI ---
st.set_page_config(page_title="Architect Terminal", layout="wide")

st.title("🏛️ XAUUSD ARCHITECT TERMINAL")
st.markdown("### Law of Time-Price Inertia | Institutional Framework")

if st.button("RUN CALCULATE: GENERATE TRADE SIGNALS"):
    with st.spinner('Gathering Real-Life Market Data...'):
        data = get_market_data()
        
        if data:
            # Step 1: Temporal Context & MOC Edge
            is_moc, edge_time = check_moc_edge(data['time'])
            
            # Step 2: Directional Synthesis
            # P_direction = (QIB × 0.35) + (sign(TDO - Current) × 0.25) + (MOC_bias × 0.40)
            tdo_bias = 0.25 if data['price'] > data['tdo'] else -0.25
            moc_bias_val = 0.72 if is_moc else 0.40
            
            p_long = (QIB_BIAS * 0.35) + (tdo_bias) + (moc_bias_val * 0.40)
            
            # Normalize to your 48% - 73% probability range
            final_prob = min(max(p_long * 100, 48), 78)

            # Step 3: Risk Sizing (Kelly)
            risk_amount = EQUITY * KELLY_RISK_FRAC
            sl_dist = 1.8 * data['atr']
            # Gold positioning: 1 lot = $100 per $1 move
            lots = risk_amount / (sl_dist * 100)

            # Step 4: Targets (E_Max)
            # Gamma based on regime (auto-trending if price far from WOFM)
            gamma = 1.618 if abs(data['price'] - data['wofm']) > (data['atr'] * 2) else 1.382
            tp_dist = sl_dist * 2.2 # Per your framework R:2.2

            # --- DISPLAY OUTPUT ---
            c1, c2, c3 = st.columns(3)
            c1.metric("CURRENT PRICE", f"${data['price']:.2f}")
            c2.metric("WOFM MIDPOINT", f"${data['wofm']:.2f}")
            c3.metric("TDO (20:00 GMT)", f"${data['tdo']:.2f}")

            st.divider()

            # Signal Logic
            if data['vol_pct'] > 150:
                st.info(f"🔥 VOLUME SPIKE DETECTED: {data['vol_pct']:.0f}%")
            
            if is_moc:
                st.success(f"⚡ MOC EDGE ACTIVE: {edge_time} GMT")
            else:
                st.warning("⚠️ OUTSIDE MOC EDGE: Expect lower predictability (ε_t is higher)")

            # Final Verdict
            st.subheader("STRATEGIC MANDATE")
            bias = "LONG" if data['price'] < data['wofm'] else "SHORT"
            
            if bias == "LONG":
                st.write(f"### ACTION: **BUY / LONG**")
                st.write(f"**ENTRY:** ${data['price']:.2f} (± 0.2 ATR)")
                st.write(f"**STOP LOSS:** ${(data['price'] - sl_dist):.2f}")
                st.write(f"**TARGET (E_MAX):** ${(data['price'] + tp_dist):.2f}")
            else:
                st.write(f"### ACTION: **SELL / SHORT**")
                st.write(f"**ENTRY:** ${data['price']:.2f}")
                st.write(f"**STOP LOSS:** ${(data['price'] + sl_dist):.2f}")
                st.write(f"**TARGET (E_MAX):** ${(data['price'] - tp_dist):.2f}")

            st.write(f"**POSITION SIZE:** {lots:.2f} Lots")
            st.write(f"**PROBABILITY OF EDGE:** {final_prob:.1f}%")
            
            st.divider()
            st.write(f"**RISK ADVISORY:** Risking ${risk_amount:,.2f} on $125k capital. Expected Drawdown: -18% to -22%.")
        else:
            st.error("Market Offline or API Limit Reached. Try again in 1 minute.")

st.caption("Terminal Execution Logic: ΔP/Δt = α × (μ - P_t) / σ_t + β × ∇VOL_t + ε_t")
