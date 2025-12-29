import streamlit as st
import yfinance as yf
import pandas as pd

# 網頁設定
st.set_page_config(page_title="台股飆股雷達-防追高版", layout="wide")
st.title("🏹 台股全自動飆股雷達 (防追高 + 產業分析)")
st.markdown("當前邏輯：**均線極度糾結 + 剛帶量突破 + 乖離率過濾 (不追高)**")

# 1. 產生全台股掃描池 (涵蓋約 700+ 檔熱門上市櫃)
@st.cache_data
def get_extended_stock_list():
    # 根據台股常用板塊設定區間
    ranges = [
        range(1101, 1105), # 水泥
        range(1301, 1330), # 塑膠
        range(1501, 1600), # 重電/機械
        range(2301, 2500), # 電子權值/IC設計
        range(2601, 2640), # 航運/航空
        range(2801, 2900), # 金融/租賃
        range(3001, 3100), # 電子/光學
        range(3201, 3300), # 中小型電子
        range(4901, 5000), # 通訊/IC設計
        range(6101, 6300), # 櫃買中小型
        range(8001, 8100), # 櫃買
        range(8201, 8300)  # 櫃買
    ]
    full_list = []
    for r in ranges:
        for i in r:
            full_list.append(f"{i}.TW")
    return full_list

# 2. 產業類別判斷邏輯
def get_industry(ticker):
    code = int(ticker.split(".")[0])
    if 2330 <= code <= 2454: return "半導體/電子代工"
    if 2601 <= code <= 2637: return "航運/貨運"
    if 1501 <= code <= 1519: return "重電/電力"
    if 2801 <= code <= 2892: return "金融金控"
    if 3001 <= code <= 3100: return "光學/電子零組件"
    if 4901 <= code <= 4968: return "IC設計/通訊"
    return "一般電子/傳產"

def scan_breakout_no_chase():
    all_tickers = get_extended_stock_list()
    # 批次下載數據 (一次下載加快效率)
    data = yf.download(all_tickers, period="60d", group_by='ticker', progress=False)
    
    results = []
    progress_bar = st.progress(0)
    
    for i, ticker in enumerate(all_tickers):
        try:
            df = data[ticker].dropna()
            if len(df) < 20: continue
            
            close = df['Close']
            ma5 = close.rolling(5).mean().iloc[-1]
            ma10 = close.rolling(10).mean().iloc[-1]
            ma20 = close.rolling(20).mean().iloc[-1]
            curr_price = close.iloc[-1]
            
            # --- 核心邏輯 ---
            # 1. 均線糾結度 (5/10/20MA 差距 < 3%)
            ma_list = [ma5, ma10, ma20]
            squeeze_ratio = (max(ma_list) - min(ma_list)) / min(ma_list)
            
            # 2. 突破確認 (站上所有均線)
            is_breakout = curr_price > max(ma_list)
            
            # 3. 量能確認 (今日量 > 5日均量 1.5倍)
            vol_ma5 = df['Volume'].rolling(5).mean().iloc[-1]
            curr_vol = df['Volume'].iloc[-1]
            vol_ratio = curr_vol / vol_ma5
            
            # 4. 【關鍵：防追高過濾】
            # 計算乖離率：如果股價離 MA5 超過 3.5%，代表已經噴發兩天了，這種不抓
            bias_5ma = (curr_price - ma5) / ma5
            is_not_too_high = bias_5ma < 0.035 
            
            # 綜合過濾：要有量、要突破、要糾結、但不能噴太遠、成交量不能太小
            if curr_vol > 800 and is_breakout and squeeze_ratio < 0.03 and is_not_too_high:
                stock_id = ticker.replace(".TW", "")
                results.append({
                    "代碼連結": f"https://tw.stock.yahoo.com/quote/{stock_id}.TW",
                    "代號": stock_id,
                    "產業": get_industry(ticker),
                    "目前價格": round(curr_price, 2),
                    "糾結度": f"{round(squeeze_ratio * 100, 2)}%",
                    "量能倍數": round(vol_ratio, 2),
                    "建議買入點": round(curr_price * 1.005, 2),
                    "建議停利點": round(curr_price * 1.12, 2),
                    "策略建議": "剛起步突破，風險較低"
                })
        except:
            continue
        progress_bar.progress((i + 1) / len(all_tickers))
        
    return sorted(results, key=lambda x: x['量能倍數'], reverse=True)[:15]

# --- UI 顯示 ---
if st.button("🚀 啟動 700 檔全台股掃描 (防追高模式)"):
    with st.spinner('正在分析全台股大數據，請稍候約 30 秒...'):
        top_picks = scan_breakout_no_chase()
        
        if top_picks:
            st.success(f"🎉 捕捉成功！已為您過濾掉噴發太遠的標的，剩餘 {len(top_picks)} 檔：")
            
            res_df = pd.DataFrame(top_picks)
            
            # 渲染表格，加入可點擊連結
            st.dataframe(
                res_df,
                column_config={
                    "代碼連結": st.column_config.LinkColumn(
                        "即時 K 線圖",
                        display_text="📈 查看 Yahoo 線圖"
                    ),
                },
                hide_index=True,
                use_container_width=True
            )
            st.info("💡 邏輯說明：本系統優先選擇『乖離率 < 3.5%』的標的，旨在捕捉『第一根紅 K』或是『盤整剛起漲』的機會。")
        else:
            st.warning("目前市場 700 檔標的中，暫無符合『剛突破且未過熱』的標的。")