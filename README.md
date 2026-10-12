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
