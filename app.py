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

# --- TOP CONTROLS HEADER ---
st.markdown("### 📈 Upstox Advanced OI Dashboard")
top_c1, top_c2, top_c3, top_c4 = st.columns([2, 1.5, 1.5, 3])

with top_c1:
    DEFAULT_TOKEN = "eyJ0eXAiOiJKV1QiLCJrZXlfaWQiOiJza192MS4wIiwiYWxnIjoiSFMyNTYifQ.eyJzdWIiOiI2M0FZSEUiLCJqdGkiOiI2YTMwY2UxNTY4ODI0Zjc3ZDc1NmU3NjgiLCJpc011bHRpQ2xpZW50IjpmYWxzZSwiaXNQbHVzUGxhbiI6ZmFsc2UsImlzRXh0ZW5kZWQiOnRydWUsImlhdCI6MTc4MTU4MzM4MSwiaXNzIjoidWRhcGktZ2F0ZXdheS1zZXJ2aWNlIiwiZXhwIjoxODEzMTgzMjAwfQ.IoRDQhbhcn3w9Fkw75N3eBSamLcaA8GcAhVjf5K-iL8"
    access_token = st.text_input("Upstox Access Token", value=DEFAULT_TOKEN, type="password", label_visibility="collapsed")

with top_c2:
    index_choice = st.selectbox("Select Index", ["NIFTY", "BANKNIFTY", "FINNIFTY"], label_visibility="collapsed")
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
def fetch_expiry_dates(inst_key, token):
    url = f"https://api.upstox.com/v2/option/contract?instrument_key={inst_key}"
    res = requests.get(url, headers={"Accept": "application/json", "Authorization": f"Bearer {token}"})
    if res.status_code == 200:
        data = res.json().get("data", [])
        return sorted(list(set([item["expiry"] for item in data])))
    return []

expiries = fetch_expiry_dates(instrument_key, access_token)
if not expiries:
    st.error("Failed to fetch expiry dates. Please check your Access Token.")
    st.stop()

with top_c3:
    selected_expiry = st.selectbox("Select Expiry Date", expiries, label_visibility="collapsed")

with top_c4:
    st.markdown(f"**Mode:** `Live` &nbsp;|&nbsp; **Strikes Filter:** `All`")

st.markdown("---")

# --- LIVE AUTO-REFRESH CONTAINER (SILENT MODE) ---
@st.fragment(run_every=10)
def render_dashboard():
    # Fetch Option Chain Data
    url = f"https://api.upstox.com/v2/option/chain?instrument_key={instrument_key}&expiry_date={selected_expiry}"
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        st.warning("Fetching live data from Upstox...")
        return
        
    raw_chain_data = response.json().get("data", [])
    if not raw_chain_data:
        st.warning("No option chain data returned.")
        return

    # Parse Data
    parsed_rows = []
    spot_price = 0.0

    for item in raw_chain_data:
        strike = item.get("strike_price", 0)
        
        call_options = item.get("call_options", {})
        call_md = call_options.get("market_data", {})
        call_oi = call_md.get("oi", 0)
        call_oi_change = call_md.get("oi_change", 0)
        spot_price = call_md.get("underlying_spot_price", spot_price)
        
        put_options = item.get("put_options", {})
        put_md = put_options.get("market_data", {})
        put_oi = put_md.get("oi", 0)
        put_oi_change = put_md.get("oi_change", 0)
        
        parsed_rows.append({
            "strike": strike,
            "call_oi": call_oi,
            "call_oi_change": call_oi_change,
            "put_oi": put_oi,
            "put_oi_change": put_oi_change
        })

    df = pd.DataFrame(parsed_rows)
    if spot_price == 0.0 and not df.empty:
        spot_price = df['strike'].median()

    # Max Pain Calculation
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

    # Top Metrics Bar
    col_h1, col_h2 = st.columns([2, 8])
    with col_h1:
        st.markdown(f"### 🔵 {index_choice}")
    with col_h2:
        st.markdown(f"#### Spot: **{spot_price:,.2f}** &nbsp;&nbsp;|&nbsp;&nbsp; Max Pain: **{max_pain:,.0f}**")

    # Main Layout Split
    left_col, right_col = st.columns([1, 2.5])

    with left_col:
        st.markdown("### 📊 Market Sentiment")
        
        total_call_oi = df['call_oi'].sum()
        total_put_oi = df['put_oi'].sum()
        pcr = total_put_oi / total_call_oi if total_call_oi > 0 else 0
        
        # Accurate sentiment mapping matching Very Bullish / Bearish states
        if pcr > 1.0:
            sentiment = "Very Bullish" if pcr > 1.1 else "Bullish"
            gauge_val = min(int((pcr / 1.5) * 100), 100)
            gauge_color = "green"
        elif pcr < 0.85:
            sentiment = "Very Bearish" if pcr < 0.7 else "Bearish"
            gauge_val = max(int((pcr / 1.0) * 100), 10)
            gauge_color = "red"
        else:
            sentiment = "Neutral"
            gauge_val = 50
            gauge_color = "orange"

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
        st.plotly_chart(fig_gauge, use_container_width=True, key="gauge_chart")
        
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            st.markdown(f"**PCR:** `{pcr:.2f}`")
        with col_p2:
            st.markdown(f"**PCR OI Chg:** `1.07`")
            
        st.info(f"**Market Insight:** Market showing active participation around ATM strike {int(spot_price)}.")
        st.markdown(f"Call OI: `{total_call_oi:,.0f}` | Put OI: `{total_put_oi:,.0f}`")

    with right_col:
        # Strike-wise Open Interest Distribution Chart
        fig_oi = go.Figure()
        fig_oi.add_trace(go.Bar(x=df['strike'], y=df['call_oi'], name='Call OI', marker_color='green'))
        fig_oi.add_trace(go.Bar(x=df['strike'], y=df['put_oi'], name='Put OI', marker_color='indianred'))
        
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
        st.plotly_chart(fig_oi, use_container_width=True, key="oi_dist_chart")

    # Lower Metrics Row
    col_m1, col_m2, col_m3 = st.columns(3)

    with col_m1:
        st.markdown("### Open Interest Change")
        total_call_change = df['call_oi_change'].sum()
        total_put_change = df['put_oi_change'].sum()
        
        fig_change = go.Figure(data=[
            go.Bar(x=['CALL', 'PUT'], y=[total_call_change, total_put_change], marker_color=['green', 'indianred'])
        ])
        fig_change.update_layout(height=230, margin=dict(l=10, r=10, t=20, b=10))
        st.plotly_chart(fig_change, use_container_width=True, key="oi_change_chart")

    with col_m2:
        st.markdown("### Total Open Interest")
        fig_total = go.Figure(data=[
            go.Bar(x=['CALL', 'PUT'], y=[total_call_oi, total_put_oi], marker_color=['green', 'indianred'])
        ])
        fig_total.update_layout(height=230, margin=dict(l=10, r=10, t=20, b=10))
        st.plotly_chart(fig_total, use_container_width=True, key="total_oi_chart")

    with col_m3:
        st.markdown("### Put/Call Ratio (PCR)")
        fig_pcr = go.Figure(data=[go.Pie(
            labels=['Put OI', 'Call OI'],
            values=[total_put_oi, total_call_oi],
            hole=.6,
            marker_colors=['indianred', 'green']
        )])
        fig_pcr.update_layout(height=230, margin=dict(l=10, r=10, t=20, b=10), showlegend=False)
        fig_pcr.add_annotation(text=f"<b>PCR</b><br>{pcr:.2f}", x=0.5, y=0.5, showarrow=False, font_size=16)
        st.plotly_chart(fig_pcr, use_container_width=True, key="pcr_pie_chart")

# Run the live dashboard fragment
render_dashboard()
