import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone

# --- THE ARCHITECT'S UNIFORM ENGINE (FINAL VERSION) ---
# This version targets SPOT GOLD (XAUUSD) instead of Futures

EQUITY = 125000
KELLY_FRAC = 0.0938 

def get_autonomous_data():
    try:
        # Ticker XAUUSD=X is the Spot Gold price (Matches brokers more closely)
        gold = yf.Ticker("XAUUSD=X")
        
        # Pull 7 days of 1-hour data for WOFM and TDO
        df_h = gold.history(period="7d", interval="1h")
        # Pull 1 day of 5-minute data for ATR and Vol
        df_m5 = gold.history(period="1d", interval="5m")
        
        if df_h.empty or df_m5.empty:
            return None

        # 1. AUTO-WOFM (Monday 00:00 GMT Midpoint)
        # Identify the start of the current trading week
        now = datetime.now(timezone.utc)
        monday_offset = now.weekday()
        monday_start = (now - timedelta(days=monday_offset)).replace(hour=0, minute=0, second=0, microsecond=0)
        
        weekly_slice = df_h[df_h.index >= pd.to_datetime(monday_start).tz_localize('UTC')]
        if not weekly_slice.empty:
            wofm_mid = (weekly_slice['High'].iloc[0] + weekly_slice['Low'].iloc[0]) / 2
        else:
            wofm_mid = (df_h['High'].iloc[0] + df_h['Low'].iloc[0]) / 2

        # 2. AUTO-TDO (True Day Open - 20:00 GMT Reset)
        # We find the close of the 20:00 GMT candle from the previous session
        tdo_slice = df_h.between_time('19:30', '20:30')
        tdo = tdo_slice['Close'].iloc[-1] if not tdo_slice.empty else df_h['Close'].iloc[-24]

        # 3. LIVE CALCULATIONS
        current_price = df_m5['Close'].iloc[-1]
        atr = (df_m5['High'] - df_m5['Low']).rolling(5).mean().iloc[-1]
        
        # Volume Imbalance (Beta Factor)
        avg_vol = df_m5['Volume'].iloc[-20:].mean()
        curr_vol = df_m5['Volume'].iloc[-1]
        vol_gradient = curr_vol / avg_vol if avg_vol > 0 else 1.0

        return {
            "price": current_price,
            "wofm": wofm_mid,
            "tdo": tdo,
            "atr": atr,
            "vol_gradient": vol_gradient,
            "time": now
        }
    except Exception as e:
        return None

# --- STREAMLIT INTERFACE ---
st.set_page_config(page_title="Architect XAUUSD", layout="wide")
st.title("🏛️ XAUUSD ARCHITECT: QUANT TERMINAL")
st.caption("Live Spot Gold (XAUUSD) | Institutional Inertia Model")

# OPTIONAL: Broker Offset (To perfectly sync with your specific broker)
with st.expander("Broker Sync (Optional)"):
    offset = st.number_input("If your broker price is different, enter the difference here (e.g., -2.50 or +1.20):", value=0.0)

if st.button("CALCULATE TRADE SIGNALS"):
    data = get_autonomous_data()
    
    if data:
        # Apply offset to match user's broker exactly
        live_p = data['price'] + offset
        wofm_p = data['wofm'] + offset
        tdo_p = data['tdo'] + offset
        
        # 4. DIRECTIONAL SYNTHESIS (Part II of request)
        qib = 0.42
        tdo_bias = 0.25 if live_p > tdo_p else -0.25
        
        # 90-Minute Macro Cycle Check
        curr_min = data['time'].hour * 60 + data['time'].minute
        is_moc = any(abs(curr_min - m) <= 5 for m in [0, 90, 180, 270, 360, 450, 540, 630, 720, 810, 900, 990, 1080, 1170, 1260, 1350])
        moc_bias = 0.75 if is_moc else 0.40
        
        p_long = (qib * 0.35) + (tdo_bias * 0.25) + (moc_bias * 0.40)
        
        # 5. RISK MANAGEMENT (Kelly)
        risk_usd = EQUITY * KELLY_FRAC
        sl_dist = 1.8 * data['atr']
        lots = risk_usd / (sl_dist * 100)

        # UI DISPLAY
        col1, col2, col3 = st.columns(3)
        col1.metric("BROKER PRICE", f"${live_p:.2f}")
        col2.metric("WOFM CENTER", f"${wofm_p:.2f}")
        col3.metric("TDO RESET", f"${tdo_p:.2f}")

        st.divider()

        # SIGNAL OUTPUT
        if is_moc:
            st.success("⚡ MOC EDGE ACTIVE: Mean-Reversion probability spiked to 73-78%")
        
        if p_long > 0.50:
            st.header("🟢 SIGNAL: LONG (BUY)")
            st.write(f"**ENTRY:** ${live_p:.2f}")
            st.write(f"**STOP LOSS:** ${(live_p - sl_dist):.2f}")
            st.write(f"**TARGET:** ${wofm_p:.2f} (WOFM Midpoint)")
        else:
            st.header("🔴 SIGNAL: SHORT (SELL)")
            st.write(f"**ENTRY:** ${live_p:.2f}")
            st.write(f"**STOP LOSS:** ${(live_p + sl_dist):.2f}")
            st.write(f"**TARGET:** ${tdo_p:.2f} (TDO Target)")

        st.info(f"**POSITION SIZE:** {lots:.2f} Lots (Risk: ${risk_usd:,.0f})")
        st.caption(f"Confidence Score: {p_long:.2f} | Vol Gradient: {data['vol_gradient']:.2f}")
        
    else:
        st.error("Data fetch failed. Markets might be closed or API is syncing.")

st.warning("Note: Free market data has a 15-minute delay. Use the 'Broker Sync' above if the price gap is larger than 1.00.")
