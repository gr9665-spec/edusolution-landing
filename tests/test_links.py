from tools.check_links import check


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_reports_missing_file_and_missing_anchor_but_not_good_links(tmp_path):
    write(tmp_path / "index.html", '<div id="top"></div><a href="/pages/a/">ok</a><a href="#top">ok</a>'
          '<a href="/pages/a/#sec">ok</a><a href="/pages/none/">깨짐</a><a href="#nope">깨짐</a>'
          '<img src="/assets/x.png"><a href="https://example.com/">외부</a><a href="mailto:a@b.c">메일</a>')
    write(tmp_path / "pages/a/index.html", '<div id="sec"></div>')
    write(tmp_path / "assets/x.png", "x")
    problems = check(tmp_path)
    assert len(problems) == 2
    assert any("/pages/none/" in p for p in problems) and any("#nope" in p for p in problems)


def test_percent_encoded_paths_are_resolved_and_extra_roots_are_searched(tmp_path):
    site, repo = tmp_path / "site", tmp_path / "repo"
    write(site / "index.html", '<img src="/assets/한글%20파일.jpg"><a href="/pages/x/#sec">link</a>')
    write(repo / "assets/한글 파일.jpg", "x")
    write(repo / "pages/x/index.html", '<div id="sec"></div>')
    assert check(site, extra_roots=[repo]) == []
    assert len(check(site)) == 2


def test_relative_links_resolve_from_the_page_folder(tmp_path):
    write(tmp_path / "pages/a/index.html", '<img src="../../assets/logo.png"><a href="../b/">b</a>')
    write(tmp_path / "pages/b/index.html", "")
    write(tmp_path / "assets/logo.png", "x")
    assert check(tmp_path) == []


def test_non_site_folders_are_not_scanned(tmp_path):
    write(tmp_path / "index.html", "<p>ok</p>")
    for folder in ("tests/golden", "docs/x", ".superpowers/y", "sections"):
        write(tmp_path / folder / "index.html", '<img src="/assets/nope.png">')
    assert check(tmp_path) == []
