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
        
    st.session_state['notification_history'] = state.get('notification_history', [])
    
    st.sidebar.header("⚙️ Settings")
    st.sidebar.markdown("---")
    selected_page = st.sidebar.radio("Navigation", ["Sector Dashboard", "PDH/PDL Scanner"])
    
    st.sidebar.markdown("---")
    st.sidebar.success("🟢 **LIVE ENGINE CONNECTED**\nRunning securely on backend server.")
    
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
                
                fig1 = px.bar(sector_df, y='Sector', x='% Change', text='% Change', orientation='h')
                fig1.update_traces(
                    marker_color=['#00C853' if x >= 0 else '#D50000' for x in sector_df['% Change']], 
                    texttemplate='<b>%{y}</b><br>%{text:+.2f}%', 
                    textposition='auto',
                    textangle=0,
                    textfont=dict(color='white', size=14)
                )
                fig1.update_layout(
                    yaxis=dict(showgrid=False, showticklabels=False, title=""),
                    xaxis=dict(showgrid=False, showticklabels=False, title="", zeroline=True, zerolinecolor='gray', zerolinewidth=2),
                    showlegend=False, 
                    height=450, 
                    margin=dict(t=0, b=0, l=0, r=0),
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    clickmode='event+select'
                )
                
                event = st.plotly_chart(fig1, use_container_width=True, on_select="rerun", key="sector_chart", config={'displayModeBar': False})
                
                if hasattr(event, 'selection') and getattr(event.selection, 'points', None):
                    if len(event.selection.points) > 0:
                        selected_sector = event.selection.points[0].get('y')
                elif isinstance(event, dict) and event.get('selection', {}).get('points'):
                    selected_sector = event['selection']['points'][0].get('y')
                    
        with chart_col2:
            st.markdown("<h4 style='text-align: center;'>Sector Stocks (Top Spurts)</h4>", unsafe_allow_html=True)
            if selected_sector:
                st.caption(f"**{selected_sector}**")
                all_stocks_df = pd.DataFrame(state.get('all_stocks_data', []))
                matched_key = next((k for k in SECTOR_MAP.keys() if selected_sector.upper() in k), None)
                if matched_key and not all_stocks_df.empty:
                    sector_stocks = SECTOR_MAP.get(matched_key, [])
                    s_df = all_stocks_df[all_stocks_df['Stock'].isin(sector_stocks)].copy()
                    if not s_df.empty:
                        # Stocks ko Lowest se Highest sort kiya taki Chart me Sabse Highest wala Upar aaye!
                        s_df = s_df.sort_values(by='Today_Sort', ascending=True)
                        
                        fig2 = px.bar(s_df, y='Stock', x='Today_Sort', text='Today_Sort', orientation='h')
                        fig2.update_traces(
                            marker_color=['#00C853' if x >= 0 else '#D50000' for x in s_df['Today_Sort']], 
                            texttemplate='<b>%{y}</b><br>%{text:+.2f}%', 
                            textposition='auto',
                            textangle=0,
                            textfont=dict(color='white', size=14)
                        )
                        fig2.update_layout(
                            yaxis=dict(showgrid=False, showticklabels=False, title=""),
                            xaxis=dict(showgrid=False, showticklabels=False, title="", zeroline=True, zerolinecolor='gray', zerolinewidth=2),
                            showlegend=False, 
                            height=450, 
                            margin=dict(t=0, b=0, l=0, r=0),
                            plot_bgcolor='rgba(0,0,0,0)',
                            paper_bgcolor='rgba(0,0,0,0)',
                            clickmode='event+select'
                        )
                        st.plotly_chart(fig2, use_container_width=True, key="stocks_chart", config={'displayModeBar': False})
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
                
            date_cols = [c for c in top_6_data.columns if c not in ['Stock', 'LTP', 'Avg', 'Today_Sort']]
            format_dict = {c: '{:+.2f}%' for c in date_cols + ['Avg']}
            
            display_df_1 = top_6_data.drop(columns=['Today_Sort'], errors='ignore').copy()
            display_df_1['LTP'] = display_df_1['LTP'].apply(lambda x: f"₹{x:,.2f}" if isinstance(x, (int, float)) else x)
            styled_df_1 = display_df_1.style.format(format_dict).map(style_spurt, subset=date_cols + ['Avg'])
            
            st.markdown("#### 🔥 4-Day Strong Trend (Top 6)")
            st.dataframe(styled_df_1, use_container_width=True, hide_index=True)
            
            st.markdown("---")
            st.markdown("### ⚡ Daily Top 10 Spurts")
            
            def format_daily(df, col):
                if df.empty: return df
                disp = df.copy()
                disp['LTP'] = disp['LTP'].apply(lambda x: f"₹{x:,.2f}" if isinstance(x, (int, float)) else x)
                return disp.style.format({col: '{:+.2f}%'}).map(style_spurt, subset=[col])
                
            rev_dates = list(reversed(date_cols))
            
            cols_ui = st.columns(2)
            for i, d_col in enumerate(rev_dates):
                t_df = all_stocks_data.sort_values(by=d_col, ascending=False).head(10)[['Stock', 'LTP', d_col]]
                with cols_ui[i % 2]:
                    st.markdown(f"##### 📅 Top 10 for {d_col}")
                    st.dataframe(format_daily(t_df, d_col), use_container_width=True, hide_index=True)

            # Consistent Performers Logic
            st.markdown("---")
            st.markdown("### 🎯 Consistent Performers (Common in Top 10s)")
            
            all_top_stocks = []
            for d_col in rev_dates:
                all_top_stocks.extend(all_stocks_data.sort_values(by=d_col, ascending=False).head(10)['Stock'].tolist())
                
            if all_top_stocks:
                from collections import Counter
                counts = Counter(all_top_stocks)
                
                consistent_data = []
                for stock, count in counts.items():
                    if count >= 2:
                        consistent_data.append({
                            'Stock': stock,
                            'Times in Top 10': count
                        })
                
                if consistent_data:
                    cons_df = pd.DataFrame(consistent_data).sort_values(by='Times in Top 10', ascending=False)
                    st.dataframe(cons_df, use_container_width=True, hide_index=True)
                else:
                    st.info("No stock repeated in Top 10s across these days.")

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
