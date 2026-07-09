# 네이버 지식인 키워드 → 자동 블로그 글 생성 파이프라인

키워드를 넣어두면, 매일 자동으로:
1. 네이버 오픈API(지식iN 검색)로 관련 질문 주제를 수집하고
2. AI가 그 주제를 참고해 **완전히 새로운 글**을 작성하고
3. Jekyll 포스트로 저장 → GitHub Pages에 자동 배포

> 지식인 원문을 복사하지 않고, 질문 "제목/요약"만 참고해서 새 글을 씁니다.
> 네이버 오픈API는 공식 제공 API라 지식인 페이지를 직접 크롤링하는 것과 달리 이용약관 문제가 없습니다.

---

## 1단계. 이 폴더를 내 GitHub 저장소로 만들기

1. GitHub에서 새 저장소 생성 (예: `my-auto-blog`)
2. 이 폴더의 파일들을 그대로 그 저장소에 업로드/커밋
3. 저장소 Settings → Pages → Source를 `GitHub Actions` 또는 `main` 브랜치로 설정
   (github-pages gem을 쓰므로 보통 자동으로 잡힙니다)

## 2단계. 네이버 오픈API 키 발급받기

1. https://developers.naver.com/apps/#/register 접속 (네이버 로그인 필요)
2. "애플리케이션 등록" 클릭
3. 애플리케이션 이름은 아무거나 (예: auto-blog)
4. "사용 API"에서 **검색** 체크
5. 비로그인 오픈API 서비스 환경 → **WEB 설정**에 아무 URL이나 입력 가능
   (예: `https://github.com`)
6. 등록 완료 후 발급되는 **Client ID / Client Secret** 를 복사해두기

## 3단계. Gemini API 키 무료로 발급받기

1. https://aistudio.google.com 접속 (구글 계정으로 로그인)
2. 왼쪽 메뉴 또는 우측 상단 "Get API key" 클릭
3. "Create API key" → 새 프로젝트 선택 후 생성
4. 발급된 키 복사해두기

> 신용카드 등록 없이 무료로 발급되고, 무료 티어(Gemini 2.5 Flash 기준 분당 10회,
> 일일 250건 요청)로도 이 파이프라인(하루 1개 글 생성)은 충분히 커버됩니다.
> 다만 무료 정책은 구글이 수시로 바꾸므로, 발급 시점에 AI Studio 요금 페이지에서
> 최신 무료 한도를 한 번 확인해보는 걸 추천해요.

## 4단계. GitHub 저장소에 Secrets 등록

저장소 → Settings → Secrets and variables → Actions → New repository secret

다음 3개를 각각 등록:
- `NAVER_CLIENT_ID`
- `NAVER_CLIENT_SECRET`
- `GEMINI_API_KEY`

## 5단계. 키워드 설정

`keywords.txt` 파일을 열어서 한 줄에 하나씩 원하는 키워드를 적어두세요.
매 실행마다 아직 처리하지 않은 키워드 1개를 골라 글을 하나 생성합니다.
(어떤 키워드를 이미 썼는지는 `scripts/.used_keywords.json`에 자동 기록됩니다)

## 6단계. 실행 확인

- 기본적으로 매일 한국시간 오전 9시에 자동 실행됩니다 (`.github/workflows/auto-post.yml`의 cron 설정)
- 저장소 → Actions 탭 → "Auto Generate Post" → **Run workflow** 버튼으로 즉시 수동 실행도 가능
- 실행 후 `_posts/` 폴더에 새 `.md` 파일이 생기고 자동 커밋되면 성공
- 며칠 뒤 GitHub Pages 사이트(`https://내계정.github.io/저장소이름/`)에서 글 확인

---

## 로컬에서 미리 테스트해보고 싶다면

```bash
cd scripts
pip install -r requirements.txt

export NAVER_CLIENT_ID="발급받은값"
export NAVER_CLIENT_SECRET="발급받은값"
export GEMINI_API_KEY="발급받은값"

cd ..
python scripts/generate_post.py
```

## 주의사항

- 하루 1개씩 생성되도록 기본 설정되어 있어요. 너무 자주/많이 돌리면
  저품질 대량생성 콘텐츠로 취급되어 검색 노출에 불리할 수 있습니다.
- keywords.txt가 바닥나면 새 키워드를 추가해줘야 계속 생성됩니다.
- 생성된 글은 발행 전에 가끔 직접 검토하는 걸 추천해요 (품질 관리).
