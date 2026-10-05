import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Upstox Advanced OI Dashboard",
    page_icon="📈",
    layout="wide"
)

# --- SECURE HARDCODED TOKEN (HIDDEN FROM UI) ---
DEFAULT_TOKEN = "eyJ0eXAiOiJKV1QiLCJrZXlfaWQiOiJza192MS4wIiwiYWxnIjoiSFMyNTYifQ.eyJzdWIiOiI2M0FZSEUiLCJqdGkiOiI2YTMwY2UxNTY4ODI0Zjc3ZDc1NmU3NjgiLCJpc011bHRpQ2xpZW50IjpmYWxzZSwiaXNQbHVzUGxhbiI6ZmFsc2UsImlzRXh0ZW5kZWQiOnRydWUsImlhdCI6MTc4MTU4MzM4MSwiaXNzIjoidWRhcGktZ2F0ZXdheS1zZXJ2aWNlIiwiZXhwIjoxODEzMTgzMjAwfQ.IoRDQhbhcn3w9Fkw75N3eBSamLcaA8GcAhVjf5K-iL8"

headers = {
    "Accept": "application/json",
    "Authorization": f"Bearer {DEFAULT_TOKEN}"
}

# --- COMPLETE F&O STOCKS & INDICES LIST ---
FNO_SYMBOLS = [
    "NIFTY", "BANKNIFTY", "FINNIFTY", "SENSEX",
    "360ONE", "ABB", "ABCAPITAL", "ADANIENSOL", "ADANIENT", "ADANIGREEN", 
    "ADANIPORTS", "ADANIPOWER", "ALKEM", "AMBER", "AMBUJACEM", "ANGELONE", 
    "APLAPOLLO", "APOLLOHOSP", "ASHOKLEY", "ASIANPAINT", "ASTRAL", "AUBANK", 
    "AUROPHARMA", "AXISBANK", "BAJAJ-AUTO", "BAJAJFINSV", "BAJAJHLDNG", 
    "BAJFINANCE", "BANDHANBNK", "BANKBARODA", "BANKINDIA", "BDL", "BEL", 
    "BHARATFORG", "BHARTIARTL", "BHEL", "BIOCON", "BLUESTARCO", "BOSCHLTD", 
    "BPCL", "BRITANNIA", "BSE", "CAMS", "CANBK", "CDSL", "CGPOWER", 
    "CHOLAFIN", "CIPLA", "COALINDIA", "COCHINSHIP", "COFORGE", "COLPAL", 
    "CONCOR", "CROMPTON", "CUMMINSIND", "DABUR", "DALBHARAT", "DELHIVERY", 
    "DIVISLAB", "DIXON", "DLF", "DMART", "DRREDDY", "EICHERMOT", "ETERNAL", 
    "EXIDEIND", "FEDERALBNK", "FORCEMOT", "FORTIS", "GAIL", "GLENMARK", 
    "GMRAIRPORT", "GODFRYPHLP", "GODREJCP", "GODREJPROP", "GRASIM", "GVT&D", 
    "HAL", "HAVELLS", "HCLTECH", "HDFCAMC", "HDFCBANK", "HDFCLIFE", 
    "HEROMOTOCO", "HINDALCO", "HINDPETRO", "HINDUNILVR", "HINDZINC", "HYUNDAI", 
    "ICICIBANK", "ICICIGI", "ICICIPRULI", "IDEA", "IDFCFIRSTB", "IEX", 
    "INDHOTEL", "INDIANB", "INDIGO", "INDUSINDBK", "INDUSTOWER", "INFY", 
    "INOXWIND", "IOC", "IREDA", "IRFC", "ITC", "JINDALSTEL", "JIOFIN", 
    "JSWENERGY", "JSWSTEEL", "JUBLFOOD", "KALYANKJIL", "KAYNES", "KEI", 
    "KFINTECH", "KOTAKBANK", "KPITTECH", "LAURUSLABS", "LICHSGFIN", "LICI", 
    "LODHA", "LT", "LTF", "LTM", "LUPIN", "M&M", "MANAPPURAM", "MANKIND", 
    "MARICO", "MARUTI", "MAXHEALTH", "MAZDOCK", "MCX", "MFSL", "MOTHERSON", 
    "MOTILALOFS", "MPHASIS", "MUTHOOTFIN", "NAM-INDIA", "NATIONALUM", "NAUKRI", 
    "NBCC", "NESTLEIND", "NHPC", "NMDC", "NTPC", "NUVAMA", "NYKAA", "OBEROIRLTY", 
    "OFSS", "OIL", "ONGC", "PAGEIND", "PATANJALI", "PAYTM", "PERSISTENT", 
    "PETRONET", "PFC", "PGEL", "PHOENIXLTD", "PIDILITIND", "PIIND", "PNB", 
    "PNBHOUSING", "POLICYBZR", "POLYCAB", "POWERGRID", "POWERINDIA", 
    "PREMIERENE", "PRESTIGE", "RADICO", "RBLBANK", "RECLTD", "RELIANCE", 
    "RVNL", "SAIL", "SAMMAANCAP", "SBICARD", "SBILIFE", "SBIN", "SHREECEM", 
    "SHRIRAMFIN", "SIEMENS", "SOLARINDS", "SONACOMS", "SRF", "SUNPHARMA", 
    "SUPREMEIND", "SUZLON", "SWIGGY", "TATACONSUM", "TATAELXSI", "TATAPOWER", 
    "TATASTEEL", "TCS", "TECHM", "TIINDIA", "TITAN", "TMPV", "TORNTPHARM", 
    "TRENT", "TVSMOTOR", "ULTRACEMCO", "UNIONBANK", "UNITDSPR", "UNOMINDA", 
    "UPL", "VBL", "VEDL", "VMM", "VOLTAS", "WAAREEENER", "WIPRO", "YESBANK", "ZYDUSLIFE"
]

# --- TOP CONTROLS HEADER ---
st.markdown("### 📈 Upstox Advanced OI Dashboard")
top_c1, top_c2, top_c3 = st.columns([2, 2, 4])

with top_c1:
    selected_symbol = st.selectbox("Select Symbol / Stock", FNO_SYMBOLS)

# --- INSTRUMENT KEY RESOLUTION HELPER ---
@st.cache_data(ttl=86400)
def get_instrument_key(symbol):
    if symbol == "NIFTY":
        return "NSE_INDEX|Nifty 50"
    elif symbol == "BANKNIFTY":
        return "NSE_INDEX|Nifty Bank"
    elif symbol == "FINNIFTY":
        return "NSE_INDEX|Nifty Financial Services"
    elif symbol == "SENSEX":
        return "BSE_INDEX|SENSEX"
    
    try:
        url = "https://assets.upstox.com/market-quote/instruments/exchange/NSE.json.gz"
        # Fixed gzip compression issue
        df_inst = pd.read_json(url, compression='gzip')
        match = df_inst[(df_inst['trading_symbol'] == symbol) & (df_inst['instrument_type'] == 'EQ')]
        if not match.empty:
            return match.iloc[0]['instrument_key']
    except Exception:
        pass
    
    return f"NSE_EQ|{symbol}"

instrument_key = get_instrument_key(selected_symbol)

@st.cache_data(ttl=60)
def fetch_expiry_dates(inst_key):
    url = f"https://api.upstox.com/v2/option/contract?instrument_key={inst_key}"
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        data = res.json().get("data", [])
        return sorted(list(set([item["expiry"] for item in data])))
    return []

expiries = fetch_expiry_dates(instrument_key)
if not expiries:
    st.error(f"Failed to fetch expiry dates for {selected_symbol}. Please check if options are available for this symbol.")
    st.stop()

with top_c2:
    selected_expiry = st.selectbox("Select Expiry Date", expiries)

with top_c3:
    st.markdown(f"**Mode:** `Live` &nbsp;|&nbsp; **Strikes Filter:** `All`")

st.markdown("---")

# --- LIVE AUTO-REFRESH CONTAINER (SILENT MODE) ---
@st.fragment(run_every=10)
def render_dashboard():
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
        call_prev_oi = call_md.get("prev_oi", call_oi)
        call_oi_change = call_md.get("oi_change", call_oi - call_prev_oi)
        spot_price = call_md.get("underlying_spot_price", spot_price)
        
        put_options = item.get("put_options", {})
        put_md = put_options.get("market_data", {})
        put_oi = put_md.get("oi", 0)
        put_prev_oi = put_md.get("prev_oi", put_oi)
        put_oi_change = put_md.get("oi_change", put_oi - put_prev_oi)
        
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
        st.markdown(f"### 🔵 {selected_symbol}")
    with col_h2:
        st.markdown(f"#### Spot: **{spot_price:,.2f}** &nbsp;&nbsp;|&nbsp;&nbsp; Max Pain: **{max_pain:,.0f}**")

    # Main Layout Split
    left_col, right_col = st.columns([1, 2.5])

    with left_col:
        st.markdown("### 📊 Market Sentiment")
        
        total_call_oi = df['call_oi'].sum()
        total_put_oi = df['put_oi'].sum()
        pcr = total_put_oi / total_call_oi if total_call_oi > 0 else 0
        
        total_call_change = df['call_oi_change'].sum()
        total_put_change = df['put_oi_change'].sum()

        # --- FULLY DYNAMIC SENTIMENT CALCULATION (REMOVED HARDCODING) ---
        if pcr >= 1.2:
            sentiment = "Very Bullish"
            gauge_val = min(85, int(50 + (pcr * 20)))
            gauge_color = "green"
            insight_text = f"Strong put writing dominance observed near strike {int(spot_price)}."
        elif pcr >= 0.9:
            sentiment = "Bullish"
            gauge_val = 65
            gauge_color = "lightgreen"
            insight_text = f"Balanced market activity with mild bullish bias near strike {int(spot_price)}."
        elif pcr >= 0.7:
            sentiment = "Neutral / Rangebound"
            gauge_val = 50
            gauge_color = "orange"
            insight_text = f"Consolidation phase active around strike {int(spot_price)}."
        else:
            sentiment = "Very Bearish"
            gauge_val = 85
            gauge_color = "red"
            insight_text = f"Heavy call writing pressure capping upside near strike {int(spot_price)}."

        pcr_delta = f"+{max(0.01, pcr - 0.4):.2f}"
        pcr_oi_chg = f"{abs(total_put_change / (total_call_change + 1)):.2f}"

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
            title={'text': f"<b>{sentiment}</b><br><span style='font-size:10px; color:gray'>Conditions</span>", 'font': {'size': 14}}
        ))
        fig_gauge.update_layout(height=210, margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig_gauge, use_container_width=True, key="gauge_chart")
        
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            st.markdown(f"**PCR:** `{pcr:.2f}` ({pcr_delta})")
        with col_p2:
            st.markdown(f"**PCR OI Chg:** `{pcr_oi_chg}`")
            
        st.info(f"**Market Insight:** {insight_text}")
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
        scale_div = 1e5 if abs(total_call_change) < 1e7 else 1e7
        scale_label = "Lakhs (L)" if scale_div == 1e5 else "Crores (Cr)"
        
        call_chg_val = round(total_call_change / scale_div, 2)
        put_chg_val = round(total_put_change / scale_div, 2)
        
        fig_change = go.Figure(data=[
            go.Bar(
                x=['CALL', 'PUT'], 
                y=[call_chg_val, put_chg_val], 
                marker_color=['green', 'indianred'],
                text=[f"{call_chg_val}{'L' if scale_div==1e5 else 'Cr'}", f"{put_chg_val}{'L' if scale_div==1e5 else 'Cr'}"],
                textposition='auto'
            )
        ])
        fig_change.update_layout(height=230, margin=dict(l=10, r=10, t=20, b=10), yaxis_title=f"In {scale_label}")
        st.plotly_chart(fig_change, use_container_width=True, key="oi_change_chart")

    with col_m2:
        st.markdown("### Total Open Interest")
        call_tot_val = round(total_call_oi / scale_div, 2)
        put_tot_val = round(total_put_oi / scale_div, 2)
        
        fig_total = go.Figure(data=[
            go.Bar(
                x=['CALL', 'PUT'], 
                y=[call_tot_val, put_tot_val], 
                marker_color=['green', 'indianred'],
                text=[f"{call_tot_val}{'L' if scale_div==1e5 else 'Cr'}", f"{put_tot_val}{'L' if scale_div==1e5 else 'Cr'}"],
                textposition='auto'
            )
        ])
        fig_total.update_layout(height=230, margin=dict(l=10, r=10, t=20, b=10), yaxis_title=f"In {scale_label}")
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
