"""현재 저장소의 생성물을 tests/golden 으로 복사한다(줄바꿈은 LF로 통일).

사람이 화면 변화를 확인하고 승인한 변경 뒤에만 실행한다.  사용법: python tests/snapshot_golden.py
"""
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GOLDEN = ROOT / "tests" / "golden"

FILES = ["index.html", "sitemap.xml", "robots.txt",
         "27/index.html", "28/index.html", "29/index.html", "30/index.html"]
for folder in ("team", "credit-bank", "education-info", "reviews"):
    FILES += ["pages/%s/%s" % (folder, name)
              for name in ("index.html", "00-nav.html", "03-kakao-float-button.html", "04-diagnostic-popup.html")]


def main() -> None:
    if GOLDEN.exists():
        shutil.rmtree(GOLDEN)
    for rel in FILES:
        dst = GOLDEN / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes((ROOT / rel).read_bytes().replace(b"\r\n", b"\n"))
    print("golden %d개 저장" % len(FILES))


if __name__ == "__main__":
    main()
