#!/usr/bin/env python3
"""
Automated Playwright Bounding-Box Unit Test for Kids' Own Stories.

Verifies that across ALL 16 pages × 3 reading tiers (seby, ale, emma) × 3 languages (it, fr, de):
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
LEVELS = ["seby", "ale", "emma"]
LANGS = ["it", "fr", "de"]
TOTAL_SPREADS = 8  # 16 pages (2 pages per spread)
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
    summary_rows: list[tuple[str, str, int, float, float, float, float, int]] = []
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

            for level in LEVELS:
                for lang in LANGS:
                    url = f"{base_url}?story=sardegna&mode={level}&lang={lang}"
                    page.goto(url, wait_until="networkidle")
                    page.wait_for_selector(".kids-sentence-box", timeout=10000)
                    page.evaluate("() => document.fonts ? document.fonts.ready : Promise.resolve()")

                    fonts: list[float] = []
                    fills: list[float] = []
                    overflow_count = 0

                    for spread_idx in range(TOTAL_SPREADS):
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

                        if not metrics:
                            failures.append(f"[{level}/{lang}] spread {spread_idx + 1}: no metrics returned")
                            continue

                        for m in metrics:
                            fonts.append(m["fontSizePx"])
                            fills.append(m["fillRatio"])
                            if not m["fits"] or m["overflowY"] > MAX_OVERFLOW_PX or m["overflowX"] > MAX_OVERFLOW_PX:
                                overflow_count += 1
                                failures.append(
                                    f"OVERFLOW [{level}/{lang}] P{m['page']:02d}: "
                                    f"font={m['fontSizePx']}px scrollH={m['scrollHeight']} > clientH={m['clientHeight']} "
                                    f"(overflowY={m['overflowY']}px, overflowX={m['overflowX']}px)"
                                )
                            if m["fillRatio"] < MIN_FILL_RATIO:
                                failures.append(
                                    f"UNDERFILL [{level}/{lang}] P{m['page']:02d}: "
                                    f"font={m['fontSizePx']}px fillRatio={m['fillRatio']:.2f} < {MIN_FILL_RATIO}"
                                )

                    if fonts and fills:
                        summary_rows.append(
                            (
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
            # Verify Left Page == Book Language and Right Page == Translation Language (including EN!)
            parallel_pairs = [
                ("it", "en"),
                ("fr", "en"),
                ("de", "en"),
                ("de", "it"),
                ("fr", "it"),
                ("it", "fr"),
            ]
            parallel_checked = 0
            for book_lang, tr_lang in parallel_pairs:
                url = f"{base_url}?story=sardegna&mode=emma&lang={book_lang}&parallel=1"
                page.goto(url, wait_until="networkidle")
                page.wait_for_selector(".kids-sentence-box", timeout=10000)
                page.evaluate("(tr) => { if (typeof setKidsTranslationLang === 'function') setKidsTranslationLang(tr); }", tr_lang)
                page.wait_for_timeout(80)
                page.evaluate("() => { if (typeof fitKidsTextToPatch === 'function') fitKidsTextToPatch(); }")
                metrics = page.evaluate("() => window.__kidsTextFitMetrics ? window.__kidsTextFitMetrics() : []")
                badges = page.evaluate(
                    "() => Array.from(document.querySelectorAll('#openBookSpread .kids-book-page-num')).map(el => el.textContent.trim())"
                )
                parallel_checked += 1
                if len(metrics) != 2:
                    failures.append(f"PARALLEL [{book_lang}->{tr_lang}]: expected 2 facing pages, got {len(metrics)}")
                    continue
                left_m, right_m = metrics[0], metrics[1]
                if left_m["page"] != right_m["page"]:
                    failures.append(f"PARALLEL [{book_lang}->{tr_lang}]: page mismatch SX={left_m['page']} vs DX={right_m['page']}")
                if left_m["lang"] != book_lang:
                    failures.append(f"PARALLEL [{book_lang}->{tr_lang}]: SX lang={left_m['lang']} != expected {book_lang}")
                if right_m["lang"] != tr_lang:
                    failures.append(f"PARALLEL [{book_lang}->{tr_lang}]: DX lang={right_m['lang']} != expected {tr_lang}")
                expected_badges = [f"1 · {book_lang.upper()}", f"1 · {tr_lang.upper()}"]
                if badges != expected_badges:
                    failures.append(f"PARALLEL [{book_lang}->{tr_lang}]: badges={badges} != expected {expected_badges}")
                for side_lbl, m in (("SX", left_m), ("DX", right_m)):
                    if not m["fits"] or m["overflowY"] > MAX_OVERFLOW_PX or m["overflowX"] > MAX_OVERFLOW_PX:
                        failures.append(
                            f"PARALLEL OVERFLOW [{book_lang}->{tr_lang}] {side_lbl}: "
                            f"scrollH={m['scrollHeight']} > clientH={m['clientHeight']}"
                        )

            # Mobile Portrait (390×844) Single-Page Mode & Face Keep-Out Island unit tests (GitHub Issue #8):
            mobile_ctx = browser.new_context(viewport={"width": 390, "height": 844})
            mpage = mobile_ctx.new_page()
            for level in LEVELS:
                test_lang = "de" if level == "ale" else ("fr" if level == "emma" else "it")
                url = f"{base_url}?story=sardegna&mode={level}&lang={test_lang}"
                mpage.goto(url, wait_until="networkidle")
                mpage.wait_for_selector(".kids-sentence-box", timeout=10000)
                mpage.evaluate("() => document.fonts ? document.fonts.ready : Promise.resolve()")

                is_single = mpage.evaluate(
                    "() => document.getElementById('openBookSpread')?.classList.contains('kids-single-page-mode') === true"
                )
                if not is_single:
                    failures.append(f"MOBILE [{level}]: expected #openBookSpread.kids-single-page-mode on 390x844 viewport")

                for page_idx in range(16):
                    if page_idx > 0:
                        mpage.evaluate("() => turnPage(1)")
                    mpage.wait_for_timeout(60)
                    mpage.evaluate("() => { if (typeof fitKidsTextToPatch === 'function') fitKidsTextToPatch(); }")
                    m_metrics = mpage.evaluate("() => window.__kidsTextFitMetrics ? window.__kidsTextFitMetrics() : []")
                    b_metrics = mpage.evaluate("() => window.__kidsBubbleOverlapMetrics ? window.__kidsBubbleOverlapMetrics() : []")
                    mobile_pages_checked += 1
                    if len(m_metrics) != 1:
                        failures.append(f"MOBILE [{level}] P{page_idx + 1:02d}: expected 1 single page leaf, got {len(m_metrics)}")
                        continue
                    mm = m_metrics[0]
                    if mm["page"] != page_idx + 1:
                        failures.append(f"MOBILE [{level}]: turnPage(1) expected page {page_idx + 1}, got {mm['page']}")
                    if mm["overflowX"] > MAX_OVERFLOW_PX:
                        failures.append(
                            f"MOBILE HORIZONTAL OVERFLOW [{level}] P{mm['page']:02d}: overflowX={mm['overflowX']}px"
                        )
                    for bm in b_metrics:
                        if bm.get("overlapsFace"):
                            failures.append(
                                f"MOBILE FACE OVERLAP [{level}/{test_lang}] P{bm['page']:02d}: "
                                f"bubble rect={bm['rect']} overlaps face keep-out island (area={bm['overlapArea']})"
                            )
            mobile_ctx.close()

            browser.close()
    finally:
        httpd.shutdown()

    print("\n📐 Kids' Own Stories — Bounding-Box Text Auto-Fit & Mobile Single-Page Report")
    print("-" * 78)
    print(f"{'Level':<7} {'Lang':<5} {'Pages':<6} {'Font min/avg (px)':<20} {'Fill min/avg':<18} {'Overflows':<9}")
    print("-" * 78)
    for level, lang, count, f_min, f_avg, fill_min, fill_avg, ov in summary_rows:
        status = "✅ 0" if ov == 0 else f"❌ {ov}"
        print(f"{level:<7} {lang:<5} {count:<6} {f_min:5.1f} / {f_avg:5.1f} px     {fill_min:4.0%} / {fill_avg:4.0%}        {status}")
    print("-" * 78)

    if failures:
        print(f"\n❌ {len(failures)} bounding-box check(s) failed:")
        for err in failures[:25]:
            print(f"  - {err}")
        if len(failures) > 25:
            print(f"  ... and {len(failures) - 25} more")
        return 1

    print(
        f"\n✅ ALL {sum(r[2] for r in summary_rows)} desktop page renderings + {mobile_pages_checked} mobile portrait single-page renderings passed with 0 overflows!"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
