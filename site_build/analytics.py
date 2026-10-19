"""방문 분석 도구(구글 애널리틱스 4, 네이버 애널리틱스) 코드를 만든다. 아이디는 data/analytics.json 에서 읽고, 없으면 아무것도 넣지 않는다."""
from __future__ import annotations

from typing import Mapping


def analytics_head(cfg: Mapping) -> str:
    """모든 페이지 <head>에 들어갈 분석 코드. 구글 태그(gtag)는 head-extra.html 에서 이미 불러오므로 설정 한 줄만 더한다."""
    parts = []
    if cfg.get("ga4"):
        parts.append("<script>gtag('config', '%s');</script>" % cfg["ga4"])
    if cfg.get("naver"):
        parts.append('<script src="//wcs.pstatic.net/wcslog.js"></script>\n'
                     '<script>\nif(!wcs_add) var wcs_add = {};\nwcs_add["wa"] = "%s";\nif(window.wcs){ wcs_do(); }\n</script>' % cfg["naver"])
    return "\n".join(parts)
