"""고정 데이터(tests/golden_data)로 빌드한 결과를 tests/golden 으로 저장한다(줄바꿈은 LF).

조각 파일(sections/, pages/)이나 빌더 코드를 바꿔 화면이 달라졌고 그 변화를 확인·승인한 뒤에만 실행한다.
후기·수치 같은 운영 데이터(data/)를 바꾼 것만으로는 실행할 필요가 없다.  사용법: python tests/snapshot_golden.py
"""
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from site_build.core import build_all  # noqa: E402
from site_build.site import load_site  # noqa: E402

GOLDEN = ROOT / "tests" / "golden"
GOLDEN_DATA = ROOT / "tests" / "golden_data"

FILES = ["index.html", "sitemap.xml", "robots.txt",
         "27/index.html", "28/index.html", "29/index.html", "30/index.html"]
for folder in ("team", "credit-bank", "education-info", "reviews"):
    FILES += ["pages/%s/%s" % (folder, name)
              for name in ("index.html", "00-nav.html", "03-kakao-float-button.html", "04-diagnostic-popup.html")]
FILES.append("pages/reviews/g01/index.html")        # 후기 상세 페이지 한 개(대표 이미지·제목·본문 서식 포함)
FILES.append("pages/education-info/sample-article/index.html")        # 교육정보 글 상세 페이지 한 개(표·구조화 정보 포함)


def main() -> None:
    if GOLDEN.exists():
        shutil.rmtree(GOLDEN)
    with tempfile.TemporaryDirectory() as tmp:
        built = Path(tmp)
        tokens, extra = load_site(ROOT, data_root=GOLDEN_DATA)
        build_all(ROOT, built, tokens, extra)
        for rel in FILES:
            dst = GOLDEN / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes((built / rel).read_bytes().replace(b"\r\n", b"\n"))
    print("golden %d개 저장" % len(FILES))


if __name__ == "__main__":
    main()
