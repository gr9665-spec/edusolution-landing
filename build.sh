#!/bin/bash
# 사용법: bash build.sh
# sections/, pages/<이름>/ 의 조각 파일을 합쳐 index.html 을 만들고, 옛 아임웹 주소(/27~/30) 안내 페이지를 생성합니다.
# 조각 파일(00-nav 등)을 고친 뒤에는 항상 이 스크립트를 다시 실행하세요.
set -e
cd "$(dirname "$0")"

SITE="https://edu-solution.co.kr"
OG_IMAGE="$SITE/assets/og-image.png"

# make_head <title> <description> <url-path>
make_head() {
  local title="$1" desc="$2" path="$3"
  cat <<EOF
<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>$title</title>
<meta name="description" content="$desc">
<link rel="canonical" href="$SITE$path">
<link rel="icon" href="/assets/logo.png">
<meta name="theme-color" content="#1a2d4a">
<meta property="og:type" content="website">
<meta property="og:site_name" content="에듀솔루션">
<meta property="og:title" content="$title">
<meta property="og:description" content="$desc">
<meta property="og:url" content="$SITE$path">
<meta property="og:image" content="$OG_IMAGE">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="648">
<meta name="twitter:card" content="summary_large_image">
<style>
/* 아임웹이 기본으로 깔아주던 부트스트랩 기본 스타일 중 레이아웃에 영향을 주는 것만 복원 (위젯 코드의 rem 단위는 html 10px 기준) */
html{font-size:10px;-webkit-tap-highlight-color:rgba(0,0,0,0)}
*,*::before,*::after{box-sizing:border-box}
h1,h2,h3,h4,h5,h6{font-family:'Noto Sans KR',sans-serif}
body{margin:0;font-family:"Helvetica Neue",Helvetica,Arial,sans-serif;font-size:14px;line-height:1.6;color:#333;background-color:#fff}
p{margin:0 0 10px}
a{color:#337ab7;text-decoration:none}
button,input,optgroup,select,textarea{margin:0;font:inherit;color:inherit}
label{display:inline-block;max-width:100%;margin-bottom:5px;font-weight:700}
</style>
EOF
  cat head-extra.html
  printf '</head>\n<body>\n'
}

# build_page <out-file> <logo-path> <title> <description> <url-path> <fragment...>
build_page() {
  local out="$1" logo="$2" title="$3" desc="$4" path="$5"; shift 5
  {
    make_head "$title" "$desc" "$path"
    for f in "$@"; do
      if [ "$(basename "$f")" = "00-nav.html" ]; then
        sed "s#\.\./assets/logo\.png#$logo#" sections/00-nav.html
      else
        cat "$f"
      fi
      printf '\n\n'
    done
    printf '</body>\n</html>\n'
  } > "$out"
}

# 서브페이지가 공유하는 조각은 sections/ 원본에서 복사
for p in team credit-bank education-info reviews; do
  sed 's#\.\./assets/logo\.png#../../assets/logo.png#' sections/00-nav.html > "pages/$p/00-nav.html"
  cp sections/09-kakao-float-button.html "pages/$p/03-kakao-float-button.html"
  cp sections/10-diagnostic-popup.html   "pages/$p/04-diagnostic-popup.html"
done

# 메인
build_page index.html "assets/logo.png" \
  "학점은행제 전문 플래너 | 에듀솔루션 edusolution" \
  "학점은행제 전문 플래너 팀이 학위 취득 목표에 맞는 수강 플랜을 1:1로 설계해 드립니다. 사회복지사, 보육교사, 편입 준비 등 다양한 목적에 맞춰 빠르고 정확하게 안내해 드리니 지금 바로 무료 상담을 신청해보세요!" \
  "/" \
  sections/00-nav.html sections/01-hero-image.html sections/02-hero-navy-features.html \
  sections/03-service-grid.html sections/04-caution-compare.html sections/05-reviews.html \
  sections/06-consult-form.html sections/09-kakao-float-button.html sections/10-diagnostic-popup.html \
  sections/08-form-label-fix.html sections/07-animations.html

# 서브페이지 (조각 순서: nav, 본문, 카카오, 팝업, 애니메이션)
sub() { # <folder> <title> <description>
  local p="$1"
  build_page "pages/$p/index.html" "../../assets/logo.png" "$2" "$3" "/pages/$p/" \
    "pages/$p/00-nav.html" "pages/$p/01-main-content.html" "pages/$p/03-kakao-float-button.html" \
    "pages/$p/04-diagnostic-popup.html" "pages/$p/02-animations.html"
}
sub team "팀 에듀솔루션 | 에듀솔루션" "에듀솔루션 팀과 상담 담당자를 소개합니다."
sub credit-bank "학점은행제란? 제도 개요·목표·진행 절차 | 에듀솔루션" "학점은행제의 제도 개요, 목표별 활용법, 진행 절차와 자주 묻는 질문을 한눈에 정리했습니다."
sub education-info "학점은행제 교육정보 | 학위·자격증·편입·대학원 | 에듀솔루션" "학위 취득, 사회복지사 2급, 보육교사 2급, 기사·산업기사 응시자격, 편입, 대학원까지 목표별 조건과 과정을 정리했습니다."
sub reviews "수강생 후기 | 에듀솔루션" "에듀솔루션과 함께 학점은행제 과정을 마친 수강생분들의 후기를 목표별로 확인해 보세요."

# 옛 아임웹 주소 → 새 페이지 (GitHub Pages는 301을 지원하지 않아 meta refresh 사용)
redirect() { # <old-path-folder> <new-path>
  mkdir -p "$1"
  cat > "$1/index.html" <<EOF
<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<title>페이지가 이동했습니다 | 에듀솔루션</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="refresh" content="0; url=$2">
<link rel="canonical" href="$SITE$2">
<script>location.replace("$2");</script>
</head>
<body>
<p>페이지가 이동했습니다. <a href="$2">이동하기</a></p>
</body>
</html>
EOF
}
redirect 27 /pages/team/
redirect 28 /pages/credit-bank/
redirect 29 /pages/education-info/
redirect 30 /pages/reviews/

# sitemap.xml
{
  echo '<?xml version="1.0" encoding="UTF-8"?>'
  echo '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
  for u in / /pages/team/ /pages/credit-bank/ /pages/education-info/ /pages/reviews/; do
    echo "  <url><loc>$SITE$u</loc></url>"
  done
  echo '</urlset>'
} > sitemap.xml

printf 'User-agent: *\nAllow: /\n\nSitemap: %s/sitemap.xml\n' "$SITE" > robots.txt

echo "build done"
