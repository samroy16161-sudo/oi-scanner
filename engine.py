import sqlite3
import pandas as pd
import numpy as np
import time
import requests
import yfinance as yf
from datetime import date, timedelta, datetime
try:
    from zoneinfo import ZoneInfo
except ImportError:
    import pytz as tz
    ZoneInfo = lambda x: tz.timezone(x)
import json
import os

DB_NAME = "oi_data.db"
STATE_FILE = "dashboard_state.json"

# USER CONFIG:
TELEGRAM_BOT_TOKEN = "8779660104:AAG3sAE2d7jGQvfZtODfZSeb3tLNcEDwXLc"
TELEGRAM_CHAT_ID = "1214613107" # User's chat ID

def send_telegram(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage?chat_id={TELEGRAM_CHAT_ID}&text={message}"
        requests.get(url, timeout=10)
    except Exception as e:
        print(f"Telegram Error: {e}")

# -----------------------------------------------------------------------------
# Database Setup & Rolling Window Logic
# -----------------------------------------------------------------------------
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS historical_spurt (
            date TEXT,
            stock_name TEXT,
            spurt_pct REAL,
            PRIMARY KEY (date, stock_name)
        )
    ''')
    conn.commit()
    conn.close()

def maintain_rolling_window():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT date FROM historical_spurt ORDER BY date DESC")
    dates = cursor.fetchall()
    if len(dates) > 4:
        dates_to_keep = [d[0] for d in dates[:4]]
        placeholders = ','.join(['?'] * len(dates_to_keep))
        cursor.execute(f"DELETE FROM historical_spurt WHERE date NOT IN ({placeholders})", dates_to_keep)
        conn.commit()
    conn.close()

def save_eod_data(live_list: list):
    if not live_list: return
    live_df = pd.DataFrame([
        {'stock_name': x['symbol'], 'nse_spurt_pct': x.get('avgInOI', 0)}
        for x in live_list if x.get('symbol') not in ['NIFTY', 'BANKNIFTY', 'FINNIFTY']
    ])
    if live_df.empty: return
    today_str = date.today().strftime('%Y-%m-%d')
    conn = sqlite3.connect(DB_NAME)
    eod_df = live_df.rename(columns={'nse_spurt_pct': 'spurt_pct'})
    eod_df['date'] = today_str
    for _, row in eod_df.iterrows():
        cursor = conn.cursor()
        cursor.execute('SELECT count(*) FROM historical_spurt WHERE date=? AND stock_name=?', (today_str, row['stock_name']))
        if cursor.fetchone()[0] > 0:
            cursor.execute('UPDATE historical_spurt SET spurt_pct=? WHERE date=? AND stock_name=?', (row['spurt_pct'], today_str, row['stock_name']))
        else:
            df_insert = pd.DataFrame([row])
            df_insert.to_sql('historical_spurt', conn, if_exists='append', index=False)
    conn.commit()
    conn.close()
    maintain_rolling_window()

# -----------------------------------------------------------------------------
# Data Fetching
# -----------------------------------------------------------------------------
def get_real_nse_data():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.5',
    }
    s = requests.Session()
    s.headers.update(headers)
    try:
        s.get("https://www.nseindia.com", timeout=10)
        url = f"https://www.nseindia.com/api/live-analysis-oi-spurts-underlyings?v={int(time.time())}"
        r = s.get(url, timeout=10)
        if r.status_code == 200:
            return r.json().get("data", []), s
        return [], s
    except Exception as e:
        print(f"Exception fetching real data: {e}")
        return [], s

def get_sector_performance(session):
    url = f"https://www.nseindia.com/api/allIndices?v={int(time.time())}"
    try:
        r = session.get(url, timeout=10)
        if r.status_code == 200:
            data = r.json().get('data', [])
            sectors = ["NIFTY BANK", "NIFTY AUTO", "NIFTY FIN SERVICE", "NIFTY FMCG", "NIFTY IT", "NIFTY MEDIA", "NIFTY METAL", "NIFTY PHARMA", "NIFTY PSU BANK", "NIFTY REALTY"]
            sector_data = []
            for item in data:
                if item['index'] in sectors:
                    sector_data.append({
                        'Sector': item['index'].replace('NIFTY ', ''),
                        '% Change': item['percentChange']
                    })
            df = pd.DataFrame(sector_data)
            if not df.empty:
                df = df.sort_values(by='% Change', ascending=True)
            return df
    except Exception as e:
        print(f"Error fetching sectors: {e}")
    return pd.DataFrame()

def get_fo_gainers_losers(session):
    url = f"https://www.nseindia.com/api/live-analysis-variations?index=fno&v={int(time.time())}"
    try:
        r = session.get(url, timeout=10)
        if r.status_code == 200:
            data = r.json()
            gainers = pd.DataFrame(data.get('NIFTY', {}).get('gainers', []))
            losers = pd.DataFrame(data.get('NIFTY', {}).get('loosers', []))
            if not gainers.empty:
                gainers = gainers[['symbol', 'perChange']].rename(columns={'symbol': 'Stock', 'perChange': '% Change'})
                gainers['% Change'] = pd.to_numeric(gainers['% Change'], errors='coerce')
                gainers = gainers.sort_values(by='% Change', ascending=False).head(10)
            if not losers.empty:
                losers = losers[['symbol', 'perChange']].rename(columns={'symbol': 'Stock', 'perChange': '% Change'})
                losers['% Change'] = pd.to_numeric(losers['% Change'], errors='coerce')
                losers = losers.sort_values(by='% Change', ascending=True).head(10)
            return gainers, losers
    except Exception as e:
        print(f"Error fetching gainers/losers: {e}")
    return pd.DataFrame(), pd.DataFrame()

def get_pre_925_data(stocks):
    if not stocks: return {}
    tickers_str = " ".join([s + ".NS" for s in stocks])
    try:
        data = yf.download(tickers_str, interval='5m', period='1d', group_by='ticker', progress=False)
        res = {}
        for s in stocks:
            try:
                if len(stocks) == 1:
                    df = data
                else:
                    df = data[s + '.NS']
                df = df.dropna()
                df_early = df.between_time('09:15', '09:24')
                if not df_early.empty:
                    early_high = df_early['High'].max()
                    early_low = df_early['Low'].min()
                    res[s] = {'early_high': early_high, 'early_low': early_low}
            except Exception:
                pass
        return res
    except Exception as e:
        print(f"yfinance pre_925 error: {e}")
        return {}

def get_pdh_pdl(stocks):
    if not stocks: return {}
    tickers_str = " ".join([s + ".NS" for s in stocks])
    try:
        data = yf.download(tickers_str, period="2d", interval="1d", group_by='ticker', progress=False)
        res = {}
        for s in stocks:
            try:
                if len(stocks) == 1:
                    df = data
                else:
                    df = data[s + '.NS']
                df = df.dropna()
                if len(df) >= 2:
                    prev_day = df.iloc[-2]
                    res[s] = {'PDH': prev_day['High'], 'PDL': prev_day['Low']}
            except Exception:
                pass
        return res
    except Exception as e:
        print(f"yfinance PDH/PDL error: {e}")
        return {}

def process_scanner_data(live_list):
    conn = sqlite3.connect(DB_NAME)
    hist_df = pd.read_sql("SELECT * FROM historical_spurt", conn)
    conn.close()
    if hist_df.empty:
        return pd.DataFrame(), pd.DataFrame()
    hist_pivot = hist_df.pivot(index='stock_name', columns='date', values='spurt_pct').reset_index()
    date_cols = sorted([c for c in hist_pivot.columns if c != 'stock_name'])
    if not date_cols:
        return pd.DataFrame(), pd.DataFrame()
    col_mapping = {}
    today_str = date.today().strftime('%Y-%m-%d')
    for d in date_cols:
        if d == today_str:
            col_mapping[d] = 'Today'
        else:
            diff_days = np.busday_count(d, today_str)
            col_mapping[d] = f"D-{diff_days}"
    hist_pivot.rename(columns=col_mapping, inplace=True)
    required_cols = ['D-3', 'D-2', 'D-1', 'Today']
    for c in required_cols:
        if c not in hist_pivot.columns:
            hist_pivot[c] = np.nan
    all_data = hist_pivot[['stock_name'] + required_cols].copy()
    all_data.rename(columns={'stock_name': 'Stock'}, inplace=True)
    live_ltp_map = {x['symbol']: x.get('underlyingValue', 0) for x in live_list}
    all_data['LTP'] = all_data['Stock'].map(live_ltp_map)
    all_data['Avg'] = all_data[required_cols].mean(axis=1, skipna=True)
    top_6 = all_data.sort_values(by='Avg', ascending=False).head(6)
    return top_6, all_data

def is_market_open():
    now = datetime.now(ZoneInfo("Asia/Kolkata"))
    if now.weekday() >= 5: return False
    start_time = datetime.strptime("09:15", "%H:%M").time()
    end_time = datetime.strptime("15:30", "%H:%M").time()
    if not (start_time <= now.time() <= end_time): return False
    return True

def run_engine():
    print("Starting F&O Scanner Engine...")
    init_db()
    
    prev_top_10 = set()
    prev_ltps = {}
    active_breakouts = {}
    prev_brk = set()
    notification_history = []
    
    while True:
        if not is_market_open():
            print(f"[{datetime.now(ZoneInfo('Asia/Kolkata'))}] Market closed. Sleeping for 5 minutes...")
            time.sleep(300)
            continue
            
        print(f"[{datetime.now(ZoneInfo('Asia/Kolkata'))}] Fetching data...")
        try:
            live_data, session = get_real_nse_data()
            if not live_data:
                time.sleep(60)
                continue
                
            sector_df = get_sector_performance(session)
            gainers_df, losers_df = get_fo_gainers_losers(session)
            
            save_eod_data(live_data)
            top_6_data, all_stocks_data = process_scanner_data(live_data)
            
            t_today = pd.DataFrame()
            breakout_res = []
            
            if not all_stocks_data.empty:
                t_today = all_stocks_data.sort_values(by='Today', ascending=False).head(10)
                current_top_10 = set(t_today['Stock'].tolist())
                
                if prev_top_10:
                    new_entries = current_top_10 - prev_top_10
                    if new_entries:
                        stocks_str = ", ".join(new_entries)
                        msg = f"🚀 New in Today's Top 10: {stocks_str}"
                        send_telegram(msg)
                        notification_history.append(f"[{datetime.now(ZoneInfo('Asia/Kolkata')).strftime('%H:%M:%S')}] {msg}")
                prev_top_10 = current_top_10
                
                current_time = datetime.now(ZoneInfo('Asia/Kolkata')).time()
                start_time = datetime.strptime("09:25", "%H:%M").time()
                scanner_active = current_time >= start_time
                
                if scanner_active:
                    top_10_stocks = t_today['Stock'].tolist()
                    pdh_pdl_data = get_pdh_pdl(top_10_stocks)
                    
                    for _, row in t_today.iterrows():
                        stock = row['Stock']
                        ltp = float(row['LTP'])
                        if stock in pdh_pdl_data:
                            pdh = float(pdh_pdl_data[stock]['PDH'])
                            pdl = float(pdh_pdl_data[stock]['PDL'])
                            prev_ltp = prev_ltps.get(stock, ltp)
                            
                            if stock not in active_breakouts:
                                if ltp > pdh and prev_ltp <= pdh:
                                    active_breakouts[stock] = {'Status': "🔥 PDH Breakout (Bullish)", 'Time': current_time.strftime('%H:%M:%S')}
                                elif ltp < pdl and prev_ltp >= pdl:
                                    active_breakouts[stock] = {'Status': "🩸 PDL Breakout (Bearish)", 'Time': current_time.strftime('%H:%M:%S')}
                            else:
                                active = active_breakouts[stock]
                                if "Bullish" in active['Status'] and ltp <= pdh:
                                    del active_breakouts[stock]
                                elif "Bearish" in active['Status'] and ltp >= pdl:
                                    del active_breakouts[stock]
                            
                            prev_ltps[stock] = ltp
                            
                            if stock in active_breakouts:
                                b_data = active_breakouts[stock]
                                breakout_res.append({
                                    'Time': b_data['Time'], 'Stock': stock, 'LTP': ltp, 'PDH': pdh, 'PDL': pdl, 'Status': b_data['Status']
                                })
                                
                    current_brk = set([b['Stock'] for b in breakout_res])
                    if prev_brk:
                        new_brk = current_brk - prev_brk
                        if new_brk:
                            stocks_str = ", ".join(new_brk)
                            msg = f"🔥 NEW BREAKOUT ALERT: {stocks_str} crossed PDH/PDL!"
                            send_telegram(msg)
                            notification_history.append(f"[{datetime.now(ZoneInfo('Asia/Kolkata')).strftime('%H:%M:%S')}] {msg}")
                    prev_brk = current_brk
                    
            state = {
                'timestamp': datetime.now(ZoneInfo('Asia/Kolkata')).strftime('%H:%M:%S'),
                'sector_df': sector_df.to_dict('records') if not sector_df.empty else [],
                'gainers_df': gainers_df.to_dict('records') if not gainers_df.empty else [],
                'losers_df': losers_df.to_dict('records') if not losers_df.empty else [],
                'top_6_data': top_6_data.to_dict('records') if not top_6_data.empty else [],
                'all_stocks_data': all_stocks_data.to_dict('records') if not all_stocks_data.empty else [],
                'breakout_res': breakout_res,
                'notification_history': notification_history[-50:]
            }
            with open(STATE_FILE, 'w') as f:
                json.dump(state, f)
                
        except Exception as e:
            print(f"Engine Loop Error: {e}")
            
        time.sleep(60)

if __name__ == "__main__":
    run_engine()
