import pandas as pd
import numpy as np


CSV_PATH = "opensky_korea_sample.csv"


def load_flight_data(csv_path):
    df = pd.read_csv(csv_path)
    return df


def detect_anomaly_planes(df, threshold=-3.0):
    df = df.copy()

    # vertical_rate를 숫자로 변환
    df["vertical_rate"] = pd.to_numeric(df["vertical_rate"], errors="coerce")

    # on_ground가 문자열로 들어온 경우 처리
    if df["on_ground"].dtype == "object":
        df["on_ground"] = (
            df["on_ground"]
            .astype(str)
            .str.strip()
            .str.lower()
            .isin(["true", "1", "yes"])
        )

    # 비행 중인 항공기 + vertical_rate가 있는 항공기만 남김
    df_flying = df[
        (df["on_ground"] == False) &
        (df["vertical_rate"].notna())
    ].copy()

    if df_flying.empty:
        print("분석 가능한 비행 중 항공기 데이터가 없습니다.")
        return df_flying, pd.DataFrame()

    mean_vr = np.mean(df_flying["vertical_rate"])
    std_vr = np.std(df_flying["vertical_rate"])

    print(f"분석 대상 비행기 수: {len(df_flying)}대")
    print(f"수직 승강률 평균: {mean_vr:.2f} m/s")
    print(f"수직 승강률 표준편차: {std_vr:.2f}")

    if std_vr == 0:
        df_flying["z_score"] = 0.0
    else:
        df_flying["z_score"] = (
            df_flying["vertical_rate"] - mean_vr
        ) / std_vr

    danger_planes = df_flying[df_flying["z_score"] <= threshold].copy()

    return df_flying, danger_planes


if __name__ == "__main__":
    df = load_flight_data(CSV_PATH)

    # 실제 기준은 -3
    # 데이터 수가 너무 적어 위험 항공기가 안 나오면 수업 시연용으로 -2 사용 가능
    df_flying, danger_planes = detect_anomaly_planes(df, threshold=-3.0)

    print("\n위험 항공기 탐지 결과")
    print(f"위험 항공기 수: {len(danger_planes)}대")

    if danger_planes.empty:
        print("현재 기준에서는 위험 항공기가 탐지되지 않았습니다.")
    else:
        result_columns = [
            "callsign",
            "origin_country",
            "vertical_rate",
            "z_score",
            "latitude",
            "longitude"
        ]

        print(danger_planes[result_columns].to_string(index=False))

        danger_planes.to_csv(
            "danger_planes.csv",
            index=False,
            encoding="utf-8-sig"
        )

        print("\n위험 항공기 CSV 저장 완료: danger_planes.csv")
