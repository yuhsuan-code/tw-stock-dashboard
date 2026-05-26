
import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="外資＋投信同步買超", layout="wide")
st.title("📈 外資＋投信同步買超儀表板")

@st.cache_data(ttl=3600)
def get_twse_t86(date_str):
    url = f"https://www.twse.com.tw/rwd/zh/fund/T86?date={date_str}&selectType=ALLBUT0999&response=json"
    r = requests.get(url, timeout=20)
    data = r.json()

    if "data" not in data or not data["data"]:
        return None

    cols = data["fields"]
    df = pd.DataFrame(data["data"], columns=cols)

    stock_col = [c for c in cols if "證券代號" in c][0]
    name_col = [c for c in cols if "證券名稱" in c][0]
    foreign_col = next((c for c in cols if "外資及陸資買賣超股數" in c or "外陸資買賣超股數" in c), None)
    trust_col = next((c for c in cols if "投信買賣超股數" in c), None)

    if foreign_col is None or trust_col is None:
        return None

    df = df[[stock_col, name_col, foreign_col, trust_col]].copy()
    df.columns = ["股票代號","股票名稱","外資","投信"]

    for c in ["外資","投信"]:
        df[c] = df[c].astype(str).str.replace(",", "", regex=False).astype(int)

    df["外資方向"] = df["外資"].apply(lambda x: "買超" if x > 0 else ("賣超" if x < 0 else "中立"))
    df["投信方向"] = df["投信"].apply(lambda x: "買超" if x > 0 else ("賣超" if x < 0 else "中立"))
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

foreign_pivot = combined.pivot_table(
    index=["股票代號","股票名稱"],
    columns="日期",
    values="外資方向",
    aggfunc="first"
)

trust_pivot = combined.pivot_table(
    index=["股票代號","股票名稱"],
    columns="日期",
    values="投信方向",
    aggfunc="first"
)

sync_buy = foreign_pivot[
    (foreign_pivot == "買超").all(axis=1) &
    (trust_pivot == "買超").all(axis=1)
].reset_index()

st.metric("🔥 外資＋投信連3日同步買超", len(sync_buy))
st.subheader("同步連3日買超股票")
st.dataframe(sync_buy, use_container_width=True)
st.caption("資料來源：TWSE")
