
import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="台股投信3日追蹤儀表板", layout="wide")
st.title("📈 台股投信 3 日追蹤儀表板")

@st.cache_data(ttl=3600)
def get_twse_t86(date_str):
    url = f"https://www.twse.com.tw/rwd/zh/fund/T86?date={date_str}&selectType=ALLBUT0999&response=json"
    r = requests.get(url, timeout=20)
    data = r.json()

    if "data" not in data or not data["data"]:
        return None

    cols = data["fields"]
    df = pd.DataFrame(data["data"], columns=cols)

    stock_col = [c for c in df.columns if "證券代號" in c][0]
    name_col = [c for c in df.columns if "證券名稱" in c][0]

    buy_sell_col = None
    for c in df.columns:
        if "投信" in c and "買賣超" in c:
            buy_sell_col = c
            break

    if buy_sell_col is None:
        return None

    df = df[[stock_col, name_col, buy_sell_col]].copy()
    df.columns = ["股票代號", "股票名稱", "投信買賣超"]

    df["投信買賣超"] = (
        df["投信買賣超"]
        .astype(str)
        .str.replace(",", "", regex=False)
        .astype(int)
    )

    df["方向"] = df["投信買賣超"].apply(
        lambda x: "買超" if x > 0 else ("賣超" if x < 0 else "中立")
    )
    df["日期"] = date_str
    return df

dfs = []
today = datetime.today()

for i in range(10):
    d = (today - timedelta(days=i)).strftime("%Y%m%d")
    try:
        df = get_twse_t86(d)
        if df is not None:
            dfs.append(df)
    except:
        pass
    if len(dfs) >= 3:
        break

if len(dfs) < 3:
    st.error("抓不到足夠交易日資料")
    st.stop()

dfs = dfs[::-1]
combined = pd.concat(dfs)

pivot = combined.pivot_table(
    index=["股票代號", "股票名稱"],
    columns="日期",
    values="方向",
    aggfunc="first"
)

dates = list(pivot.columns)

repeat_buy = pivot[(pivot == "買超").all(axis=1)].reset_index()
repeat_sell = pivot[(pivot == "賣超").all(axis=1)].reset_index()

latest = dates[-1]
prev = dates[-2]

buy_to_sell = pivot[
    (pivot[prev] == "買超") & (pivot[latest] == "賣超")
].reset_index()

sell_to_buy = pivot[
    (pivot[prev] == "賣超") & (pivot[latest] == "買超")
].reset_index()

c1, c2, c3, c4 = st.columns(4)
c1.metric("連3日買超", len(repeat_buy))
c2.metric("連3日賣超", len(repeat_sell))
c3.metric("買→賣", len(buy_to_sell))
c4.metric("賣→買", len(sell_to_buy))

tab1, tab2, tab3, tab4 = st.tabs(
    ["🔥 連3日買超", "❄️ 連3日賣超", "↘️ 買轉賣", "↗️ 賣轉買"]
)

with tab1:
    st.dataframe(repeat_buy, use_container_width=True)

with tab2:
    st.dataframe(repeat_sell, use_container_width=True)

with tab3:
    st.dataframe(buy_to_sell, use_container_width=True)

with tab4:
    st.dataframe(sell_to_buy, use_container_width=True)

st.caption("資料來源：TWSE 公開資訊，更新依交易日資料而定")
