import requests
import pandas as pd


def fetch_korea_flights():
    url = "https://opensky-network.org/api/states/all"

    # 한반도 상공 범위
    # 위도 33~39, 경도 124~132
    params = {
        "lamin": 33.0,
        "lomin": 124.0,
        "lamax": 39.0,
        "lomax": 132.0
    }

    columns = [
        "icao24", "callsign", "origin_country", "time_position",
        "last_contact", "longitude", "latitude", "baro_altitude",
        "on_ground", "velocity", "true_track", "vertical_rate",
        "sensors", "geo_altitude", "squawk", "spi", "position_source"
    ]

    try:
        response = requests.get(url, params=params, timeout=20)
        response.raise_for_status()

        data = response.json()

        if data.get("states") is None:
            print("현재 지정된 한반도 상공에 조회되는 비행기가 없습니다.")
            return pd.DataFrame(columns=columns)

        df = pd.DataFrame(data["states"], columns=columns)

        df["callsign"] = df["callsign"].fillna("").astype(str).str.strip()

        return df

    except requests.exceptions.RequestException as e:
        print(f"API 요청 중 에러가 발생했습니다: {e}")
        return None


if __name__ == "__main__":
    korea_flights_df = fetch_korea_flights()

    if korea_flights_df is not None and not korea_flights_df.empty:
        print(f"총 {len(korea_flights_df)}대의 비행기 데이터를 성공적으로 가져왔습니다.\n")
        print(korea_flights_df.head())

        korea_flights_df.to_csv(
            "opensky_korea_sample.csv",
            index=False,
            encoding="utf-8-sig"
        )

        print("\nCSV 저장 완료: opensky_korea_sample.csv")

    elif korea_flights_df is not None:
        print("조회된 데이터가 없습니다.")
