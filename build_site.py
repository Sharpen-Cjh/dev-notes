#!/usr/bin/env python3
"""dev-notes/*.md -> dev-notes/site/*.html 정적 사이트 빌드 스크립트.

사용법: python3 build_site.py
소스(.md)를 수정한 뒤 이 스크립트를 다시 실행하면 site/ 폴더가 갱신된다.
site/ 폴더를 그대로 Vercel 등 정적 호스팅에 올리면 배포된다.
"""
from __future__ import annotations

import re
import shutil
from pathlib import Path

import markdown

ROOT = Path(__file__).parent
SITE = ROOT / "site"
SITE_SRC = ROOT / "site_src"

CATEGORIES = {
    "language": "언어",
    "frontend": "프론트엔드",
    "backend": "백엔드",
    "db": "데이터베이스",
    "system": "시스템",
    "network": "네트워크",
}

MD = markdown.Markdown(extensions=["fenced_code", "tables", "toc"])


def read_title_and_body(md_path: Path) -> tuple[str, str]:
    text = md_path.read_text(encoding="utf-8")
    MD.reset()
    html_body = MD.convert(text)
    match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    title = match.group(1).strip() if match else md_path.stem
    return title, html_body


def page_shell(*, title: str, depth: int, breadcrumb_html: str, body_html: str, active_cat: str | None) -> str:
    prefix = "../" * depth
    nav_links = "\n".join(
        f'<a href="{prefix}{slug}/index.html" class="{"active" if slug == active_cat else ""}">{label}</a>'
        for slug, label in CATEGORIES.items()
    )
    return f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} · 개발 노트</title>
<link rel="stylesheet" href="{prefix}assets/style.css">
</head>
<body>
<header class="site-header">
  <a class="title" href="{prefix}index.html">📓 개발 노트 <span class="accent">Notes</span></a>
  <nav class="category-nav">{nav_links}</nav>
</header>
<main>
  <div class="breadcrumb">{breadcrumb_html}</div>
  {body_html}
</main>
<footer class="page-footer">여러 프로젝트를 하며 배운 것을 카테고리별로 누적 정리하는 개인 노트입니다.</footer>
</body>
</html>
"""


def build_topic_page(cat_slug: str, md_path: Path) -> str:
    title, body_html = read_title_and_body(md_path)
    slug = md_path.stem
    cat_label = CATEGORIES[cat_slug]
    breadcrumb = f'<a href="../index.html">홈</a> / <a href="index.html">{cat_label}</a> / {title}'
    return page_shell(title=title, depth=1, breadcrumb_html=breadcrumb, body_html=body_html, active_cat=cat_slug)


def build_category_index(cat_slug: str, md_files: list[Path]) -> str:
    cat_label = CATEGORIES[cat_slug]
    if not md_files:
        items_html = '<p class="empty-state">아직 정리된 내용이 없습니다.</p>'
    else:
        items = []
        for md_path in sorted(md_files):
            title, body_html = read_title_and_body(md_path)
            first_para = re.search(r"<p>(.*?)</p>", body_html, re.DOTALL)
            desc = re.sub("<[^<]+?>", "", first_para.group(1)).strip()[:80] if first_para else ""
            items.append(
                f'<li><a href="{md_path.stem}.html">{title}</a>'
                f'<span class="desc">{desc}</span></li>'
            )
        items_html = f'<ul class="topic-list">{"".join(items)}</ul>'
    breadcrumb = f'<a href="../index.html">홈</a> / {cat_label}'
    body = f"<h1>{cat_label}</h1>{items_html}"
    return page_shell(title=cat_label, depth=1, breadcrumb_html=breadcrumb, body_html=body, active_cat=cat_slug)


def build_home_index() -> str:
    cards = []
    for slug, label in CATEGORIES.items():
        count = len(list((ROOT / slug).glob("*.md"))) if (ROOT / slug).exists() else 0
        desc = f"{count}개 글" if count else "아직 없음"
        cards.append(f'<li><a href="{slug}/index.html">{label}</a><span class="desc">{desc}</span></li>')
    body = f"<h1>개발 노트</h1><p>프로젝트를 하며 배운 개념을 카테고리별로 정리합니다.</p>" \
           f'<ul class="topic-list">{"".join(cards)}</ul>'
    return page_shell(title="개발 노트", depth=0, breadcrumb_html="홈", body_html=body, active_cat=None)


def main() -> None:
    if SITE.exists():
        shutil.rmtree(SITE)
    (SITE / "assets").mkdir(parents=True)
    shutil.copy(SITE_SRC / "style.css", SITE / "assets" / "style.css")

    (SITE / "index.html").write_text(build_home_index(), encoding="utf-8")

    for slug in CATEGORIES:
        cat_dir = ROOT / slug
        out_dir = SITE / slug
        out_dir.mkdir(parents=True, exist_ok=True)
        md_files = sorted(cat_dir.glob("*.md")) if cat_dir.exists() else []

        for md_path in md_files:
            html = build_topic_page(slug, md_path)
            (out_dir / f"{md_path.stem}.html").write_text(html, encoding="utf-8")

        (out_dir / "index.html").write_text(build_category_index(slug, md_files), encoding="utf-8")

    print(f"빌드 완료: {SITE}")


if __name__ == "__main__":
    main()
