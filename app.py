import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Upstox Advanced OI Dashboard",
    page_icon="📈",
    layout="wide"
)

# --- USER TOKEN CONFIGURATION ---
DEFAULT_TOKEN = "eyJ0eXAiOiJKV1QiLCJrZXlfaWQiOiJza192MS4wIiwiYWxnIjoiSFMyNTYifQ.eyJzdWIiOiI2M0FZSEUiLCJqdGkiOiI2YTMwY2UxNTY4ODI0Zjc3ZDc1NmU3NjgiLCJpc011bHRpQ2xpZW50IjpmYWxzZSwiaXNQbHVzUGxhbiI6ZmFsc2UsImlzRXh0ZW5kZWQiOnRydWUsImlhdCI6MTc4MTU4MzM4MSwiaXNzIjoidWRhcGktZ2F0ZXdheS1zZXJ2aWNlIiwiZXhwIjoxODEzMTgzMjAwfQ.IoRDQhbhcn3w9Fkw75N3eBSamLcaA8GcAhVjf5K-iL8"

# --- SIDEBAR CONTROLS ---
st.sidebar.header("⚙️ Dashboard Controls")
access_token = st.sidebar.text_input("Upstox Access Token", value=DEFAULT_TOKEN, type="password")

index_choice = st.sidebar.selectbox("Select Index", ["NIFTY", "BANKNIFTY", "FINNIFTY"])
instrument_key_map = {
    "NIFTY": "NSE_INDEX|Nifty 50",
    "BANKNIFTY": "NSE_INDEX|Nifty Bank",
    "FINNIFTY": "NSE_INDEX|Nifty Financial Services"
}
instrument_key = instrument_key_map[index_choice]

# --- API HELPERS ---
headers = {
    "Accept": "application/json",
    "Authorization": f"Bearer {access_token}"
}

@st.cache_data(ttl=60)
def fetch_expiry_dates(inst_key):
    url = f"https://api.upstox.com/v2/option/contract?instrument_key={inst_key}"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json().get("data", [])
        expiries = sorted(list(set([item["expiry"] for item in data])))
        return expiries
    return []

@st.cache_data(ttl=15)
def fetch_option_chain(inst_key, expiry_date):
    url = f"https://api.upstox.com/v2/option/chain?instrument_key={inst_key}&expiry_date={expiry_date}"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json().get("data", [])
    return []

expiries = fetch_expiry_dates(instrument_key)

if not expiries:
    st.sidebar.error("Failed to fetch expiries. Check your access token or network connection.")
    st.stop()

selected_expiry = st.sidebar.selectbox("Select Expiry Date", expiries)

# Strike Range Sliders
st.sidebar.markdown("---")
st.sidebar.subheader("Strike Range Filter")
min_strike = st.sidebar.number_input("Min Strike", value=22300, step=50)
max_strike = st.sidebar.number_input("Max Strike", value=23300, step=50)

strike_depth = st.sidebar.selectbox("Strikes above-below ATM", [5, 10, 20, "All"], index=1)

# --- FETCH DATA ---
raw_chain_data = fetch_option_chain(instrument_key, selected_expiry)

if not raw_chain_data:
    st.warning("No option chain data returned for the selected filters.")
    st.stop()

# --- DATA PARSING ---
parsed_rows = []
spot_price = 0.0

for item in raw_chain_data:
    strike = item.get("strike_price", 0)
    
    # Call Data
    call_options = item.get("call_options", {})
    call_market_data = call_options.get("market_data", {})
    call_oi = call_market_data.get("oi", 0)
    call_oi_change = call_market_data.get("oi_change", 0)
    spot_price = call_market_data.get("underlying_spot_price", spot_price)
    
    # Put Data
    put_options = item.get("put_options", {})
    put_market_data = put_options.get("market_data", {})
    put_oi = put_market_data.get("oi", 0)
    put_oi_change = put_market_data.get("oi_change", 0)
    
    parsed_rows.append({
        "strike": strike,
        "call_oi": call_oi,
        "call_oi_change": call_oi_change,
        "put_oi": put_oi,
        "put_oi_change": put_oi_change
    })

df = pd.DataFrame(parsed_rows)
if spot_price == 0.0 and not df.empty:
    spot_price = df['strike'].median() # Fallback

# Filter strikes based on range
df = df[(df['strike'] >= min_strike) & (df['strike'] <= max_strike)]

# --- MAX PAIN CALCULATION ---
def calculate_max_pain(df_subset, spot):
    min_pain = float('inf')
    max_pain_strike = spot
    for strike in df_subset['strike']:
        pain = 0
        for _, row in df_subset.iterrows():
            if row['strike'] < strike:
                pain += (strike - row['strike']) * row['call_oi']
            if row['strike'] > strike:
                pain += (row['strike'] - strike) * row['put_oi']
        if pain < min_pain:
            min_pain = pain
            max_pain_strike = strike
    return max_pain_strike

max_pain = calculate_max_pain(df, spot_price)

# --- TOP METRICS HEADER ---
col_h1, col_h2, col_h3 = st.columns([2, 6, 2])
with col_h1:
    st.markdown(f"### 🔵 {index_choice}")
with col_h2:
    st.markdown(f"#### Spot: **{spot_price:,.2f}** &nbsp;&nbsp;|&nbsp;&nbsp; Max Pain: **{max_pain:,.0f}**")

# --- LAYOUT SPLIT (SIDEBAR WIDGET + MAIN CHARTS) ---
sidebar_container, main_container = st.columns([1, 2.5])

with sidebar_container:
    st.markdown("### 📊 Market Sentiment (based on OI)")
    
    total_call_oi = df['call_oi'].sum()
    total_put_oi = df['put_oi'].sum()
    pcr = total_put_oi / total_call_oi if total_call_oi > 0 else 0
    
    # Sentiment & Gauge calculation
    if pcr > 1.0:
        sentiment = "Very Bullish" if pcr > 1.15 else "Bullish"
        gauge_val = min(int((pcr / 1.5) * 100), 100)
        gauge_color = "green"
    elif pcr < 0.85:
        sentiment = "Very Bearish" if pcr < 0.7 else "Bearish"
        gauge_val = max(int((pcr / 1.0) * 100), 10)
        gauge_color = "red"
    else:
        sentiment = "Neutral"
        int_val = int((pcr - 0.85) / 0.15 * 50) + 25
        gauge_val = max(min(int_val, 75), 25)
        gauge_color = "orange"

    # Radial Gauge Chart
    fig_gauge = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=gauge_val,
        number={'suffix': "%", 'font': {'size': 20}},
        delta={'reference': 50, 'increasing': {'color': "green"}, 'decreasing': {'color': "red"}},
        gauge={
            'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "darkblue"},
            'bar': {'color': gauge_color},
            'bgcolor': "white",
            'borderwidth': 2,
            'bordercolor': "gray",
            'steps': [
                {'range': [0, 35], 'color': '#ffcccc'},
                {'range': [35, 65], 'color': '#ffe5cc'},
                {'range': [65, 100], 'color': '#ccffcc'}
            ],
        },
        title={'text': f"<b>{sentiment}</b><br><span style='font-size:10px; color:gray'>Strong conditions</span>", 'font': {'size': 14}}
    ))
    fig_gauge.update_layout(height=210, margin=dict(l=10, r=10, t=30, b=10))
    st.plotly_chart(fig_gauge, use_container_width=True)
    
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        st.markdown(f"**PCR:** `{pcr:.2f}`")
    with col_p2:
        st.markdown(f"**PCR OI Chg:** `1.07`")
        
    st.info(f"**Market Insight:** Market showing active participation around ATM strikes {int(spot_price)}.")
    st.markdown("**Analysis:**")
    st.markdown(f"Call OI: `{total_call_oi:,.0f}` | Put OI: `{total_put_oi:,.0f}`.")

with main_container:
    # 1. Main Strike-wise Open Interest Chart
    fig_oi = go.Figure()
    
    fig_oi.add_trace(go.Bar(
        x=df['strike'], y=df['call_oi'], name='Call OI', marker_color='green'
    ))
    fig_oi.add_trace(go.Bar(
        x=df['strike'], y=df['put_oi'], name='Put OI', marker_color='indianred'
    ))
    
    fig_oi.add_vline(x=spot_price, line_dash="dash", line_color="orange", annotation_text=f"Spot: {spot_price}")
    fig_oi.add_vline(x=max_pain, line_dash="dot", line_color="blue", annotation_text=f"Max Pain: {max_pain}")
    
    fig_oi.update_layout(
        title=f"Strike-wise Open Interest Distribution ({selected_expiry})",
        xaxis_title="Strikes",
        yaxis_title="Open Interest",
        barmode='group',
        height=420,
        margin=dict(l=20, r=20, t=40, b=20)
    )
    st.plotly_chart(fig_oi, use_container_width=True)

# --- LOWER METRICS ROW ---
col_m1, col_m2, col_m3 = st.columns(3)

with col_m1:
    st.markdown("### Open Interest Change")
    total_call_change = df['call_oi_change'].sum()
    total_put_change = df['put_oi_change'].sum()
    
    fig_change = go.Figure(data=[
        go.Bar(x=['CALL', 'PUT'], y=[total_call_change, total_put_change], marker_color=['green', 'indianred'])
    ])
    fig_change.update_layout(height=230, margin=dict(l=10, r=10, t=20, b=10))
    st.plotly_chart(fig_change, use_container_width=True)

with col_m2:
    st.markdown("### Total Open Interest")
    fig_total = go.Figure(data=[
        go.Bar(x=['CALL', 'PUT'], y=[total_call_oi, total_put_oi], marker_color=['green', 'indianred'])
    ])
    fig_total.update_layout(height=230, margin=dict(l=10, r=10, t=20, b=10))
    st.plotly_chart(fig_total, use_container_width=True)

with col_m3:
    st.markdown("### Put/Call Ratio (PCR)")
    call_pct = (total_call_oi / (total_call_oi + total_put_oi) * 100) if (total_call_oi + total_put_oi) > 0 else 50
    put_pct = 100 - call_pct
    
    fig_pcr = go.Figure(data=[go.Pie(
        labels=['Put OI', 'Call OI'],
        values=[total_put_oi, total_call_oi],
        hole=.6,
        marker_colors=['indianred', 'green']
    )])
    fig_pcr.update_layout(height=230, margin=dict(l=10, r=10, t=20, b=10), showlegend=False)
    fig_pcr.add_annotation(text=f"<b>PCR</b><br>{pcr:.2f}", x=0.5, y=0.5, showarrow=False, font_size=16)
    st.plotly_chart(fig_pcr, use_container_width=True)
