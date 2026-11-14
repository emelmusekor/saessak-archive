/* 2025 디지털새싹 프로그램
   출처: 2025년도 디지털새싹 사업 운영 프로그램 제안서(합본), 2025년 디지털새싹 운영 결과보고서(프로그램별 참여 인원) */
window.PROGRAM_YEAR = {
  year: 2025,
  seriesLabel: "나도 ○○!",
  facts: [["구성", "기본 5 · 특화 1"], ["대상", "초등학교 – 중학교"], ["학생", "6,837명"], ["수료율", "95.3%"]],
  programs: [
    {
      id: "security", label: "나도 보안전문가!", word: "보안전문가!", title: "도둑맞은 개인정보를 찾아서",
      track: "기본과정", levelLabel: "초등 저학년", literacy: "디지털 리터러시", sessions: 8, phases: [2, 2, 4], color: "#2E4D8F", participants: 1747,
      tagline: "클레이로 지은 집에 암호를 건다",
      intro: "그림책 속 이야기에서 개인정보가 무엇인지 찾고, 몸으로 명령어를 익히는 언플러그드 코딩과 모션 코딩으로 원리를 잡습니다. 마지막에는 클레이로 꾸민 집에 메이키메이키를 연결해 암호를 맞혀야 열리는 집을 만듭니다.",
      steps: ["이야기 속 개인정보 찾기, 몸으로 하는 코딩", "모션 코딩과 암호 규칙", "암호가 걸린 클레이 집, 보호 실천 다짐"],
      made: "암호화·복호화가 되는 나만의 클레이 집",
      icon: '<rect x="10" y="21" width="28" height="21" rx="3"/><path d="M16 21v-6a8 8 0 0 1 16 0v6"/><circle cx="24" cy="30" r="2.5"/><path d="M24 32.5V36"/>',
      links: [], activities: []
    },
    {
      id: "eco", label: "나도 환경운동가!", word: "환경운동가!", title: "AI 독도전문가의 강치 프로젝트",
      track: "기본과정", levelLabel: "초등학교", literacy: "컴퓨팅 사고력", sessions: 8, phases: [3, 3, 2], color: "#1588A6", participants: 1609,
      tagline: "독도 강치를 지키는 코딩 미션",
      intro: "독도와 그곳에 살던 강치 이야기에서 출발해, 환경운동가가 되어 섬을 지키는 문제를 풉니다. 언플러그드 활동으로 순서를 세우고 뚜루뚜루 로봇과 엔트리로 미션을 해결합니다.",
      steps: ["독도와 강치 이야기, 언플러그드 문제 해결", "뚜루뚜루 로봇 코딩 미션", "엔트리로 독도 지키기 프로젝트"],
      made: "독도 조사 자료, 뚜루뚜루·엔트리 프로그램",
      icon: '<path d="M14 30l7-14 5 8 4-5 6 11"/><path d="M5 35c3 0 3-2 6.3-2s3.2 2 6.4 2 3.2-2 6.3-2 3.2 2 6.4 2 3.2-2 6.3-2S40 35 43 35"/><path d="M5 41c3 0 3-2 6.3-2s3.2 2 6.4 2 3.2-2 6.3-2 3.2 2 6.4 2 3.2-2 6.3-2S40 41 43 41"/>',
      links: [], activities: []
    },
    {
      id: "store", label: "나도 기업가!", word: "기업가!", title: "글로벌 무인 스토어 만들기",
      track: "기본과정", levelLabel: "초등학교", literacy: "인공지능 소양", sessions: 8, phases: [2, 3, 3], color: "#2F7D63", participants: 1326,
      tagline: "여러 나라 말로 손님을 맞는 무인 가게",
      intro: "지구촌 사람들이 겪는 불편을 살펴본 뒤, 엔트리의 AI 블록과 마이크로비트로 무인 가게를 차립니다. 손님의 언어에 맞춰 음성으로 안내하고 화면에 글자를 띄우는 가게를 모둠별로 완성합니다.",
      steps: ["지구촌 문제와 세계시민", "엔트리 AI 블록과 마이크로비트", "다국어 무인 스토어 완성과 발표"],
      made: "다국어 음성 안내와 문자 출력이 되는 무인 스토어",
      icon: '<path d="M8 18l3-9h26l3 9"/><path d="M8 18c0 3 2.2 5 5 5s5-2 5-5c0 3 2.2 5 5 5s5-2 5-5c0 3 2.2 5 5 5s5-2 5-5"/><path d="M11 23v18h26V23"/><path d="M20 41V31h8v10"/>',
      links: [], activities: []
    },
    {
      id: "remix", label: "나도 예술가!", word: "예술가!", title: "AI와 함께 Remix 음악 만들기",
      track: "기본과정", levelLabel: "초등학교", literacy: "인공지능 소양", sessions: 8, phases: [4, 2, 2], color: "#6B4FC8", participants: 1023,
      tagline: "AI와 같이 쓰는 리믹스 한 곡",
      intro: "AI가 만든 음악을 들어 보는 데서 시작해, CyberPi로 리듬과 멜로디를 만들고 몸동작으로 합주합니다. Chord AI로 좋아하는 곡의 화음을 분석하고 Musia One과 함께 그 곡을 새로 편곡합니다.",
      steps: ["AI 음악 감상, CyberPi 리듬·멜로디 합주", "Chord AI 화음 분석, Musia One 익히기", "AI와 함께 리믹스 곡 완성"],
      made: "CyberPi 코드, 기존 곡을 변주한 리믹스 음원",
      icon: '<path d="M18 34V10l20-4v24"/><circle cx="13" cy="34" r="5"/><circle cx="33" cy="30" r="5"/><path d="M18 17l20-4"/>',
      links: [], activities: []
    },
    {
      id: "data", label: "나도 데이터 전문가!", word: "데이터 전문가!", title: "외국인을 위한 인공지능 시스템 구축하기",
      track: "기본과정", levelLabel: "중학교", literacy: "데이터 소양", sessions: 8, phases: [2, 4, 2], color: "#2463A6", participants: 725,
      tagline: "‘안녕’ 한마디에 학교 표지판 언어가 바뀐다",
      intro: "다문화 가정 학생과 학부모가 학교에서 겪는 어려움을 공공 데이터와 통계로 확인합니다. 스프레드시트로 분석한 결과를 바탕으로 앱인벤터 AI와 ESP32를 써서, 들은 언어에 맞춰 바뀌는 OLED 표지판을 만듭니다.",
      steps: ["다문화 사회 데이터 수집과 문제 찾기", "분석·시각화, 앱인벤터 AI와 ESP32", "다국어 표지판 시스템 제작과 발표"],
      made: "외국어 인사를 알아듣고 언어를 바꾸는 AI 앱과 OLED 표지판",
      icon: '<circle cx="24" cy="24" r="17"/><path d="M7 24h34"/><path d="M24 7c5 5 7 11 7 17s-2 12-7 17c-5-5-7-11-7-17s2-12 7-17z"/>',
      links: [], activities: []
    },
    {
      id: "city", label: "나도 도시설계자!", word: "도시설계자!", title: "미래도시 에너지 네트워크 설계하기",
      track: "특화과정", levelLabel: "초등학교", literacy: "데이터 소양", sessions: 12, phases: [4, 4, 4], color: "#13305C", participants: 407,
      tagline: "로봇과 센서로 잇는 미래 도시의 전력망",
      intro: "빛·거리·색상 센서로 반응하는 로봇을 만들고 얼굴과 손동작, 음성으로 로봇을 조종합니다. 팀마다 맡은 구간을 체인리액션으로 이어 스마트 그리드 도시의 에너지 흐름을 완성합니다.",
      steps: ["센서로 반응하는 아이온 로봇", "얼굴·손동작·음성 인식 제어", "스마트 그리드 체인리액션 완성"],
      made: "반응형 로봇, 모션·음성 인식 제어 로봇, 체인리액션 모듈",
      icon: '<path d="M8 41V21l8-5v25M16 41V12l10-5v34M26 41V19l14 6v16"/><path d="M34 6l-4 7h5l-4 7"/>',
      links: [], activities: []
    }
  ]
};
