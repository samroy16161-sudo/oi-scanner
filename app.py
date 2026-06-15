import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime
import plotly.express as px

st.set_page_config(page_title="F&O OI Spurt Scanner", layout="wide", page_icon="📈")

STATE_FILE = "dashboard_state.json"
SECTOR_MAP = {
    'NIFTY AUTO': ['M&M', 'MARUTI', 'TATAMOTORS', 'BAJAJ-AUTO', 'EICHERMOT', 'HEROMOTOCO', 'TVSMOTOR', 'ASHOKLEY', 'BOSCHLTD', 'BHARATFORG', 'MRF', 'TIINDIA', 'MOTHERSON', 'BALKRISIND', 'SONACOMS'],
    'NIFTY BANK': ['HDFCBANK', 'ICICIBANK', 'SBIN', 'AXISBANK', 'KOTAKBANK', 'INDUSINDBK', 'PNB', 'BANKBARODA', 'FEDERALBNK', 'IDFCFIRSTB', 'AUBANK', 'BANDHANBNK'],
    'NIFTY FIN SERVICE': ['HDFCBANK', 'ICICIBANK', 'BAJFINANCE', 'AXISBANK', 'KOTAKBANK', 'SBIN', 'BAJAJFINSV', 'CHOLAFIN', 'SHRIRAMFIN', 'MUTHOOTFIN', 'SBI LIFE', 'HDFCLIFE', 'ICICIGI', 'SBICARD', 'PFC', 'RECLTD', 'M&MFIN', 'LICHSGFIN', 'CHOLAFIN'],
    'NIFTY FMCG': ['ITC', 'HUL', 'NESTLEIND', 'TATACONSUM', 'BRITANNIA', 'GODREJCP', 'DABUR', 'MARICO', 'COLPAL', 'UBL', 'UNITEDSPR', 'PGHH', 'EMAMILTD', 'RADICO', 'BALRAMCHIN'],
    'NIFTY IT': ['TCS', 'INFY', 'HCLTECH', 'WIPRO', 'TECHM', 'LTIM', 'PERSISTENT', 'COFORGE', 'MPHASIS', 'LTTS'],
    'NIFTY MEDIA': ['ZEEL', 'SUNTV', 'PVRINOX', 'NETWORK18', 'TV18BRDCST', 'DISHTV', 'HATHWAY', 'NAVKARCORP'],
    'NIFTY METAL': ['TATASTEEL', 'HINDALCO', 'JSWSTEEL', 'COALINDIA', 'ADANIENT', 'VEDL', 'NMDC', 'SAIL', 'JINDALSTEL', 'NATIONALUM', 'HINDZINC', 'WELCORP', 'RATNAMANI'],
    'NIFTY PHARMA': ['SUNPHARMA', 'DRREDDY', 'CIPLA', 'DIVISLAB', 'LUPIN', 'AUROPHARMA', 'TORNTPHARM', 'ZYDUSLIFE', 'ALKEM', 'BIOCON', 'GLENMARK', 'IPCALAB', 'LAURUSLABS', 'GRANULES', 'NATCOPHARM', 'SANOFI', 'ABBOTINDIA', 'PFIZER'],
    'NIFTY PSU BANK': ['SBIN', 'PNB', 'BANKBARODA', 'CANBK', 'UNIONBANK', 'INDIANB', 'BANKINDIA', 'MAHABANK', 'CENTRALBK', 'UCOBANK', 'IOB', 'PSB'],
    'NIFTY REALTY': ['DLF', 'MACROTECH', 'GODREJPROP', 'OBEROIRLTY', 'PHOENIXLTD', 'PRESTIGE', 'BRIGADE', 'SOBHA', 'MAHLIFE', 'SUNTECK']
}

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
        except:
            return None
    return None

def main():
    st.title("🚀 F&O OI Spurt Scanner (Live Engine Connected)")
    st.markdown("""
        **Real-Time Institutional-Grade OI Analyzer** 
        Continuously scans NSE F&O stocks and identifies the **Top 6** stocks with the highest 4-Day Average % Open Interest Spurt.
    """)
    
    state = load_state()
    if not state:
        st.warning("⏳ Waiting for backend engine to collect data... Please refresh in a minute.")
        return
        
    # Inject notifications
    st.session_state['notification_history'] = state.get('notification_history', [])
    
    st.sidebar.header("⚙️ Settings")
    st.sidebar.markdown("---")
    selected_page = st.sidebar.radio("Navigation", ["Sector Dashboard", "PDH/PDL Scanner"])
    
    st.sidebar.markdown("---")
    st.sidebar.success("🟢 **LIVE ENGINE CONNECTED**\\nRunning securely on backend server.")
    
    with st.sidebar.popover("🔔 Notifications History"):
        if st.session_state['notification_history']:
            for msg in reversed(st.session_state['notification_history']):
                st.caption(msg)
        else:
            st.write("No notifications yet.")
            
    st.markdown(f"<div style='text-align: right; padding-bottom: 5px; color: gray;'>Last Updated from Engine: {state.get('timestamp', '')}</div>", unsafe_allow_html=True)

    if selected_page == "Sector Dashboard":
        chart_col1, chart_col2 = st.columns(2)
        selected_sector = None
        
        with chart_col1:
            st.markdown("<h4 style='text-align: center;'>Sector Performance</h4>", unsafe_allow_html=True)
            sector_data = state.get('sector_df', [])
            if sector_data:
                sector_df = pd.DataFrame(sector_data)
                sector_df['Color'] = ['#00FF00' if x >= 0 else '#FF4500' for x in sector_df['% Change']]
                fig1 = px.bar(sector_df, y='Sector', x='% Change', text='% Change', orientation='h')
                fig1.update_traces(marker_color=sector_df['Color'], texttemplate='%{text:.2f}%', textposition='outside')
                fig1.update_layout(yaxis_title=None, xaxis_title=None, showlegend=False, height=450, margin=dict(t=10, b=10, l=10, r=40))
                event = st.plotly_chart(fig1, use_container_width=True, on_select="rerun", key="sector_chart")
                
                if hasattr(event, 'selection') and getattr(event.selection, 'points', None):
                    if len(event.selection.points) > 0:
                        selected_sector = event.selection.points[0].get('y')
                elif isinstance(event, dict) and event.get('selection', {}).get('points'):
                    selected_sector = event['selection']['points'][0].get('y')
                    
        with chart_col2:
            st.markdown("<h4 style='text-align: center;'>Sector Stocks (Top Spurts)</h4>", unsafe_allow_html=True)
            if selected_sector:
                st.caption(f"**{selected_sector}**")
                # We show the stocks from Top 6 Data that match the sector
                all_stocks_df = pd.DataFrame(state.get('all_stocks_data', []))
                matched_key = next((k for k in SECTOR_MAP.keys() if k in selected_sector.upper()), None)
                if matched_key and not all_stocks_df.empty:
                    sector_stocks = SECTOR_MAP.get(matched_key, [])
                    s_df = all_stocks_df[all_stocks_df['Stock'].isin(sector_stocks)].copy()
                    if not s_df.empty:
                        s_df['Color'] = ['#00FF00' if x >= 0 else '#FF4500' for x in s_df['Today']]
                        fig2 = px.bar(s_df, y='Stock', x='Today', text='Today', orientation='h')
                        fig2.update_traces(marker_color=s_df['Color'], texttemplate='%{text:.2f}%', textposition='outside')
                        fig2.update_layout(yaxis_title=None, xaxis_title=None, showlegend=False, height=450, margin=dict(t=10, b=10, l=10, r=40))
                        st.plotly_chart(fig2, use_container_width=True, key="stocks_chart")
                    else:
                        st.info("No stocks from this sector in today's spurt list.")
                else:
                    st.info("Sector mapping not found.")
            else:
                st.info("👈 Click on a Sector bar on the left to see its stocks!")
                
        st.markdown("---")
        
        top_6_data = pd.DataFrame(state.get('top_6_data', []))
        all_stocks_data = pd.DataFrame(state.get('all_stocks_data', []))
        
        if not top_6_data.empty and not all_stocks_data.empty:
            def style_spurt(val):
                if pd.isna(val): return ''
                color = '#00C853' if val > 0 else '#D50000'
                return f'color: {color}; font-weight: bold'
                
            format_dict = {'D-3': '{:+.2f}%', 'D-2': '{:+.2f}%', 'D-1': '{:+.2f}%', 'Today': '{:+.2f}%', 'Avg': '{:+.2f}%'}
            subset_cols = [c for c in ['D-3', 'D-2', 'D-1', 'Today', 'Avg'] if c in top_6_data.columns]
            
            display_df_1 = top_6_data.copy()
            display_df_1['LTP'] = display_df_1['LTP'].apply(lambda x: f"₹{x:,.2f}" if isinstance(x, (int, float)) else x)
            styled_df_1 = display_df_1.style.format(format_dict).map(style_spurt, subset=subset_cols)
            
            st.markdown("#### 🔥 4-Day Strong Trend (Top 6)")
            st.dataframe(styled_df_1, use_container_width=True, hide_index=True)
            
            st.markdown("---")
            st.markdown("### ⚡ Daily Top 10 Spurts & Consistent Performers")
            
            t_today = all_stocks_data.sort_values(by='Today', ascending=False).head(10)[['Stock', 'LTP', 'Today']]
            t_d1 = all_stocks_data.sort_values(by='D-1', ascending=False).head(10)[['Stock', 'LTP', 'D-1']] if 'D-1' in all_stocks_data else pd.DataFrame()
            t_d2 = all_stocks_data.sort_values(by='D-2', ascending=False).head(10)[['Stock', 'LTP', 'D-2']] if 'D-2' in all_stocks_data else pd.DataFrame()
            t_d3 = all_stocks_data.sort_values(by='D-3', ascending=False).head(10)[['Stock', 'LTP', 'D-3']] if 'D-3' in all_stocks_data else pd.DataFrame()
            
            def format_daily(df, col):
                if df.empty: return df
                disp = df.copy()
                disp['LTP'] = disp['LTP'].apply(lambda x: f"₹{x:,.2f}" if isinstance(x, (int, float)) else x)
                return disp.style.format({col: '{:+.2f}%'}).map(style_spurt, subset=[col])
                
            r1c1, r1c2 = st.columns(2)
            with r1c1:
                st.markdown("##### 📅 Today's Top 10")
                st.dataframe(format_daily(t_today, 'Today'), use_container_width=True, hide_index=True)
            with r1c2:
                st.markdown("##### 📅 D-1 Top 10")
                if not t_d1.empty: st.dataframe(format_daily(t_d1, 'D-1'), use_container_width=True, hide_index=True)
                
            r2c1, r2c2 = st.columns(2)
            with r2c1:
                st.markdown("##### 📅 D-2 Top 10")
                if not t_d2.empty: st.dataframe(format_daily(t_d2, 'D-2'), use_container_width=True, hide_index=True)
            with r2c2:
                st.markdown("##### 📅 D-3 Top 10")
                if not t_d3.empty: st.dataframe(format_daily(t_d3, 'D-3'), use_container_width=True, hide_index=True)

    elif selected_page == "PDH/PDL Scanner":
        st.markdown("<h2 style='text-align: center;'>🚀 PDH/PDL Breakout Scanner</h2>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center;'>Scanning live Top 10 OI Spurt stocks for Previous Day High/Low breakouts (After 9:25 AM)</p>", unsafe_allow_html=True)
        st.markdown("---")
        
        breakout_res = state.get('breakout_res', [])
        
        if breakout_res:
            brk_df = pd.DataFrame(breakout_res)
            
            def highlight_status(val):
                if "Bullish" in str(val): return 'color: #00FF00; font-weight: bold'
                if "Bearish" in str(val): return 'color: #FF4500; font-weight: bold'
                return 'color: gray'
                
            for col in ['LTP', 'PDH', 'PDL']:
                if col in brk_df.columns:
                    brk_df[col] = brk_df[col].apply(lambda x: f"₹{x:,.2f}" if isinstance(x, (int, float)) else x)
                    
            display_brk = brk_df[['Time', 'Stock', 'LTP', 'PDH', 'PDL', 'Status']]
            st.dataframe(display_brk.style.map(highlight_status, subset=['Status']), use_container_width=True, hide_index=True)
        else:
            st.info("No active breakouts found yet or scanner is out of market window (09:25 to 15:30).")

def start_engine():
    import subprocess
    import sys
    try:
        if sys.platform == "win32":
            output = subprocess.check_output("tasklist | findstr engine.py", shell=True).decode()
            if "engine.py" not in output:
                subprocess.Popen([sys.executable, "engine.py"])
        else:
            output = subprocess.check_output(["ps", "aux"]).decode()
            if output.count("engine.py") <= 1: 
                subprocess.Popen([sys.executable, "engine.py"])
    except Exception as e:
        try:
            subprocess.Popen([sys.executable, "engine.py"])
        except:
            pass

if __name__ == "__main__":
    start_engine()
    main()
