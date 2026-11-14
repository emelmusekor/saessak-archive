# 디지털새싹 아카이브

(사)한국인공지능교육학회가 개발·운영한 2023~2026 디지털새싹 프로그램을 연도별로 정리하고, 수업용 웹 활동지를 바로 체험할 수 있게 만든 정적 사이트입니다.

사이트: https://emelmusekor.github.io/saessak-archive/

## 폴더 구조

```
docs/                    공개되는 사이트 (GitHub Pages가 이 폴더를 배포)
  index.html             홈: 메인 영상, 프로그램, 선생님, 연도별 프로그램, 수업 자료, 참여 후기
  2026.html, 2025.html   연도별 프로그램 페이지 (tools/make_year_pages.py로 생성, assets/programs.js가 data/programs-YYYY.js를 읽어 그림)
  library.html           자료실 (data/materials.js가 있으면 연도·프로그램별 자료 목록이 열림)
  try.html               웹 활동지 모음 + 프로그램별 수업 도구 링크
  try/*.html             Make! 클래스 마켓 웹 활동지 7개, Insight! 실시간 항공 지도(try/flight-map.html)
  data/programs-YYYY.js  연도별 프로그램 내용 (한 줄 소개, 설명, 3단계, 학생 결과물, 참여 인원)
  data/schools-YYYY.js   연도별 참여 학교 (있을 때만 페이지 아래 참여 학교 영역이 열림)
  assets/site.css        사이트 공통 디자인 (한국인공지능교육학회 홈페이지 톤: 네이비·블루·청록, Noto Sans KR)
  assets/site.js         머리글 메뉴, 연도 탭
  assets/activity.css    활동지 공통 디자인
  assets/img, video      홍보 영상 장면, 학회 로고, 활동지 썸네일
tools/build_activities.py  원본 활동지 HTML을 사이트 디자인으로 다시 만드는 스크립트
tools/fetch_logos.py       학교명 → 나이스 학교정보 → 학교 누리집에서 교표를 찾아 PNG로 저장
tools/make_schools_js.py   참여 학교 자료(private/) + 교표 → docs/data/schools-YYYY.js
private/                   내부 원자료 (git에 올리지 않음)
```

## 자료 출처

- 사진·메인 영상: 한국인공지능교육학회 디지털새싹 홍보 영상에서 발췌 (로고·자막 부분은 잘라 냄)
- 참여 후기: 2023~2025 결과보고서 참가자 후기에서 이름·학교명을 빼고 인용
- 언론 보도: 머니투데이 등 기사 원문 확인 후 링크
- 2026 참여 학교: 운영기관이 정리한 결과보고용 수업 사진 폴더(학교별). 교표는 각 학교 누리집에서 가져옴
- 2026 참여 인원: 프로그램별 목표 인원(전 프로그램 목표 달성)
- 연도별 참여 인원·수료율·만족도: 2023년 상·하반기, 2024년, 2025년 디지털새싹 사업 결과보고서
- 2026 프로그램 소개·차시·하위역량: 2026년도 디지털새싹 사업 운영 프로그램 제안서(새싹B 일반형)
- 참여 학생 22,170명은 2023 상반기 3,097 + 하반기 6,284 + 2024년 5,952 + 2025년 6,837의 합(연인원)입니다.

## 고치는 방법

- **프로그램 내용 수정**: `docs/data/programs-YYYY.js`만 고치면 해당 연도 페이지에 반영됩니다.
- **연도 페이지 추가**: `tools/make_year_pages.py`의 YEARS·ALL_YEARS에 연도를 넣고 실행합니다.
- **활동지 원본이 바뀌었을 때**: 아래 명령으로 7개를 다시 만듭니다. 원본 문구가 바뀌어 바꿀 곳을 찾지 못하면 스크립트가 멈추고 알려 줍니다.
  ```
  python tools/build_activities.py "<원본 활동지 폴더>" docs/try
  ```
- 수정 후 `main` 브랜치에 push하면 1~2분 뒤 사이트에 반영됩니다.
