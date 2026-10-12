import statistics

import pytest
from PIL import Image

from tools.mask import FILL, mask_image, parse_box


def noise_image(path, size=(400, 300), fmt="PNG"):
    Image.effect_noise(size, 80).convert("RGB").save(path, fmt)
    return path


def region_pixels(im, box):
    x, y, w, h = box
    return [im.getpixel((px, py)) for px in range(x, x + w) for py in range(y, y + h)]


def test_box_is_filled_with_solid_color(tmp_path):
    src = noise_image(tmp_path / "a.png")
    dst = tmp_path / "out" / "a.jpg"
    mask_image(src, dst, [(40, 60, 120, 50)], max_width=4000)
    with Image.open(dst) as im:
        inner = region_pixels(im, (50, 70, 100, 30))   # JPEG 경계 번짐을 피해 안쪽만 본다
    assert all(abs(p[c] - FILL[c]) <= 8 for p in inner for c in range(3))


def test_outside_box_is_left_alone(tmp_path):
    src = noise_image(tmp_path / "a.png")
    dst = tmp_path / "a.jpg"
    mask_image(src, dst, [(40, 60, 120, 50)], max_width=4000)
    with Image.open(dst) as im:
        outside = [p[0] for p in region_pixels(im, (200, 150, 100, 100))]
    assert statistics.pstdev(outside) > 20   # 노이즈 그대로(가려지지 않음)


def test_wide_image_is_resized_to_max_width(tmp_path):
    src = noise_image(tmp_path / "wide.png", size=(2000, 1000))
    size = mask_image(src, tmp_path / "wide.jpg", [])
    assert size == (1200, 600)


def test_box_outside_image_raises(tmp_path):
    src = noise_image(tmp_path / "a.png")
    with pytest.raises(ValueError, match="밖"):
        mask_image(src, tmp_path / "a.jpg", [(380, 10, 50, 20)])


def test_metadata_is_not_kept(tmp_path):
    src = tmp_path / "meta.jpg"
    im = Image.effect_noise((200, 200), 80).convert("RGB")
    exif = Image.Exif()
    exif[0x010F] = "SomePhoneMaker"
    im.save(src, "JPEG", exif=exif)
    dst = tmp_path / "clean.jpg"
    mask_image(src, dst, [])
    with Image.open(dst) as out:
        assert len(out.getexif()) == 0


def test_non_jpg_destination_is_rejected(tmp_path):
    src = noise_image(tmp_path / "a.png")
    with pytest.raises(ValueError, match="jpg"):
        mask_image(src, tmp_path / "a.png", [])


def test_parse_box_validates_format():
    assert parse_box("1,2,3,4") == (1, 2, 3, 4)
    for bad in ("1,2,3", "a,b,c,d", "1,2,0,4"):
        with pytest.raises(Exception):
            parse_box(bad)
