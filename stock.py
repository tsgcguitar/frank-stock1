import streamlit as st
import yfinance as yf
import pandas as pd
import datetime

# 1. 網頁基礎設定
st.set_page_config(page_title="台股飆股雷達-專業訂閱版", layout="wide")
st.title("🏹 台股全自動飆股雷達 (專業版)")
st.markdown("""
當前邏輯：**均線極度糾結 + 單日量能 > 1000張 + 剛帶量突破 + 低乖離防追高**
""")

# 2. 產生全台股掃描池
@st.cache_data
def get_extended_stock_list():
    # 涵蓋台股多數具備流動性的代碼區間
    ranges = [
        range(1101, 1110), # 水泥
        range(1301, 1330), # 塑膠
        range(1501, 1600), # 重電/機械/電機
        range(2301, 2499), # 電子權值/IC設計/半導體
        range(2601, 2640), # 航運/航空
        range(2801, 2900), # 金融金控
        range(3001, 3100), # 電子零組件
        range(3201, 3700), # 中小型電子/封測
        range(4901, 5000), # 通訊/IC設計
        range(6101, 6299), # 櫃買中小型
        range(8001, 8299), # 櫃買半導體
        range(8901, 8940)  # 其他
    ]
    full_list = []
    for r in ranges:
        for i in r:
            full_list.append(f"{i}.TW")
    return full_list

# 3. 優化產業類別判斷
def get_industry_v2(ticker):
    try:
        code = int(ticker.split(".")[0])
        # 個別龍頭精確判定
        if code == 2330: return "半導體-晶圓代工"
        if code == 2317: return "電子代工-鴻海"
        if code == 2454: return "IC設計-聯發科"
        if code in [1513, 1514, 1519, 6806]: return "綠能/重電/儲能"
        if code in [2603, 2609, 2615]: return "航運-貨櫃三雄"
        
        # 區間判定
        if 1101 <= code <= 1399: return "傳統/水泥/塑膠"
        if 1501 <= code <= 1799: return "電機/機電/化工"
        if 2301 <= code <= 2399: return "電腦周邊/電子代工"
        if 2401 <= code <= 2499: return "半導體/IC設計"
        if 2601 <= code <= 2699: return "航運/航空/物流"
        if 2801 <= code <= 2899: return "金融金控"
        if 3001 <= code <= 3599: return "光學/電子零組件"
        if 4901 <= code <= 4999: return "通信網路/IC設計"
        if 6101 <= code <= 8299: return "櫃買中小型電子"
        return "其他/生技/傳產"
    except:
        return "未知分類"

# 4. 核心掃描運算
def scan_breakout_pro():
    all_tickers = get_extended_stock_list()
    # 增加下載的天數以確保 MA 計算正確
    data = yf.download(all_tickers, period="60d", group_by='ticker', progress=False)
    
    results = []
    progress_bar = st.progress(0)
    
    for i, ticker in enumerate(all_tickers):
        try:
            # 取得該股數據並移除空值
            df = data[ticker].dropna()
            if len(df) < 20: continue
            
            close = df['Close']
            volume = df['Volume']
            curr_price = close.iloc[-1]
            curr_vol = volume.iloc[-1]
            
            # --- 條件 A: 單日成交量必須 > 1000張 (Yahoo 單位為股) ---
            if curr_vol < 1000000: continue
            
            # --- 條件 B: 均線計算 ---
            ma5 = close.rolling(5).mean().iloc[-1]
            ma10 = close.rolling(10).mean().iloc[-1]
            ma20 = close.rolling(20).mean().iloc[-1]
            ma_list = [ma5, ma10, ma20]
            
            # --- 條件 C: 糾結度計算 (5,10,20MA 離散度 < 3%) ---
            squeeze_ratio = (max(ma_list) - min(ma_list)) / min(ma_list)
            
            # --- 條件 D: 帶量確認 (今日量 > 5日均量 1.5倍) ---
            vol_ma5 = volume.rolling(5).mean().iloc[-1]
            vol_ratio = curr_vol / vol_ma5
            
            # --- 條件 E: 突破位階與乖離過濾 (防追高) ---
            is_breakout = curr_price > max(ma_list)
            bias_5ma = (curr_price - ma5) / ma5
            is_not_too_high = bias_5ma < 0.035 # 乖離超過3.5%就不追
            
            # --- 符合所有初步條件後的策略判定 ---
            if is_breakout and squeeze_ratio < 0.03 and is_not_too_high and vol_ratio > 1.2:
                
                # 策略建議邏輯
                strategy = ""
                if vol_ratio > 3.0:
                    strategy = "🔥 爆量大突破：市場焦點，留意延續性"
                elif squeeze_ratio < 0.015:
                    strategy = "💎 極致糾結：盤整極久，噴發潛力高"
                elif curr_price > ma20 and close.iloc[-2] <= ma20:
                    strategy = "🔄 轉強訊號：跌深反彈站上月線"
                else:
                    strategy = "✅ 安全起漲：風險收益比佳"

                stock_id = ticker.replace(".TW", "")
                results.append({
                    "代碼": stock_id,
                    "產業": get_industry_v2(ticker),
                    "目前價格": round(curr_price, 2),
                    "漲跌幅": f"{round(((curr_price/close.iloc[-2])-1)*100, 2)}%",
                    "成交量(張)": int(curr_vol / 1000),
                    "量能倍數": round(vol_ratio, 2),
                    "均線糾結": f"{round(squeeze_ratio * 100, 2)}%",
                    "策略建議": strategy,
                    "建議停損點": round(min(ma_list), 2),
                    "連結": f"https://tw.stock.yahoo.com/quote/{stock_id}.TW"
                })
        except:
            continue
        
        # 更新進度條
        progress_bar.progress((i + 1) / len(all_tickers))
        
    # 回傳結果，以量能倍數排序取前 20 檔
    return sorted(results, key=lambda x: x['量能倍數'], reverse=True)[:20]

# 5. UI 介面設計
if st.button("🚀 執行全台股專業掃描"):
    with st.spinner('正在分析 700+ 檔標的，請稍候...'):
        top_picks = scan_breakout_pro()
        
        if top_picks:
            st.success(f"🎉 捕捉成功！目前市場共有 {len(top_picks)} 檔符合「防追高起漲」標的")
            
            df_final = pd.DataFrame(top_picks)
            
            # 使用 LinkColumn 讓連結變好看
            st.dataframe(
                df_final,
                column_config={
                    "連結": st.column_config.LinkColumn("查看線圖", display_text="📈 Yahoo Finance"),
                    "目前價格": st.column_config.NumberColumn(format="$%.2f"),
                    "成交量(張)": st.column_config.NumberColumn(format="%d 張"),
                },
                hide_index=True,
                use_container_width=True
            )
            
            st.info("""
            **📢 操作小提醒：**
            1. **停損建議**：若收盤價跌破『建議停損點』(通常為均線群底端)，應果斷執行紀律。
            2. **量能門檻**：系統已過濾單日成交量小於 1000 張的冷門股，降低被操控風險。
            3. **產業連動**：若發現同一產業有多檔同時上榜，該族群為當日強勢主流。
            """)
        else:
            st.warning("當前盤勢較弱，暫無符合『帶量起漲』且『乖離尚小』的標的。")

# 側邊欄說明
with st.sidebar:
    st.header("關於此工具")
    st.write("這是一款專為**不喜歡追高**的投資者設計的雷達。")
    st.divider()
    st.write("**版本：** 專業訂閱版 v2.0")
    st.write("**核心邏輯：**")
    st.write("- 均線糾結度 < 3%")
    st.write("- 成交量 > 1000 張")
    st.write("- 5日乖離率 < 3.5%")
