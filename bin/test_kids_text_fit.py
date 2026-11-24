#!/usr/bin/env python3
"""
Automated Playwright Bounding-Box Unit Test for Kids' Own Stories.

Verifies that across ALL books (sardegna 16 pages + petit-prince 26 pages)
× 3 reading tiers (seby, ale, emma) × 3 learning languages (fr, it, de),
plus Traduzione Pari Pari pairs (including en-GB) and mobile portrait single-page mode:
  1. ZERO vertical or horizontal text overflow out of the virtual sand-patch bounding box
     (.kids-white-patch-text-zone).
  2. High visual legibility & space utilization (fillRatio >= MIN_FILL_RATIO, no wasted half-empty patch).

Usage:
  uv run --with playwright python3 bin/test_kids_text_fit.py
  # or via just:
  just test-fit
"""

from __future__ import annotations

import functools
import http.server
import os
import socketserver
import sys
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

REPO_ROOT = Path(__file__).resolve().parent.parent
BOOKS = [
    {
        "alias": "sardegna",
        "story_id": "storia-sardegna-cala-gonone-arbatax-famiglia",
        "spreads": 8,
        "pages": 16,
        "frontispiece_pages": set(),
    },
    {
        "alias": "petit-prince",
        "story_id": "le-petit-prince",
        "spreads": 13,
        "pages": 26,
        "frontispiece_pages": {1},
    },
]
LEVELS = ["seby", "ale", "emma"]
LANGS = ["fr", "it", "de"]
MIN_FILL_RATIO = 0.42
MAX_OVERFLOW_PX = 2


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:  # noqa: A002
        pass


def start_static_server(root: Path) -> tuple[socketserver.TCPServer, int]:
    handler = functools.partial(QuietHandler, directory=str(root))
    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.TCPServer(("127.0.0.1", 0), handler)
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return httpd, port


def main() -> int:
    if len(os.environ.get("TMPDIR", "")) > 40 and os.path.isdir("/tmp"):
        os.environ["TMPDIR"] = "/tmp"

    httpd, port = start_static_server(REPO_ROOT)
    base_url = f"http://127.0.0.1:{port}/index.html"
    failures: list[str] = []
    summary_rows: list[tuple[str, str, str, int, float, float, float, float, int]] = []
    parallel_checked = 0
    mobile_pages_checked = 0

    try:
        with sync_playwright() as p:
            launch_kwargs: dict = {"headless": True}
            if os.path.exists("/usr/bin/google-chrome"):
                launch_kwargs["executable_path"] = "/usr/bin/google-chrome"
                launch_kwargs["args"] = [
                    "--use-gl=angle",
                    "--use-angle=gl",
                    "--enable-gpu-rasterization",
                    "--enable-webgl",
                    "--ignore-gpu-blocklist",
                ]
            browser = p.chromium.launch(**launch_kwargs)
            context = browser.new_context(viewport={"width": 1440, "height": 900})
            page = context.new_page()

            for book in BOOKS:
                alias = book["alias"]
                story_id = book["story_id"]
                spreads = book["spreads"]
                for level in LEVELS:
                    for lang in LANGS:
                        url = f"{base_url}?book={alias}&mode={level}&lang={lang}"
                        page.goto(url, wait_until="networkidle")
                        page.wait_for_selector(".kids-sentence-box", timeout=10000)
                        page.evaluate("() => document.fonts ? document.fonts.ready : Promise.resolve()")
                        resolved_tab = page.evaluate("() => typeof activeTab !== 'undefined' ? activeTab : ''")
                        if resolved_tab != story_id:
                            failures.append(f"[{alias}/{level}/{lang}]: activeTab={resolved_tab!r} != {story_id!r}")

                        fonts: list[float] = []
                        fills: list[float] = []
                        overflow_count = 0

                        for spread_idx in range(spreads):
                            if spread_idx > 0:
                                page.evaluate(
                                    """(idx) => {
                                        if (typeof kidsPageIndexBySlug !== 'undefined') {
                                            kidsPageIndexBySlug[activeTab] = idx * 2;
                                            renderActiveBook();
                                        }
                                    }""",
                                    spread_idx,
                                )
                            page.wait_for_timeout(80)
                            page.evaluate("() => { if (typeof fitKidsTextToPatch === 'function') fitKidsTextToPatch(); }")
                            metrics = page.evaluate("() => window.__kidsTextFitMetrics ? window.__kidsTextFitMetrics() : []")

                            expected_leaves = 1 if (spread_idx == 0 and 1 in book["frontispiece_pages"]) else 2
                            if len(metrics) != expected_leaves:
                                failures.append(
                                    f"[{alias}/{level}/{lang}] spread {spread_idx + 1}: expected {expected_leaves} pages, got {len(metrics)}"
                                )
                                continue
                            if spread_idx == 0 and 1 in book["frontispiece_pages"]:
                                front_ok = page.evaluate(
                                    "() => Boolean(document.querySelector('#bookPageLeft .kids-watercolor-leaf.is-frontispiece')) && document.querySelectorAll('#bookPageLeft .kids-white-patch-text-zone').length === 0"
                                )
                                if not front_ok:
                                    failures.append(
                                        f"[{alias}/{level}/{lang}] spread 1: expected clean .is-frontispiece on #bookPageLeft with 0 text zones"
                                    )

                            for m in metrics:
                                fonts.append(m["fontSizePx"])
                                fills.append(m["fillRatio"])
                                if not m["fits"] or m["overflowY"] > MAX_OVERFLOW_PX or m["overflowX"] > MAX_OVERFLOW_PX:
                                    overflow_count += 1
                                    failures.append(
                                        f"OVERFLOW [{alias}/{level}/{lang}] P{m['page']:02d}: "
                                        f"font={m['fontSizePx']}px scrollH={m['scrollHeight']} > clientH={m['clientHeight']} "
                                        f"(overflowY={m['overflowY']}px, overflowX={m['overflowX']}px)"
                                    )
                                if m["fillRatio"] < MIN_FILL_RATIO:
                                    failures.append(
                                        f"UNDERFILL [{alias}/{level}/{lang}] P{m['page']:02d}: "
                                        f"font={m['fontSizePx']}px fillRatio={m['fillRatio']:.2f} < {MIN_FILL_RATIO}"
                                    )

                        if fonts and fills:
                            summary_rows.append(
                                (
                                    alias,
                                    level,
                                    lang,
                                    len(fonts),
                                    min(fonts),
                                    sum(fonts) / len(fonts),
                                    min(fills),
                                    sum(fills) / len(fills),
                                    overflow_count,
                                )
                            )

            # Parallel Translation ("Cheating Mode") unit tests:
            # Verify Left Page == Book Language and Right Page == Translation Language (including en-GB!)
            parallel_pairs = [
                ("it", "en"),
                ("fr", "en"),
                ("de", "en"),
                ("de", "it"),
                ("fr", "it"),
                ("it", "fr"),
            ]
            for book in BOOKS:
                alias = book["alias"]
                total_pages = book["pages"]
                front_pages = book["frontispiece_pages"]
                readable_pages = [p for p in range(1, total_pages + 1) if p not in front_pages]
                first_p = readable_pages[0]
                for book_lang, tr_lang in parallel_pairs:
                    pages_to_test = readable_pages if tr_lang == "en" else readable_pages[:2]
                    url = f"{base_url}?book={alias}&mode=emma&lang={book_lang}&parallel=1&page={first_p}"
                    page.goto(url, wait_until="networkidle")
                    page.wait_for_selector(".kids-sentence-box", timeout=10000)
                    page.evaluate(
                        "(tr) => { if (typeof setKidsTranslationLang === 'function') setKidsTranslationLang(tr); }",
                        tr_lang,
                    )
                    for test_page in pages_to_test:
                        if test_page != first_p:
                            page.evaluate(
                                """(pnum) => {
                                    if (typeof kidsPageIndexBySlug !== 'undefined') {
                                        kidsPageIndexBySlug[activeTab] = pnum - 1;
                                        renderActiveBook();
                                    }
                                }""",
                                test_page,
                            )
                        page.wait_for_timeout(45)
                        page.evaluate("() => { if (typeof fitKidsTextToPatch === 'function') fitKidsTextToPatch(); }")
                        metrics = page.evaluate("() => window.__kidsTextFitMetrics ? window.__kidsTextFitMetrics() : []")
                        badges = page.evaluate(
                            "() => Array.from(document.querySelectorAll('#openBookSpread .kids-book-page-num')).map(el => el.textContent.trim())"
                        )
                        texts = page.evaluate(
                            "() => Array.from(document.querySelectorAll('#openBookSpread .kids-sentence-box')).map(el => (el.innerText || '').trim())"
                        )
                        parallel_checked += 1
                        if len(metrics) != 2:
                            failures.append(f"PARALLEL [{alias} p.{test_page} {book_lang}->{tr_lang}]: expected 2 facing pages, got {len(metrics)}")
                            continue
                        left_m, right_m = metrics[0], metrics[1]
                        if left_m["page"] != test_page or right_m["page"] != test_page:
                            failures.append(
                                f"PARALLEL [{alias} p.{test_page} {book_lang}->{tr_lang}]: page mismatch SX={left_m['page']} DX={right_m['page']} != {test_page}"
                            )
                        if left_m["lang"] != book_lang:
                            failures.append(
                                f"PARALLEL [{alias} p.{test_page} {book_lang}->{tr_lang}]: SX lang={left_m['lang']} != expected {book_lang}"
                            )
                        if right_m["lang"] != tr_lang:
                            failures.append(
                                f"PARALLEL [{alias} p.{test_page} {book_lang}->{tr_lang}]: DX lang={right_m['lang']} != expected {tr_lang}"
                            )
                        disp_page = (test_page - 1) if front_pages else test_page
                        expected_badges = [f"{disp_page} · {book_lang.upper()}", f"{disp_page} · {tr_lang.upper()}"]
                        if badges != expected_badges:
                            failures.append(
                                f"PARALLEL [{alias} p.{test_page} {book_lang}->{tr_lang}]: badges={badges} != expected {expected_badges}"
                            )
                        if len(texts) != 2 or not texts[0] or not texts[1]:
                            failures.append(
                                f"PARALLEL [{alias} p.{test_page} {book_lang}->{tr_lang}]: empty parallel sentence text: {texts}"
                            )
                        for side_lbl, m in (("SX", left_m), ("DX", right_m)):
                            if not m["fits"] or m["overflowY"] > MAX_OVERFLOW_PX or m["overflowX"] > MAX_OVERFLOW_PX:
                                failures.append(
                                    f"PARALLEL OVERFLOW [{alias} p.{test_page} {book_lang}->{tr_lang}] {side_lbl}: "
                                    f"scrollH={m['scrollHeight']} > clientH={m['clientHeight']} "
                                    f"(overflowY={m['overflowY']}px, overflowX={m['overflowX']}px)"
                                )
                            if m["fillRatio"] < MIN_FILL_RATIO:
                                failures.append(
                                    f"PARALLEL UNDERFILL [{alias} p.{test_page} {book_lang}->{tr_lang}] {side_lbl}: "
                                    f"font={m['fontSizePx']}px fillRatio={m['fillRatio']:.2f} < {MIN_FILL_RATIO}"
                                )

            # Mobile Portrait (390×844) Single-Page Mode & Face Keep-Out Island unit tests (GitHub Issue #8):
            mobile_ctx = browser.new_context(viewport={"width": 390, "height": 844})
            mpage = mobile_ctx.new_page()
            for book in BOOKS:
                alias = book["alias"]
                total_pages = book["pages"]
                readable_pages = [p for p in range(1, total_pages + 1) if p not in book["frontispiece_pages"]]
                for level in LEVELS:
                    for test_lang in LANGS:
                        url = f"{base_url}?book={alias}&mode={level}&lang={test_lang}&page=1"
                        mpage.goto(url, wait_until="networkidle")
                        mpage.wait_for_selector(".kids-sentence-box", timeout=10000)
                        mpage.evaluate("() => document.fonts ? document.fonts.ready : Promise.resolve()")

                        is_single = mpage.evaluate(
                            "() => document.getElementById('openBookSpread')?.classList.contains('kids-single-page-mode') === true"
                        )
                        if not is_single:
                            failures.append(
                                f"MOBILE [{alias}/{level}/{test_lang}]: expected #openBookSpread.kids-single-page-mode on 390x844 viewport"
                            )

                        for step_idx, expected_pno in enumerate(readable_pages):
                            if step_idx > 0:
                                mpage.evaluate("() => turnPage(1)")
                            mpage.wait_for_timeout(45)
                            mpage.evaluate("() => { if (typeof fitKidsTextToPatch === 'function') fitKidsTextToPatch(); }")
                            m_metrics = mpage.evaluate("() => window.__kidsTextFitMetrics ? window.__kidsTextFitMetrics() : []")
                            b_metrics = mpage.evaluate("() => window.__kidsBubbleOverlapMetrics ? window.__kidsBubbleOverlapMetrics() : []")
                            top_clip = mpage.evaluate("""() => {
                                const z = document.querySelector('#openBookSpread .kids-white-patch-text-zone');
                                if (!z) return 0;
                                const tok = z.querySelector('.kw-token');
                                const zr = z.getBoundingClientRect();
                                const tr = tok ? tok.getBoundingClientRect() : zr;
                                return Number((zr.top - tr.top).toFixed(2));
                            }""")
                            mobile_pages_checked += 1
                            if len(m_metrics) != 1:
                                failures.append(
                                    f"MOBILE [{alias}/{level}/{test_lang}] P{expected_pno:02d}: expected 1 single page leaf, got {len(m_metrics)}"
                                )
                                continue
                            mm = m_metrics[0]
                            if mm["page"] != expected_pno:
                                failures.append(
                                    f"MOBILE [{alias}/{level}/{test_lang}]: turnPage(1) expected page {expected_pno}, got {mm['page']}"
                                )
                            if not mm["fits"] or mm["overflowY"] > MAX_OVERFLOW_PX or mm["overflowX"] > MAX_OVERFLOW_PX:
                                failures.append(
                                    f"MOBILE OVERFLOW [{alias}/{level}/{test_lang}] P{mm['page']:02d}: "
                                    f"fits={mm['fits']} overflowY={mm['overflowY']}px overflowX={mm['overflowX']}px"
                                )
                            if top_clip > 1.0:
                                failures.append(
                                    f"MOBILE TOP CLIP [{alias}/{level}/{test_lang}] P{mm['page']:02d}: topClippedPx={top_clip} > 1"
                                )
                            for bm in b_metrics:
                                if bm.get("overlapsFace"):
                                    failures.append(
                                        f"MOBILE FACE OVERLAP [{alias}/{level}/{test_lang}] P{bm['page']:02d}: "
                                        f"bubble rect={bm['rect']} overlaps face keep-out island (area={bm['overlapArea']})"
                                    )
            mobile_ctx.close()

            browser.close()
    finally:
        httpd.shutdown()

    print("\n📐 Kids' Own Stories — Bounding-Box Text Auto-Fit & Mobile Single-Page Report")
    print("-" * 92)
    print(f"{'Book':<13} {'Level':<7} {'Lang':<5} {'Pages':<6} {'Font min/avg (px)':<20} {'Fill min/avg':<18} {'Overflows':<9}")
    print("-" * 92)
    for book_alias, level, lang, count, f_min, f_avg, fill_min, fill_avg, ov in summary_rows:
        status = "✅ 0" if ov == 0 else f"❌ {ov}"
        print(
            f"{book_alias:<13} {level:<7} {lang:<5} {count:<6} {f_min:5.1f} / {f_avg:5.1f} px     {fill_min:4.0%} / {fill_avg:4.0%}        {status}"
        )
    print("-" * 92)

    if failures:
        print(f"\n❌ {len(failures)} bounding-box check(s) failed:")
        for err in failures[:25]:
            print(f"  - {err}")
        if len(failures) > 25:
            print(f"  ... and {len(failures) - 25} more")
        return 1

    print(
        f"\n✅ ALL {sum(r[3] for r in summary_rows)} desktop page renderings + "
        f"{parallel_checked} Pari Pari pairs + {mobile_pages_checked} mobile portrait single-page renderings passed with 0 overflows!"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
