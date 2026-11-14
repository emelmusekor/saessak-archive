import pandas as pd
import folium


CSV_PATH = "opensky_korea_sample.csv"
OUTPUT_HTML = "korea_flight_map.html"


def create_flight_map(df):
    if df.empty:
        print("시각화할 데이터가 없습니다.")
        return None

    # 한반도 중심 좌표
    m = folium.Map(
        location=[36.0, 128.0],
        zoom_start=7,
        tiles="CartoDB positron"
    )

    for _, row in df.iterrows():
        lat = row.get("latitude")
        lon = row.get("longitude")

        if pd.isna(lat) or pd.isna(lon):
            continue

        callsign = row.get("callsign", "")
        if pd.isna(callsign) or str(callsign).strip() == "":
            callsign = "Unknown"
        else:
            callsign = str(callsign).strip()

        origin_country = row.get("origin_country", "Unknown")
        altitude = row.get("baro_altitude", "N/A")
        velocity = row.get("velocity", "N/A")
        vertical_rate = row.get("vertical_rate", "N/A")

        popup_html = f"""
        <div style="width: 230px;">
            <b>항공편명:</b> {callsign}<br>
            <b>국적:</b> {origin_country}<br>
            <b>기압 고도:</b> {altitude} m<br>
            <b>속도:</b> {velocity} m/s<br>
            <b>수직 승강률:</b> {vertical_rate} m/s
        </div>
        """

        folium.Marker(
            location=[lat, lon],
            tooltip=f"{callsign} 상세 정보",
            popup=folium.Popup(popup_html, max_width=260),
            icon=folium.Icon(icon="plane", prefix="fa", color="blue")
        ).add_to(m)

    return m


if __name__ == "__main__":
    df = pd.read_csv(CSV_PATH)

    flight_map = create_flight_map(df)

    if flight_map is not None:
        flight_map.save(OUTPUT_HTML)
        print(f"지도 저장 완료: {OUTPUT_HTML}")
        print("파일을 더블클릭하면 브라우저에서 지도를 볼 수 있습니다.")
