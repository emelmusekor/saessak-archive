const fs = require("fs");
const keep = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const P = [
  { id: "create", label: "Create!", word: "Create!", title: "괴물 나라 디지털 북", track: "기본과정", levelLabel: "초등 1~4학년", literacy: "컴퓨팅 사고력", sessions: 8, phases: [2, 3, 3], color: "#3A86E8",
    tagline: "그림책 속 괴물이 태블릿에서 춤춘다",
    intro: "모리스 샌닥의 『괴물들이 사는 나라』를 읽고, 아이들이 떠올린 장면을 옥토 스튜디오로 움직이게 만듭니다. 종이 가면과 도형 스티커로 만든 괴물에 소리와 센서를 더해 모둠마다 디지털 북 한 권을 완성합니다.",
    steps: ["그림책 읽기, 괴물 특징 설명 놀이", "움직임·소리·센서 블록으로 장면 코딩", "모둠 디지털 북 제작과 발표회"],
    made: "옥토 스튜디오로 만든 디지털 북, 움직이는 종이 괴물 가면" },
  { id: "play", label: "PLAY!", word: "PLAY!", title: "내 손으로 만드는 디지털 놀이터", track: "기본과정", levelLabel: "초등 1~4학년", literacy: "디지털 리터러시", sessions: 8, phases: [2, 3, 3], color: "#12A39B",
    tagline: "은박지 버튼으로 내가 짠 게임을 조종한다",
    intro: "메이키메이키에 점토와 은박지를 이어 입력 장치를 만들고, 베티 주니어로 그 장치에 반응하는 게임을 짭니다. 마지막 시간에는 교실이 전시장이 되고, 아이들은 친구 작품을 돌아가며 해 봅니다.",
    steps: ["놀이로 익히는 입력·처리·출력", "베티 주니어 게임, 점토·은박지 입력 장치", "디지털 놀이터 전시와 체험"],
    made: "메이키메이키 입력 장치로 조종하는 베티 주니어 게임" },
  { id: "make", label: "Make!", word: "Make!", title: "클래스 마켓", track: "기본과정", levelLabel: "초등 5~6학년", literacy: "디지털 리터러시", sessions: 8, phases: [2, 2, 4], color: "#2A5BAA",
    tagline: "교실에 장이 서고, 값은 QR로 치른다",
    intro: "바코드와 QR코드가 정보를 담는 원리를 풀어 본 뒤, 학급 화폐로 물건을 사고팝니다. 거래 규칙과 환불 약관은 학급 회의로 정하고, 상품 등록과 사기 문자 가려내기도 학생들이 맡습니다.",
    steps: ["바코드·QR코드 원리 해독", "학급 화폐와 거래 규칙 정하기", "마켓 거래, 상품 등록, 사기 대처"],
    made: "픽셀아트 QR코드, 학급 거래 약관, 상품 등록서, 디지털 생애곡선" },
  { id: "design", label: "Design!", word: "Design!", title: "바이브 코딩", track: "기본과정", levelLabel: "중학교", literacy: "인공지능 소양", sessions: 8, phases: [2, 4, 2], color: "#5A5FD1",
    tagline: "학교의 불편 하나를 골라 앱으로 고친다",
    intro: "학교생활에서 불편한 점을 찾아 앱 제작 의뢰서로 정리하고, Canva의 AI 코드 생성으로 앱을 만듭니다. 프롬프트를 고쳐 가며 결과를 비교하고, 다른 모둠의 의뢰를 받아 앱을 하나 더 만듭니다.",
    steps: ["문제 찾기와 앱 제작 의뢰서", "프롬프트 설계와 앱 구현", "의뢰받은 앱 제작과 시연"],
    made: "모둠별 학교생활 개선 앱" },
  { id: "insight", label: "Insight!", word: "Insight!", title: "데이터 랩", track: "기본과정", levelLabel: "고등학교", literacy: "데이터 소양", sessions: 8, phases: [2, 2, 4], color: "#1B3D73",
    tagline: "지금 하늘을 나는 비행기가 데이터가 된다",
    intro: "OpenSky에서 실시간 항공 데이터를 받아 정리하고, 파이썬으로 이상 비행을 골라 지도 위에 띄웁니다. 직접 설계한 관제 대시보드를 근거로 두괄식 탐구 보고서를 씁니다.",
    steps: ["실시간 데이터 탐색과 탐구 질문", "수집·전처리·시각화", "관제 대시보드와 탐구 보고서"],
    made: "실시간 항공 관제 대시보드, 탐구 보고서" },
  { id: "move", label: "Move!", word: "Move!", title: "AI 우주 탐사대", track: "특화과정", levelLabel: "초등 1~4학년", literacy: "인공지능 소양", sessions: 12, phases: [4, 4, 4], color: "#0F2650",
    tagline: "몸짓으로 로봇을 움직여 행성을 탐사한다",
    intro: "AI 우주 탐사대 후보생이 되어 포즈 인식 게임으로 감각 훈련을 받고, 시뮬레이터에서 경로를 짜는 연습을 합니다. 마지막 네 차시에는 제스처로 아이온 로봇을 조종해 실물 탐사 맵을 누빕니다.",
    steps: ["포즈 인식 게임으로 감각 훈련", "시뮬레이터 탐사 미션", "아이온 로봇 행성 탐사와 임명식"],
    made: "탐사 기록지와 탐사 보고판" },
  { id: "link", label: "Link!", word: "Link!", title: "AI 동물 구조대", track: "특화과정", levelLabel: "초등 5~6학년", literacy: "인공지능 소양", sessions: 12, phases: [4, 4, 4], color: "#1F9A72",
    tagline: "모둠마다 만든 장치를 이어 동물을 구조한다",
    intro: "센서로 움직이는 구조 로봇을 만들고 얼굴·동작·음성 인식으로 로봇을 부립니다. AI가 틀릴 수 있는 상황을 따져 구조대 윤리 수칙을 정한 뒤, 모둠별 장치를 한 줄로 이어 체인리액션 구조 작전을 펼칩니다.",
    steps: ["센서 기반 구조 로봇", "얼굴·동작·음성 인식과 AI 윤리", "구조 체인리액션 완성"],
    made: "체인리액션 구조 장치와 영상 포트폴리오" }
];
const T = {"create": 1000, "play": 1100, "make": 900, "design": 500, "insight": 300, "move": 500, "link": 300};
P.forEach(p => Object.assign(p, keep[p.id], { participants: T[p.id], participantsPlus: false }));
const data = {
  year: 2026,
  seriesLabel: null,
  facts: [["구성", "기본 5 · 특화 2"], ["대상", "초등 1학년 – 고등학교"], ["학생", "4,600명"], ["학교", "217곳"]],
  programs: P
};
const out = "/* 2026 디지털새싹 프로그램 (출처: 2026년도 디지털새싹 사업 운영 프로그램 제안서, 새싹B 일반형) */\nwindow.PROGRAM_YEAR = " + JSON.stringify(data, null, 1) + ";\n";
fs.writeFileSync(process.argv[3], out);
console.log("ok", out.length);
