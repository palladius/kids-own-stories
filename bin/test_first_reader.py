#!/usr/bin/env python3
"""
Automated Playwright E2E & Chunker Test Suite for Layer-1 First Reader Mode
(Septober #242 / GHI #4 — "Primi Passi 0.9x").

Verifies:
  1. Backward compatibility: bare `?story=<slug>` opens standard Layer-1 mode at 1.1x.
  2. 1-click launch from Index card (`.first-reader-card-launch-btn`) and permalink `?firstreader=1`.
  3. Giant didactic typography (`fontSize >= 24px`), large touch buttons (`height >= 56px`),
     and uppercase (`STAMPATELLO MAIUSCOLO`) toggle.
  4. Slow karaoke speed (`0.9x` on `currentPlaybackSpeed`, `#playbackSpeedSelect`, and `#narratorAudio`).
  5. Universal chunker invariant across ALL 7 stories × 5 languages (`it, en, fr, de, pt`):
     100% of phrases have `1 <= wordCount <= 12`.
  6. Autonomous reader advance button (`#firstReaderNextBtn` "✅ Ho letto! ➔") steps phrase-by-phrase
     and flips to Page 2 (`Frase 1 / M`) after the final phrase of Page 1.
  7. Toggle OFF restores standard prose and `1.1x` playback speed cleanly.

Usage:
  uv run --with playwright python3 bin/test_first_reader.py
  # or via just:
  just test-first-reader
"""

from __future__ import annotations

import functools
import glob
import http.server
import os
import socketserver
import sys
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

REPO_ROOT = Path(__file__).resolve().parent.parent

# Prevent Chromium SingletonSocket >108-byte path overflow when harness sets a deep TMPDIR
if len(os.environ.get("TMPDIR", "")) > 48:
    os.environ["TMPDIR"] = "/tmp"


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:  # noqa: A002
        pass


class QuietThreadingTCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def handle_error(self, request, client_address) -> None:
        exc = sys.exc_info()[1]
        if isinstance(exc, (BrokenPipeError, ConnectionResetError)):
            return
        super().handle_error(request, client_address)


def start_static_server(root: Path) -> tuple[socketserver.TCPServer, int]:
    handler = functools.partial(QuietHandler, directory=str(root))
    httpd = QuietThreadingTCPServer(("127.0.0.1", 0), handler)
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return httpd, port


def launch_browser(p):
    try:
        return p.chromium.launch(headless=True)
    except Exception:
        cached = sorted(
            glob.glob(
                str(Path.home() / ".cache/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-linux64/chrome-headless-shell")
            ),
            reverse=True,
        )
        if cached:
            return p.chromium.launch(headless=True, executable_path=cached[0])
        return p.chromium.launch(headless=True, channel="chrome")


def main() -> int:
    httpd, port = start_static_server(REPO_ROOT)
    base_url = f"http://127.0.0.1:{port}"
    failures: list[str] = []
    checks_passed = 0

    def record(ok: bool, msg: str) -> None:
        nonlocal checks_passed
        if ok:
            checks_passed += 1
        else:
            failures.append(msg)
            print(f"  ❌ FAIL: {msg}")

    try:
        with sync_playwright() as p:
            browser = launch_browser(p)
            context = browser.new_context(viewport={"width": 1440, "height": 900})
            page = context.new_page()
            js_errors: list[str] = []
            page.on("pageerror", lambda err: js_errors.append(str(err)))

            # 1. Bare ?story=<slug> opens standard Layer-1 (backward compatibility)
            pony_slug = "storia-sebi-campione-pony-club-pupurabbu"
            page.goto(f"{base_url}/?story={pony_slug}", wait_until="networkidle")
            m0 = page.evaluate("window.__firstReaderMetrics()")
            record(m0["enabled"] is False, f"Bare ?story= should have firstReaderEnabled=False, got {m0}")
            record(m0["cardVisible"] is False, "Bare ?story= should not render .first-reader-card")
            record(abs(m0["playbackSpeed"] - 1.1) < 0.01, f"Default playbackSpeed expected 1.1, got {m0['playbackSpeed']}")

            # 2. Index grid renders 1-click First Reader launch button on every story card
            page.goto(f"{base_url}/#indice", wait_until="networkidle")
            card_btns = page.locator("#indexGrid .first-reader-card-launch-btn")
            total_stories = page.evaluate("(catalog && catalog.stories) ? catalog.stories.length : 0")
            record(
                card_btns.count() == total_stories and total_stories >= 7,
                f"Expected {total_stories} .first-reader-card-launch-btn on index cards, got {card_btns.count()}",
            )

            # Click First Reader button on Cavalletto Marie story (#224)
            marie_slug = "storia-cavalletto-marie-mondo-cavalli"
            page.evaluate(f"launchFirstReaderStory('{marie_slug}')")
            page.wait_for_selector("#openBookSpread .first-reader-card", timeout=5000)

            m1 = page.evaluate("window.__firstReaderMetrics()")
            url_now = page.url
            audio_rate = page.evaluate("document.getElementById('narratorAudio')?.playbackRate || 0")
            speed_sel = page.evaluate("document.getElementById('playbackSpeedSelect')?.value || ''")

            record("firstreader=1" in url_now, f"URL should contain firstreader=1, got {url_now}")
            record(m1["enabled"] is True and m1["cardVisible"] is True, f"First Reader card not visible: {m1}")
            record(1 <= m1["wordCount"] <= 12, f"Chunk wordCount out of [1, 12]: {m1}")
            record(m1["fontSizePx"] >= 24.0, f"Expected giant font >= 24px, got {m1['fontSizePx']}px")
            record(m1["listenBtnHeightPx"] >= 56.0, f"Expected listen button height >= 56px, got {m1['listenBtnHeightPx']}px")
            record(m1["nextBtnHeightPx"] >= 56.0, f"Expected next button height >= 56px, got {m1['nextBtnHeightPx']}px")
            record(abs(m1["playbackSpeed"] - 0.9) < 0.01, f"Expected playbackSpeed 0.9, got {m1['playbackSpeed']}")
            record(abs(audio_rate - 0.9) < 0.01, f"Expected narratorAudio.playbackRate 0.9, got {audio_rate}")
            record(speed_sel == "0.9", f"Expected #playbackSpeedSelect='0.9', got '{speed_sel}'")
            record(m1["stepPill"].startswith("🧒 Frase 1 /"), f"Unexpected stepPill on phrase 1: '{m1['stepPill']}'")

            # 3. Exhaustive chunker check across ALL stories × ALL 5 languages inside real browser engine
            chunk_audit = page.evaluate(
                """async () => {
                    const savedLang = currentLang;
                    const langs = ['it', 'en', 'fr', 'de', 'pt'];
                    const stories = catalog?.stories || [];
                    let totalChunks = 0;
                    let maxWordsSeen = 0;
                    const violations = [];
                    for (const s of stories) {
                      for (const lang of langs) {
                        currentLang = lang;
                        const kData = await ensureKaraokeLoaded(s, lang);
                        const slides = getSlidesForStory(s).filter(sl => sl.type !== 'video');
                        slides.forEach((sl, pIdx) => {
                          const kPage = kData?.pages?.[pIdx] || null;
                          const chunks = buildFirstReaderChunks(sl.paragraphs || [], kPage, 12);
                          chunks.forEach((c, cIdx) => {
                            totalChunks++;
                            if (c.wordCount > maxWordsSeen) maxWordsSeen = c.wordCount;
                            if (c.wordCount < 1 || c.wordCount > 12) {
                              violations.push(`${s.slug} [${lang}] p.${pIdx+1} c.${cIdx+1}: ${c.wordCount} words (${c.text})`);
                            }
                          });
                        });
                      }
                    }
                    currentLang = savedLang;
                    return { totalStories: stories.length, totalChunks, maxWordsSeen, violations };
                }"""
            )
            record(
                len(chunk_audit["violations"]) == 0 and chunk_audit["totalChunks"] > 1500,
                f"Chunker violations found: {chunk_audit}",
            )
            print(
                f"  ✅ Chunker audited {chunk_audit['totalChunks']} phrases across "
                f"{chunk_audit['totalStories']} stories × 5 langs (maxWordsSeen={chunk_audit['maxWordsSeen']} <= 12)"
            )

            # 4. Uppercase toggle ("STAMPATELLO MAIUSCOLO")
            page.click("#openBookSpread .first-reader-case-btn")
            m_upper = page.evaluate("window.__firstReaderMetrics()")
            text_transform = page.evaluate(
                "window.getComputedStyle(document.querySelector('#openBookSpread .first-reader-sentence')).textTransform"
            )
            record(m_upper["uppercase"] is True and text_transform == "uppercase", f"Uppercase toggle failed: {m_upper}, {text_transform}")
            page.click("#openBookSpread .first-reader-case-btn")

            # 5. Autonomous advance button ("✅ Ho letto! ➔") advances through all Page 1 phrases and flips to Page 2
            total_p1_chunks = int(
                page.locator("#openBookSpread .first-reader-card").get_attribute("data-total-chunks") or "0"
            )
            record(total_p1_chunks >= 3, f"Expected >= 3 chunks on Page 1 of {marie_slug}, got {total_p1_chunks}")

            page.click("#firstReaderNextBtn")
            m2 = page.evaluate("window.__firstReaderMetrics()")
            record(m2["stepPill"].startswith(f"🧒 Frase 2 / {total_p1_chunks}"), f"Expected Frase 2 / {total_p1_chunks}, got '{m2['stepPill']}'")

            # Click remaining phrases on Page 1 to trigger celebratory flip to Page 2
            for _ in range(total_p1_chunks - 1):
                page.click("#firstReaderNextBtn")
            page.wait_for_timeout(150)

            m_p2 = page.evaluate("window.__firstReaderMetrics()")
            record(m_p2["pageNum"] == 2, f"Expected auto-flip to Page 2 after reading Page 1, got pageNum={m_p2['pageNum']}")
            record(m_p2["stepPill"].startswith("🧒 Frase 1 /"), f"Expected Page 2 to start at Frase 1, got '{m_p2['stepPill']}'")

            # 6. Direct permalink ?story=<slug>&firstreader=1&lang=en (verifies British English en-GB label "Well done!" / "Listen (0.9x)")
            page.goto(f"{base_url}/?story={pony_slug}&firstreader=1&lang=en", wait_until="networkidle")
            m_en = page.evaluate("window.__firstReaderMetrics()")
            listen_txt = page.locator("#firstReaderListenBtn").inner_text()
            next_txt = page.locator("#firstReaderNextBtn").inner_text()
            record(m_en["enabled"] is True and m_en["cardVisible"] is True, f"Direct ?firstreader=1 permalink failed: {m_en}")
            record("Listen (0.9x)" in listen_txt and "I read it!" in next_txt, f"Unexpected EN button labels: '{listen_txt}' / '{next_txt}'")

            # 7. Toggle OFF via #firstReaderToggleBtn restores standard prose & 1.1x speed
            page.click("#firstReaderToggleBtn")
            m_off = page.evaluate("window.__firstReaderMetrics()")
            record(m_off["enabled"] is False and m_off["cardVisible"] is False, f"Toggle OFF did not exit First Reader Mode: {m_off}")
            record("firstreader=1" not in page.url, f"Toggle OFF should remove firstreader=1 from URL, got {page.url}")
            record(abs(m_off["playbackSpeed"] - 1.1) < 0.01, f"Toggle OFF should restore 1.1x speed, got {m_off['playbackSpeed']}")

            # 8. Mobile portrait viewport (390×844) ergonomics check
            mobile_page = browser.new_page(viewport={"width": 390, "height": 844})
            mobile_page.on("pageerror", lambda err: js_errors.append(f"mobile: {err}"))
            mobile_page.goto(f"{base_url}/?story={pony_slug}&firstreader=1", wait_until="networkidle")
            m_mob = mobile_page.evaluate("window.__firstReaderMetrics()")
            record(m_mob["cardVisible"] is True and m_mob["fontSizePx"] >= 24.0, f"Mobile First Reader typography check failed: {m_mob}")
            record(m_mob["nextBtnHeightPx"] >= 56.0, f"Mobile nextBtn height < 56px: {m_mob}")

            # 9. Standalone story pages (stories/*/*/index.html): zero 67px audio collapse & valid metadata
            for shp in sorted((REPO_ROOT / "stories").glob("*/*/index.html")):
                sh_txt = shp.read_text(encoding="utf-8")
                if 'http-equiv="refresh"' in sh_txt.lower():
                    continue
                rel_url = shp.relative_to(REPO_ROOT).as_posix()
                page.goto(f"{base_url}/{rel_url}", wait_until="domcontentloaded")
                page.evaluate("document.querySelectorAll('details').forEach(d => d.open = true)")
                page.wait_for_function(
                    "() => Array.from(document.querySelectorAll('audio')).every(a => a.readyState >= 1)",
                    timeout=8000,
                )
                aud_metrics = page.evaluate(
                    """() => Array.from(document.querySelectorAll('audio')).map(a => ({
                        src: a.currentSrc.split('/').pop(),
                        ready: a.readyState,
                        dur: a.duration || 0,
                        w: Math.round(a.getBoundingClientRect().width),
                        h: Math.round(a.getBoundingClientRect().height)
                    }))"""
                )
                record(len(aud_metrics) >= 3, f"{rel_url}: expected >= 3 <audio> players, got {aud_metrics}")
                for am in aud_metrics:
                    record(
                        am["w"] >= 260 and am["h"] >= 40 and am["ready"] >= 1 and am["dur"] > 10,
                        f"{rel_url} audio collapsed or failed to load: {am}",
                    )

            record(len(js_errors) == 0, f"Uncaught JS page errors: {js_errors}")
            browser.close()
    finally:
        httpd.shutdown()

    if failures:
        print(f"\n❌ First Reader Mode suite FAILED ({len(failures)} failures, {checks_passed} passed).")
        return 1

    print(f"\n🎉 First Reader Mode Playwright suite PASSED ({checks_passed}/{checks_passed} checks green)!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
