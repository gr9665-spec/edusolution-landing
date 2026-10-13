# 에듀솔루션 랜딩페이지 코드

아임웹(imweb) "코드 위젯"에 붙여넣던 랜딩페이지 소스를 백업/버전관리 목적으로 정리한 저장소입니다.
각 파일은 아임웹에서 섹션 하나(코드 위젯 하나)에 대응합니다.

## 섹션 순서 (아임웹에 위에서 아래로 배치되는 순서)

| 파일 | 내용 |
|---|---|
| [sections/00-nav.html](sections/00-nav.html) | 상단 고정 네비게이션 (로고, 메뉴, 모바일 햄버거) |
| [sections/01-hero-image.html](sections/01-hero-image.html) | 이미지 배경 히어로 (첫 화면 타이틀 + CTA 버튼) |
| [sections/02-hero-navy-features.html](sections/02-hero-navy-features.html) | 네이비 배경 히어로 + 4개 특징 카드 |
| [sections/03-service-grid.html](sections/03-service-grid.html) | 핵심 서비스 6개 카드 그리드 |
| [sections/04-caution-compare.html](sections/04-caution-compare.html) | "이런 곳은 조심하세요" 비교 섹션 |
| [sections/05-reviews.html](sections/05-reviews.html) | 수강생 후기 카드 6개 |
| [sections/06-consult-form.html](sections/06-consult-form.html) | 무료 상담 신청 폼 (EmailJS 연동) |
| [sections/07-animations.html](sections/07-animations.html) | 스크롤 등장 애니메이션 · 카운트업 · 네비 그림자 등 공통 스크립트 (페이지 최하단 배치) |
| [sections/08-form-label-fix.html](sections/08-form-label-fix.html) | 상담 폼 라벨 가시성 보정 CSS (아무 위치에나 추가 가능) |
| [sections/09-kakao-float-button.html](sections/09-kakao-float-button.html) | 우하단 카카오톡 플로팅 버튼 |
| [sections/10-diagnostic-popup.html](sections/10-diagnostic-popup.html) | "30초 자가진단" 플로팅 뱃지 + 팝업 모달 |

번호 순서대로 아임웹의 각 섹션 코드 위젯에 그대로 붙여넣으면 원래 페이지와 동일하게 동작합니다.

## 빌드와 로컬 미리보기

`index.html`(루트와 `pages/*/`)은 직접 고치지 않고 `python build.py`로 생성합니다. 조각 파일(`sections/`, `pages/*/01-main-content.html` 등)을 고친 뒤에는 항상 다시 실행하세요. 처음 한 번만 `pip install -r requirements.txt`로 의존성(Pillow, pytest)을 설치합니다.
링크가 도메인 루트 기준(`/pages/...`)이라 `index.html`을 파일로 직접 열면 링크가 안 맞습니다. 저장소 루트에서 아래 명령으로 띄우고 http://localhost:8777/ 로 확인하세요.

```
python -m http.server 8777
```

- `head-extra.html`: 모든 페이지 `<head>`에 들어가는 추가 코드 자리 (구글 광고/GA 태그, 검색 소유확인 meta)
- `27/`, `28/`, `29/`, `30/`: 옛 아임웹 주소로 들어온 방문자를 새 페이지로 보내는 안내 페이지
- `CNAME`, `404.html`, `sitemap.xml`, `robots.txt`: 커스텀 도메인(edu-solution.co.kr) 운영용

## 확인/조치가 필요한 부분

- **로고 이미지** — `assets/logo.png`에 원본 로고 파일을 넣어뒀습니다. `sections/00-nav.html`의 `<img>`는 이 파일을 상대경로로 참조합니다.
  아임웹에 다시 붙여넣을 때는 `assets/logo.png`를 아임웹 미디어 라이브러리에 업로드한 뒤 나오는 URL로 `src`를 바꾸거나,
  원래처럼 base64로 인코딩해서 넣으면 됩니다.
- **Google Ads 전환 추적(`gtag`)** — `sections/06-consult-form.html`의 상담 폼 제출 스크립트가 `gtag(...)`를 호출하는데,
  `gtag.js` 자체는 이 코드에 포함돼 있지 않습니다. 아임웹의 "트래킹 코드/스크립트 삽입" 설정에서 별도로 로드되고 있을 가능성이 높습니다.
- **EmailJS 키** — `service_i38779r`, `template_bfc6i4o`, public key `k9jqBez4YeBqYDgzf`는 브라우저에 그대로 노출되는 공개 값이라
  (원래 아임웹 페이지 소스에도 그대로 보였던 값들이라) 저장소에 그대로 남겨뒀습니다. 다만 이 저장소를 **퍼블릭(공개)**으로 올릴 경우
  EmailJS 대시보드에서 도메인 제한(허용 도메인)을 걸어두는 걸 권장합니다.
- **카카오 채널 링크**(`pf.kakao.com/_PxdxhHn`), **전화/상담 신청 관련 문구** 등은 실제 운영 정보이므로 그대로 유지했습니다.

## 사용 방법 (아임웹에 다시 반영할 때)

1. 아임웹 관리자 > 디자인 > 해당 섹션의 코드 위젯을 열기
2. 이 저장소의 `sections/xx-*.html` 파일 내용을 그대로 복사해서 붙여넣기
3. 로고 이미지만 위 안내대로 원본으로 교체

## 서브 페이지 (pages/)

메인 랜딩페이지 외에 아임웹의 다른 페이지 코드도 `pages/<페이지명>/` 폴더에 같은 방식으로 정리합니다.

| 페이지 | 폴더 | 비고 |
|---|---|---|
| 팀 에듀솔루션 (아임웹 `/27`) | [pages/team/](pages/team/) | 히어로 + 강점 3개 + 담당자 소개 3명 + CTA |
| 학점은행제 (아임웹 `/28`) | [pages/credit-bank/](pages/credit-bank/) | 히어로 + 제도 개요 + 목표 6개 + 진행 절차 + FAQ + CTA |
| 교육정보 (아임웹 `/29`) | [pages/education-info/](pages/education-info/) | 히어로 + 목표별 카드뉴스 6개(학위취득/사회복지사2급/보육교사2급/기사·산업기사/편입/대학원) + CTA |
| 수강생 후기 (아임웹 `/30` 대체) | [pages/reviews/](pages/reviews/) | 아임웹 코드 이전이 아니라 **새로 제작**. 기존 메인의 후기 6개 + 목표별 필터(전체/학위/자격증/편입) + 공통 키워드 4개 + CTA |

### pages/team/ 참고

- 담당자 4명(상희경·이정민·성서아·홍시현)의 사진은 `assets/team-*.jpg`에 원본에서 가로 800px로 줄여 저장했습니다. 원본은 `Desktop/잡동/담당자 이미지/`에 있습니다. 담당자를 추가할 때는 `.pt-mem-card` 블록을 복사하고, `02-animations.html`의 `nth-child` 지연값과 `.pt-mem-grid` 열 수를 같이 조정하세요.
- 네비게이션 · 카카오톡 플로팅 버튼 · 30초 자가진단 팝업은 메인 페이지(`sections/00, 09, 10`)와 동일한 코드를 재사용했습니다.

## 후기·합격 사례·수치·사업자 정보 관리 (data/)

내용은 `data/*.json`에 적고 `python build.py`를 실행하면 페이지와 sitemap이 함께 만들어집니다. 규칙에 어긋나면 어디가 문제인지 알려 주며 빌드가 멈춥니다.

| 파일 | 내용 |
|---|---|
| `data/reviews.json` | 후기·합격 사례. `kind`: `text`(글 후기) / `capture`(대화 캡처) / `case`(합격 사례, 상세 페이지 자동 생성) |
| `data/stats.json` | 메인 실적 수치 띠(최대 6개). `value`, `label`, `asOf`(기준 시점)가 필수, `source`(근거 문구)는 선택(적으면 "2026.10 기준 · 근거"로, 안 적으면 "2026.10 기준"만 표시) |
| `data/team.json` | 담당자 정보. `career`(경력·자격 목록), `youtube`(개인 유튜브 채널 주소)는 선택 |
| `data/youtube.json` | 팀 유튜브 채널(`name`, `url`, 선택 `description`). 팀 페이지 담당자 카드 위에 크게 나옵니다. 없으면 구역이 나오지 않습니다 |
| `data/business.json` | 하단 사업자 정보(상호·사업자등록번호·주소 필수, 대표자 이름은 선택). 없으면 푸터가 나오지 않습니다 |

**대화 캡처·인증 이미지 올리는 순서**
1. 원본을 `raw-proof/`에 둡니다(git에 올라가지 않습니다).
2. 이름·연락처·프로필 사진 위치를 확인하고 `python tools/mask.py raw-proof/원본.png assets/proof/결과.jpg --box x,y,w,h` 로 가립니다(여러 곳은 `--box`를 반복).
3. 결과 이미지를 직접 열어 개인정보가 가려졌는지 확인한 뒤에만 `reviews.json`에 추가합니다.

**확인 명령**: `python -m pytest -q` (테스트), `python tools/check_links.py` (링크·이미지 검사)

**주의사항**
- **`data/` 폴더는 사이트에 그대로 공개됩니다** (예: `https://edu-solution.co.kr/data/reviews.json`). `source`를 포함해 어느 칸에도 수강생 실명·전화번호·이메일을 쓰지 마세요. 전화번호·이메일 형태는 빌드가 막습니다(사업자 정보 `business.json`은 제외).
- 이미지 경로는 `assets/` 안의 상대경로만 허용됩니다. `raw-proof/`(원본)나 저장소 밖을 가리키면 빌드가 멈춥니다.
- 후기의 `headline`·`body`와 담당자의 `bio`는 HTML이 그대로 들어갑니다(`<mark>`, `<strong>`, `<br>` 사용). 나머지 칸은 자동으로 이스케이프됩니다.
- 합격 사례(`case`)를 `reviews.json`에서 지우면 다음 빌드에서 그 상세 페이지도 함께 지워집니다. 지운 뒤 반드시 `python build.py`를 실행하고 푸시하세요.
- 후기·수치를 바꾸면 화면이 바뀌므로 `python -m pytest -q`가 `test_golden`에서 실패합니다. 이것은 "기준본과 달라졌다"는 알림입니다. 로컬에서 화면을 확인한 뒤 `python tests/snapshot_golden.py`로 기준본을 갱신하고 함께 커밋하세요.
