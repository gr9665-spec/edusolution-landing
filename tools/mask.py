"""후기·합격 인증 이미지의 개인정보(이름, 연락처, 프로필 사진 등)를 가리는 도구.

사용법:
    python tools/mask.py raw-proof/원본.png assets/proof/결과.jpg --box 40,120,300,60 --box 10,10,80,80

--box x,y,w,h  가릴 사각형(원본 이미지 픽셀 좌표). 여러 번 지정할 수 있다.
결과는 JPEG로만 저장하며 EXIF·위치 정보 같은 메타데이터는 남기지 않는다.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

MAX_WIDTH = 1200
FILL = (46, 62, 90)

Box = tuple[int, int, int, int]


def parse_box(text: str) -> Box:
    try:
        parts = [int(v) for v in text.split(",")]
    except ValueError as exc:
        raise argparse.ArgumentTypeError("--box는 x,y,w,h 형식의 정수여야 합니다: " + text) from exc
    if len(parts) != 4 or parts[2] <= 0 or parts[3] <= 0:
        raise argparse.ArgumentTypeError("--box는 x,y,w,h 형식(w,h는 양수)이어야 합니다: " + text)
    return (parts[0], parts[1], parts[2], parts[3])


def mask_image(src: Path, dst: Path, boxes: list[Box], max_width: int = MAX_WIDTH) -> tuple[int, int]:
    """boxes 영역을 단색으로 덮고, 가로 max_width 이하로 줄여 dst(JPEG)에 저장한다. 저장한 크기를 돌려준다."""
    if dst.suffix.lower() not in (".jpg", ".jpeg"):
        raise ValueError("결과 파일은 .jpg 로 저장해야 합니다: %s" % dst)
    with Image.open(src) as opened:
        im = ImageOps.exif_transpose(opened).convert("RGB")
    draw = ImageDraw.Draw(im)
    for x, y, w, h in boxes:
        if x < 0 or y < 0 or x + w > im.width or y + h > im.height:
            raise ValueError("가림 영역이 이미지(%dx%d) 밖입니다: %d,%d,%d,%d" % (im.width, im.height, x, y, w, h))
        draw.rectangle([x, y, x + w - 1, y + h - 1], fill=FILL)
    if im.width > max_width:
        im = im.resize((max_width, round(im.height * max_width / im.width)), Image.LANCZOS)
    dst.parent.mkdir(parents=True, exist_ok=True)
    im.save(dst, "JPEG", quality=85, optimize=True)
    return im.size


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="이미지의 개인정보 영역을 가립니다.")
    parser.add_argument("src", type=Path)
    parser.add_argument("dst", type=Path)
    parser.add_argument("--box", type=parse_box, action="append", default=[], help="가릴 영역 x,y,w,h")
    args = parser.parse_args(argv)
    size = mask_image(args.src, args.dst, args.box)
    print("저장: %s (%dx%d, 가린 영역 %d곳)" % (args.dst, size[0], size[1], len(args.box)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
