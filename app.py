import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import numpy as np
from pathlib import Path
from datetime import date, timedelta

DATA_FILE = Path(__file__).parent / "merged_sales.xlsx"

# --- 페이지 설정 ---
st.set_page_config(page_title="매출 대시보드", layout="wide")
st.title("매출 대시보드")

# --- 데이터 로드 (파일 없으면 더미 자동 생성) ---
@st.cache_data
def load_data(path: Path) -> tuple[pd.DataFrame, bool]:
    if path.exists():
        df = pd.read_excel(path)
        df["날짜"] = pd.to_datetime(df["날짜"])
        df["금액"] = pd.to_numeric(df["금액"], errors="coerce").fillna(0).astype(int)
        return df, False

    # 더미 데이터 생성
    rng = np.random.default_rng(42)
    start = date(2024, 1, 1)
    rows = [
        {
            "날짜": pd.Timestamp(start + timedelta(days=int(rng.integers(0, 180)))),
            "지점": rng.choice(["A", "B"]),
            "상품": rng.choice(["노트북", "스마트폰", "태블릿"]),
            "금액": int(rng.integers(200_000, 2_000_000)),
        }
        for _ in range(180)
    ]
    return pd.DataFrame(rows), True

df, is_dummy = load_data(DATA_FILE)

if is_dummy:
    st.info("merged_sales.xlsx 파일을 찾을 수 없어 더미 데이터로 표시 중입니다.")

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
