import streamlit as st
import yfinance as yf
import pandas as pd

# 網頁設定
st.set_page_config(page_title="台股飆股雷達-精準量能版", layout="wide")
st.title("🏹 台股全自動飆股雷達 (1000張量能過濾 + 產業精確版)")
st.markdown("當前邏輯：**均線糾結 + 帶量(>1000張)突破 + 乖離率低於 3.5% (不追高)**")

# 1. 產生全台股掃描池 (優化區間，涵蓋更多熱門標的)
@st.cache_data
def get_extended_stock_list():
    ranges = [
        range(1101, 1105), # 水泥
        range(1501, 1599), # 重電、電機
        range(2301, 2499), # 電子權值、半導體、IC設計
        range(2601, 2618), # 航運
        range(2801, 2897), # 金融
        range(3001, 3715), # 電子零組件、光電、封測
        range(4901, 5000), # 通訊、IC設計
        range(6101, 6806), # 櫃買中小型、綠能
        range(8001, 8473), # 櫃買半導體、生技
    ]
    full_list = []
    for r in ranges:
        for i in r:
            full_list.append(f"{i}.TW")
    return full_list

# 2. 優化後的產業類別判斷邏輯 (更細緻的分類)
def get_industry_v2(ticker):
    code = int(ticker.split(".")[0])
    # 特殊權值與熱門股直接判定
    if code == 2330: return "半導體-晶圓代工"
    if code == 2317: return "電子代工-鴻海家族"
    if code in [2454, 3034, 3035, 3661]: return "IC設計-高價族群"
    if code in [1513, 1514, 1519, 6806]: return "重電/綠能/儲能"
    
    # 區間判定
    if 1101 <= code <= 1110: return "傳統-水泥工業"
    if 1501 <= code <= 1599: return "電機/機械/重電"
    if 2301 <= code <= 2329: return "電腦/周邊設備"
    if 2330 <= code <= 2454: return "半導體/IC設計"
    if 2601 <= code <= 2637: return "航運/航空/貨運"
    if 2801 <= code <= 2892: return "金融/金控/保險"
    if 3001 <= code <= 3100: return "光學/電子零組件"
    if 4901 <= code <= 4968: return "通訊網路/IC設計"
    if 6101 <= code <= 6299: return "櫃買-電子中小型"
    if 8001 <= code <= 8299: return "櫃買-半導體/電子"
    return "其他/傳產/生技"

def scan_breakout_v2():
    all_tickers = get_extended_stock_list()
    # 批次下載
    data = yf.download(all_tickers, period="60d", group_by='ticker', progress=False)
    
    results = []
    progress_bar = st.progress(0)
    
    for i, ticker in enumerate(all_tickers):
        try:
            df = data[ticker].dropna()
            if len(df) < 20: continue
            
            close = df['Close']
            curr_price = close.iloc[-1]
            curr_vol = df['Volume'].iloc[-1]
            
            # --- 過濾條件 1: 單日成交量至少 1000 張 ---
            # Yahoo Finance 的量是單位，台股 1 張 = 1000 股
            if curr_vol < 1000000: continue 
            
            # --- 核心邏輯計算 ---
            ma5 = close.rolling(5).mean().iloc[-1]
            ma10 = close.rolling(10).mean().iloc[-1]
            ma20 = close.rolling(20).mean().iloc[-1]
            
            # 1. 均線糾結 (5, 10, 20MA 差距 < 3%)
            ma_list = [ma5, ma10, ma20]
            squeeze_ratio = (max(ma_list) - min(ma_list)) / min(ma_list)
            
            # 2. 突破確認 (站上所有均線)
            is_breakout = curr_price > max(ma_list)
            
            # 3. 量能確認 (今日量 > 5日均量 1.5倍)
            vol_ma5 = df['Volume'].rolling(5).mean().iloc[-1]
            vol_ratio = curr_vol / vol_ma5
            
            # 4. 關鍵防追高 (乖離率 < 3.5%)
            bias_5ma = (curr_price - ma5) / ma5
            is_not_too_high = bias_5ma < 0.035 
            
            # 綜合過濾
            if is_breakout and squeeze_ratio < 0.03 and is_not_too_high and vol_ratio > 1.5:
                stock_id = ticker.replace(".TW", "")
                results.append({
                    "代碼連結": f"https://tw.stock.yahoo.com/quote/{stock_id}.TW",
                    "代號": stock_id,
                    "產業": get_industry_v2(ticker),
                    "價格": round(curr_price, 2),
                    "成交量(張)": int(curr_vol / 1000),
                    "糾結度": f"{round(squeeze_ratio * 100, 2)}%",
                    "量能倍數": round(vol_ratio, 2),
                    "策略建議": "量大且剛起漲"
                })
        except:
            continue
        progress_bar.progress((i + 1) / len(all_tickers))
        
    return sorted(results, key=lambda x: x['成交量(張)'], reverse=True)[:20]

# --- UI 顯示 ---
if st.button("🚀 啟動全台股精準掃描 (1000張 + 產業優化)"):
    with st.spinner('正在分析市場大數據...'):
        top_picks = scan_breakout_v2()
        
        if top_picks:
            st.success(f"🎉 掃描完成！符合量大、糾結且剛突破的標的：")
            res_df = pd.DataFrame(top_picks)
            
            st.dataframe(
                res_df,
                column_config={
                    "代碼連結": st.column_config.LinkColumn("即時 K 線圖", display_text="📈 Yahoo"),
                },
                hide_index=True,
                use_container_width=True
            )
        else:
            st.warning("目前市場無符合「量大且剛起漲」的標的。")
