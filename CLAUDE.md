# CLAUDE.md — 펫패스(PetPass) 프로젝트 컨텍스트

> 이 파일은 리포 루트에 두면 Claude Code가 매 세션 자동으로 읽습니다.
> 상세 제품 요구사항은 `docs/PRD.md` 참조.

## 제품 한 줄 정의
내 반려견의 견종·무게 조건과 목적지의 실제 출입 규정을 자동 대조해, 현장 입장 거부·헛걸음을 예방하는 반려동물 동반여행 조건 확인 웹앱.

## 기술 스택 (Streamlit 으로 전환됨 — 이 스택을 벗어나지 말 것)
- Python 3.x + **Streamlit** (`app.py` 진입점)
- HTTP: `requests` (서버측에서 API 직접 호출 → 프록시 불필요)
- 지도: **folium + streamlit-folium** (OpenStreetMap 타일)
- 위치: `streamlit-geolocation`
- 상태: `st.session_state` + JSON 파일(`petpass_data.json`)로 프로필 영속화
- 설정: `python-dotenv` (`.env`)
- 패키지: pip (`requirements.txt`)

> 초기에는 Vite + React + TS 로 만들었으나 Streamlit 으로 재구축했고, React 자산은 정리(삭제)했다.

## 아키텍처 핵심 규칙
- **API 키는 절대 클라이언트에 노출하지 않는다.** `.env`의 `KTO_SERVICE_KEY`(디코딩 원본)를
  서버측 Python(`petpass/kto.py`)에서만 사용한다. `requests` 가 파라미터를 URL-인코딩한다.
- Streamlit 은 서버(Python)에서 API를 호출하므로 CORS/mixed-content 문제가 없다 (프록시 불필요).
- 응답은 항상 `_type=json`. `resultCode !== "0000"`(단, `03`=NODATA 는 정상 빈 결과) 이거나
  items가 비면 사용자 친화 빈/오류 상태 처리.
- 조건 판정 실패 시 절대 '불가'로 오판하지 않는다. '조건부(직접 확인 필요)'로 폴백하고 원문을 함께 노출한다.
- API 응답은 `@st.cache_data` 로 캐싱해 재실행마다 재호출하지 않는다 (일 1,000콜 한도 절약).

## API 명세 (Base: `http://apis.data.go.kr/B551011/KorPetTourService2`)
공통 필수: `serviceKey`, `MobileOS=ETC`, `MobileApp=PetPass`, `_type=json`

| 용도 | 오퍼레이션 | 주요 파라미터 |
| --- | --- | --- |
| 지역 목록 | `areaBasedList2` | `lDongRegnCd`, `lDongSignguCd`, `contentTypeId`, `arrange=C` |
| 키워드 검색 | `searchKeyword2` | `keyword`(인코딩) |
| 내 주변 | `locationBasedList2` | `mapX`(경도), `mapY`(위도), `radius`(m, 최대20000), `arrange=E` |
| 공통정보 | `detailCommon2` | `contentId` → title, overview, homepage, firstimage, addr1, mapx, mapy |
| 소개정보 | `detailIntro2` | `contentId`, `contentTypeId` → usetime, restdate, parking, chkpet (타입별 상이) |
| **반려동물 조건(핵심)** | `detailPetTour2` | `contentId` → 아래 필드 |

### detailPetTour2 응답 필드 (서비스의 핵심 자산)
- `acmpyPsblCpam` 동반가능동물 — 예: "전 견종 동반 가능(맹견의 경우 입마개 필수)"
- `acmpyTypeCd` 동반유형 — 예: "전구역 동반가능"
- `acmpyNeedMtr` 동반시 필요사항 — 예: "목줄 착용"
- `etcAcmpyInfo` 기타 동반 정보 — 예: "목줄 2m 이내, 배변봉투 필수"
- `relaAcdntRiskMtr` 사고 대비사항
- `relaPosesFclty` 구비 시설 / `relaFrnshPrdlst` 비치 품목 / `relaRntlPrdlst` 렌탈 품목 / `relaPurcPrdlst` 구매 품목

### 콘텐츠 타입 코드
`12`관광지 `14`문화시설 `15`행사·공연·축제 `28`레포츠 `32`숙박 `38`쇼핑 `39`음식점

## 조건 판정 규칙 (배지)
`detailPetTour2`의 자유 텍스트를 정규식으로 파싱해 프로필과 대조:
1. 조건 필드 결측/파싱 실패 → 🟡 조건부(직접 확인 필요) — '불가' 금지, 원문 노출
2. "N kg 이하" 무게 상한 & 프로필 무게 초과 → 🔴 불가 (사유 명시)
3. 맹견 프로필 & "맹견 입마개" 패턴 → 🟡 조건부(입마개 필수)
4. "전 견종/모든 반려견 가능" & 무게 조건 없음 → 🟢 가능

> **주의:** 판정 로직은 실제 API 응답을 여러 건 받아 패턴을 확인한 뒤 다듬는다. 처음부터 완벽하게 만들려 하지 말 것.

## 성능 목표
- 상세 진입 시 `detailCommon2`·`detailIntro2`·`detailPetTour2`를 `ThreadPoolExecutor` 병렬 호출(`detail_all`)
- 목록 배지는 `pet_tours_bulk` 로 여러 `detailPetTour2` 병렬 조회
- 모든 API 호출은 `@st.cache_data` 캐싱 → 동일 인자 재조회 억제 (일 1,000콜 한도 절약)

## 코딩 컨벤션
- 커밋은 기능 단위로 작게. 각 단계 완료 시 dev 서버가 뜨는지 먼저 확인하고 넘어간다.
- API 호출은 try/catch 필수. 이미지 결측 시 플레이스홀더.
- 좌표는 WGS84: `mapy`=위도, `mapx`=경도 (Leaflet은 [lat, lng] 순서).

## 면책
조건 판정은 참고 정보이며 최종 입장 여부는 현장 규정을 따른다는 문구를 판정 결과·상세에 명시. 원천 `modifiedtime`(콘텐츠 수정일)을 상세에 노출.
