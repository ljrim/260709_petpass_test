# 🐾 PetPass — 반려동물 동반여행 조건 확인 (Streamlit)

내 반려견의 **견종·무게 조건**과 목적지의 **실제 출입 규정**(한국관광공사 반려동물 동반여행 개방데이터)을
자동 대조해, 현장 입장 거부·헛걸음을 예방하는 웹앱.

## 주요 기능
- **반려견 프로필**(F1): 이름·크기·몸무게·맹견 여부. 다중 프로필 전환, JSON 파일로 영속화.
- **목록 + 판정 배지**(F2, F5): 지역별 / 키워드 검색 / 내 주변(거리순) 3가지 진입점.
  각 장소에 🟢 가능 / 🟡 조건부 / 🔴 불가 배지를 활성 프로필 기준으로 판정.
- **상세**(F6, F7): 지도(folium+OSM)·사진·운영정보·동반 조건·준비물 체크리스트.
- **필터**(F8): "우리 강아지가 갈 수 있는 곳만 보기"(🔴 불가 숨김).

## 판정 규칙 (요약) — `petpass/match.py`
`detailPetTour2`의 자유 텍스트를 정규식으로 파싱해 활성 프로필과 대조합니다.

1. 조건 텍스트 결측/파싱 실패 → 🟡 **조건부**(직접 확인) — '불가'로 오판하지 않고 원문 노출
2. `N kg 이하` & 프로필 무게 초과 → 🔴 **불가** (사유 명시)
3. 맹견 프로필 & `맹견 제외/불가` → 🔴 **불가**
4. 맹견 프로필 & `맹견…입마개` → 🟡 **조건부**(입마개 필수)
5. `전 견종`(또는 무게상한 통과) & 조건 없음 → 🟢 **가능**

> 조건 판정은 참고 정보이며, 최종 입장 여부는 현장 규정을 따릅니다.

## 기술 스택
Python + Streamlit · requests · folium + streamlit-folium(OpenStreetMap) · streamlit-geolocation · python-dotenv

## 실행 방법

```bash
pip install -r requirements.txt
cp .env.example .env          # 아래 참고해 인증키 입력
streamlit run app.py          # http://localhost:8501
```

### .env 설정 (중요)
공공데이터포털 > 반려동물 동반여행 서비스(KorPetTourService2) 활용신청 후 발급된
**"일반 인증키(Decoding)"** 값을 그대로 넣습니다.

```env
KTO_SERVICE_KEY=여기에_디코딩된_인증키
```

- **반드시 Decoding(디코딩 원본) 키**를 넣으세요. `requests` 가 파라미터를 URL-인코딩하므로,
  Encoding 값을 넣으면 이중 인코딩으로 실패합니다.
- `.env`는 `.gitignore` 되어 있으며, 키는 **서버측 Python에서만** 쓰여 클라이언트에 노출되지 않습니다.
- Streamlit 은 서버(Python)에서 API를 직접 호출하므로 CORS/mixed-content 문제가 없습니다(프록시 불필요).

## 폴더 구조
```
app.py                  # Streamlit 진입점 (온보딩·목록·상세·사이드바)
petpass/
  kto.py                # KTO API 클라이언트 (requests + @st.cache_data 캐싱, 병렬 호출)
  match.py              # 조건 판정 파서 (핵심 로직)
  intro_fields.py       # detailIntro2 타입별 필드 매핑
  textutil.py           # HTML 제거·체크리스트 분해·날짜 포맷
  constants.py          # 지역/콘텐츠 타입 코드
  store.py              # 프로필 JSON 영속화
requirements.txt
```

## 성능/한도 메모
- 상세 진입 시 `detailCommon2`·`detailIntro2`·`detailPetTour2` **병렬 호출**(`ThreadPoolExecutor`).
- 목록 배지는 `pet_tours_bulk` 로 여러 `detailPetTour2` 를 병렬 조회.
- 모든 API 호출은 `@st.cache_data` 로 캐싱 → 재실행마다 재호출하지 않음. 개발계정 **일 1,000콜** 한도 절약.

## 배포 (Streamlit Community Cloud)
1. 이 리포를 GitHub 에 푸시한다. (`.env`, `petpass_data.json` 은 `.gitignore` 되어 올라가지 않음)
2. [share.streamlit.io](https://share.streamlit.io) 에서 New app → 리포/브랜치/`app.py` 선택.
3. **Settings → Secrets** 에 인증키를 등록한다 (디코딩 원본):
   ```toml
   KTO_SERVICE_KEY = "여기에_디코딩된_인증키"
   ```
   → `petpass/kto.py` 가 환경변수(`.env`)와 `st.secrets` 양쪽에서 키를 읽는다.
4. Deploy. (의존성은 `requirements.txt` 로 자동 설치)

> 로컬에서 secrets 로 테스트하려면 `.streamlit/secrets.toml` 에 같은 값을 넣으면 된다(gitignore됨).
