import pandas as pd

# store_a: 열 순서 = [날짜, 품목, 금액]
a = pd.read_excel("store_a.xlsx", header=0)
a.columns = ["날짜", "상품", "금액"]
a["지점"] = "A"

# store_b: 열 순서 = [거래일, 상품명, 매출(원)]
b = pd.read_excel("store_b.xlsx", header=0)
b.columns = ["날짜", "상품", "금액"]
b["지점"] = "B"

merged = pd.concat([a, b], ignore_index=True)

# 날짜 통일: YYYY-MM-DD 문자열 (혼재 형식 대응)
merged["날짜"] = pd.to_datetime(merged["날짜"], format="mixed").dt.strftime("%Y-%m-%d")

# 금액 숫자형 보장
merged["금액"] = pd.to_numeric(merged["금액"], errors="coerce").astype(int)

# 열 순서 정리 및 날짜 오름차순 정렬
merged = merged[["날짜", "지점", "상품", "금액"]].sort_values("날짜").reset_index(drop=True)

print(merged.to_string())
print()
print(f"총 {len(merged)}행")
print(merged["지점"].value_counts())

merged.to_excel("merged_sales.xlsx", index=False)
print("\nmerged_sales.xlsx 저장 완료")
