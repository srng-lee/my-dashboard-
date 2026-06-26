import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from pathlib import Path
from datetime import date

DATA_FILE = Path(__file__).parent / "merged_sales.xlsx"

# --- 페이지 설정 ---
st.set_page_config(page_title="매출 대시보드", layout="wide")
st.title("매출 대시보드")

# --- 데이터 로드 ---
if not DATA_FILE.exists():
    st.error(
        "데이터 파일(merged_sales.xlsx)을 찾을 수 없습니다. "
        "app.py와 같은 폴더에 파일을 넣고 새로고침해 주세요."
    )
    st.stop()

@st.cache_data
def load_data(path: Path) -> pd.DataFrame:
    df = pd.read_excel(path)
    df["날짜"] = pd.to_datetime(df["날짜"])
    df["금액"] = pd.to_numeric(df["금액"], errors="coerce").fillna(0).astype(int)
    return df

df = load_data(DATA_FILE)

# --- 사이드바 필터 ---
st.sidebar.header("필터")
branches = sorted(df["지점"].unique().tolist())
selected_branches = st.sidebar.multiselect(
    "지점 선택",
    options=branches,
    default=branches,
)

if not selected_branches:
    st.warning("지점을 하나 이상 선택해 주세요.")
    st.stop()

filtered = df[df["지점"].isin(selected_branches)]

# --- 전체 매출 합계 ---
total = filtered["금액"].sum()
st.metric(label="전체 매출 합계", value=f"₩{total:,.0f}")

st.divider()

# --- 지점별 매출 막대그래프 ---
st.subheader("지점별 매출 합계")
branch_summary = (
    filtered.groupby("지점", as_index=False)["금액"]
    .sum()
    .rename(columns={"금액": "매출 합계"})
)
fig = px.bar(
    branch_summary,
    x="지점",
    y="매출 합계",
    color="지점",
    text_auto=True,
    color_discrete_map={"A": "#4C8BF5", "B": "#F5824C"},
)
fig.update_layout(showlegend=False, yaxis_tickformat=",")
fig.update_traces(texttemplate="₩%{y:,.0f}")
st.plotly_chart(fig, use_container_width=True)

st.divider()

# --- 상품별 매출 표 ---
st.subheader("상품별 매출")
product_summary = (
    filtered.groupby("상품", as_index=False)["금액"]
    .agg(["sum", "count", "mean"])
    .rename(columns={"sum": "매출 합계", "count": "판매 건수", "mean": "평균 단가"})
)
product_summary["매출 합계"] = product_summary["매출 합계"].map("₩{:,.0f}".format)
product_summary["평균 단가"] = product_summary["평균 단가"].map("₩{:,.0f}".format)
st.dataframe(product_summary, use_container_width=True, hide_index=True)

st.divider()

# --- 서울 날씨 (Open-Meteo) ---
st.subheader("서울 현재 날씨")

@st.cache_data(ttl=600)
def fetch_weather() -> dict | None:
    try:
        resp = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": 37.5665,
                "longitude": 126.9780,
                "current": "temperature_2m,weathercode",
                "hourly": "temperature_2m",
                "timezone": "Asia/Seoul",
                "forecast_days": 1,
            },
            timeout=5,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return None

weather = fetch_weather()

if weather is None:
    st.warning("날씨 데이터를 불러오지 못했습니다. 잠시 후 새로고침해 주세요.")
else:
    current_temp = weather["current"]["temperature_2m"]
    st.metric(label="현재 기온 (서울)", value=f"{current_temp} °C")

    # 오늘 시간별 기온 꺾은선 그래프
    today = date.today().isoformat()
    hourly = pd.DataFrame({
        "시각": pd.to_datetime(weather["hourly"]["time"]),
        "기온(°C)": weather["hourly"]["temperature_2m"],
    })
    hourly = hourly[hourly["시각"].dt.date.astype(str) == today]

    fig_w = px.line(
        hourly,
        x="시각",
        y="기온(°C)",
        markers=True,
        title="오늘 시간별 기온",
    )
    fig_w.update_layout(xaxis_title="시각", yaxis_title="기온 (°C)")
    st.plotly_chart(fig_w, use_container_width=True)
