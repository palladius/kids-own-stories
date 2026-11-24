#!/usr/bin/env python3
"""
Opaque-Box Playwright E2E Test Suite for Kids' Own Stories Multi-Book Reader.

Covers 142 requirement-driven tests across Tiers 1-4 and all 12 feature areas (F1-F12):
  - Tier 1 (61): 5 single-feature tests per area F1-F12 (+ Escape bookmark-save/exit under F3)
  - Tier 2 (61): 5 boundary/corner-case tests per area F1-F12 (+ Escape overlay precedence under F3)
  - Tier 3 (13): Pairwise cross-feature combination tests
  - Tier 4 (7):  Realistic end-to-end family scenarios

Usage:
  uv run --with playwright --with pyyaml python3 bin/test_e2e_multibook.py
  python3 bin/test_e2e_multibook.py --help
  python3 bin/test_e2e_multibook.py --list
  python3 bin/test_e2e_multibook.py --book sardegna --baseline
"""

from __future__ import annotations

import argparse
import functools
import http.server
import json
import os
import re
import shutil
import socket
import struct
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

# ---------------------------------------------------------------------------
# Auto-reexec under `uv run --with playwright --with pyyaml` when invoked with
# bare python3 (after --help / --list fast paths if needed).
# ---------------------------------------------------------------------------
def _ensure_runtime_deps() -> None:
    if any(flag in sys.argv[1:] for flag in ("-h", "--help", "--list")):
        return
    missing = False
    try:
        import playwright  # noqa: F401
        import yaml  # noqa: F401
    except ImportError:
        missing = True

    if not missing:
        return
    if os.environ.get("KOS_UV_REEXEC") == "1":
        print(
            "❌ Missing required packages (playwright, pyyaml) even after uv re-exec.",
            file=sys.stderr,
        )
        sys.exit(1)
    uv_bin = shutil.which("uv")
    if not uv_bin:
        print(
            "❌ Neither system playwright/pyyaml nor `uv` was found. "
            "Run via: uv run --with playwright --with pyyaml python3 bin/test_e2e_multibook.py",
            file=sys.stderr,
        )
        sys.exit(1)

    env = dict(os.environ)
    env["KOS_UV_REEXEC"] = "1"
    default_uv_cache = Path.home() / ".cache" / "uv"
    if "UV_CACHE_DIR" not in env:
        probe_path = default_uv_cache
        while not probe_path.exists() and probe_path != probe_path.parent:
            probe_path = probe_path.parent
        writable = (
            os.access(default_uv_cache, os.W_OK)
            if default_uv_cache.exists()
            else os.access(probe_path, os.W_OK)
        )
        enough_space = False
        if writable:
            try:
                enough_space = shutil.disk_usage(probe_path).free >= (1024 ** 3)
            except OSError:
                enough_space = False
        if not writable or not enough_space:
            env["UV_CACHE_DIR"] = "/tmp/uv-cache"
            env.setdefault("UV_LINK_MODE", "copy")
            env.setdefault("UV_INDEX_URL", "https://pypi.org/simple")
    os.execvpe(
        uv_bin,
        [uv_bin, "run", "--with", "playwright", "--with", "pyyaml", "python3", *sys.argv],
        env,
    )


_ensure_runtime_deps()

REPO_ROOT = Path(__file__).resolve().parent.parent
SARDEGNA_ID = "storia-sardegna-cala-gonone-arbatax-famiglia"
PETIT_PRINCE_ID = "le-petit-prince"
MIN_FILL_RATIO = 0.42
MAX_OVERFLOW_PX = 2


class SkipTest(Exception):
    """Raised when a test is intentionally skipped (e.g. --book filter or --baseline)."""


# ---------------------------------------------------------------------------
# Pure-Python JPEG header parser (avoids requiring Pillow at runtime)
# ---------------------------------------------------------------------------
def parse_jpeg_info(path: Path) -> tuple[int, int, int]:
    """Return (width, height, num_components) from a complete JPEG file (SOF + SOS + EOI)."""
    data = path.read_bytes()
    if len(data) < 4 or data[:2] != b"\xff\xd8":
        raise ValueError(f"{path} is not a valid JPEG (missing SOI)")
    i = 2
    n = len(data)
    sof_info: tuple[int, int, int] | None = None
    has_sos = False
    has_eoi = data.rstrip().endswith(b"\xff\xd9")
    while i < n:
        if data[i] != 0xFF:
            i += 1
            continue
        while i < n and data[i] == 0xFF:
            i += 1
        if i >= n:
            break
        marker = data[i]
        i += 1
        if marker in (0x01, 0xD8) or (0xD0 <= marker <= 0xD7):
            continue
        if marker == 0xD9:
            has_eoi = True
            break
        if marker == 0xDA:
            has_sos = True
            break
        if i + 2 > n:
            break
        seg_len = struct.unpack(">H", data[i : i + 2])[0]
        if seg_len < 2:
            raise ValueError(f"Invalid JPEG segment length {seg_len} in {path}")
        if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
            if i + 7 > n:
                break
            height, width, comps = struct.unpack(">HHB", data[i + 3 : i + 8])
            sof_info = (width, height, comps)
        i += seg_len
    if sof_info is None:
        raise ValueError(f"Could not find SOF dimensions in {path}")
    if not has_sos:
        raise ValueError(f"{path} is truncated JPEG (missing SOS marker)")
    if not has_eoi:
        raise ValueError(f"{path} is truncated JPEG (missing EOI marker)")
    return sof_info


# ---------------------------------------------------------------------------
# Embedded HTTP/1.1 RangeRequestHandler on 127.0.0.1:0
# ---------------------------------------------------------------------------
class RangeRequestHandler(http.server.SimpleHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        pass

    def end_headers(self) -> None:
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def send_head(self):
        path = self.translate_path(self.path)
        if os.path.isdir(path):
            return super().send_head()
        if not os.path.exists(path):
            self.send_error(404, "File not found")
            return None

        range_header = self.headers.get("Range")
        if not range_header:
            return super().send_head()

        m = re.match(r"bytes=(\d+)-(\d*)", range_header)
        if not m:
            return super().send_head()

        f = open(path, "rb")
        fs = os.fstat(f.fileno())
        file_len = fs.st_size
        start = int(m.group(1))
        end = int(m.group(2)) if m.group(2) else file_len - 1
        end = min(end, file_len - 1)
        if start >= file_len or start > end:
            f.close()
            self.send_error(416, "Requested Range Not Satisfiable")
            return None

        length = end - start + 1
        ctype = self.guess_type(path)
        self.send_response(206, "Partial Content")
        self.send_header("Content-type", ctype)
        self.send_header("Content-Range", f"bytes {start}-{end}/{file_len}")
        self.send_header("Content-Length", str(length))
        self.send_header("Last-Modified", self.date_time_string(fs.st_mtime))
        self.end_headers()
        f.seek(start)
        self._range_remaining = length
        return f

    def copyfile(self, source, outputfile) -> None:
        remaining = getattr(self, "_range_remaining", None)
        if remaining is None:
            return super().copyfile(source, outputfile)
        self._range_remaining = None
        bufsize = 64 * 1024
        while remaining > 0:
            chunk = source.read(min(bufsize, remaining))
            if not chunk:
                break
            outputfile.write(chunk)
            remaining -= len(chunk)


class QuietThreadingHTTPServer(http.server.ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True

    def handle_error(self, request, client_address) -> None:
        _, exc, _ = sys.exc_info()
        if isinstance(exc, (ConnectionResetError, BrokenPipeError)):
            return
        super().handle_error(request, client_address)


def start_range_server(root: Path) -> tuple[http.server.ThreadingHTTPServer, int]:
    handler = functools.partial(RangeRequestHandler, directory=str(root))
    httpd = QuietThreadingHTTPServer(("127.0.0.1", 0), handler)
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return httpd, port


# ---------------------------------------------------------------------------
# Browser Session & Network / Console / SpeechSynthesis Spy
# ---------------------------------------------------------------------------
SPEECH_SPY_INIT_JS = """
(() => {
  window.__kosTtsCalls = [];
  const wrapSpeak = (obj) => {
    if (!obj || obj.__kosSpied) return false;
    const orig = typeof obj.speak === 'function' ? obj.speak.bind(obj) : null;
    try {
      Object.defineProperty(obj, 'speak', {
        configurable: true,
        writable: true,
        value: function(utterance) {
          window.__kosTtsCalls.push({
            text: utterance ? String(utterance.text || '') : '',
            lang: utterance ? String(utterance.lang || '') : '',
            rate: utterance ? Number(utterance.rate) : null,
            ts: Date.now()
          });
          if (orig) {
            try { return orig(utterance); } catch (_) {}
          }
        }
      });
      obj.__kosSpied = true;
      return true;
    } catch (_) {
      return false;
    }
  };
  if (typeof window.speechSynthesis !== 'undefined') {
    wrapSpeak(window.speechSynthesis);
  }
  if (typeof window.SpeechSynthesis !== 'undefined' && window.SpeechSynthesis.prototype) {
    wrapSpeak(window.SpeechSynthesis.prototype);
  }
})();
"""


@dataclass
class PageRecorder:
    pageerrors: list[str] = field(default_factory=list)
    console_errors: list[tuple[str, str]] = field(default_factory=list)
    bad_responses: list[tuple[int, str]] = field(default_factory=list)
    audio_requests: list[str] = field(default_factory=list)
    mp3_range_statuses: list[tuple[int, str]] = field(default_factory=list)

    def clear(self) -> None:
        self.pageerrors.clear()
        self.console_errors.clear()
        self.bad_responses.clear()
        self.audio_requests.clear()
        self.mp3_range_statuses.clear()


def attach_listeners(page, base_url_prefix: str) -> PageRecorder:
    rec = PageRecorder()

    def on_pageerror(err) -> None:
        rec.pageerrors.append(str(err))

    def on_console(msg) -> None:
        if msg.type == "error":
            loc = msg.location if isinstance(msg.location, dict) else {}
            rec.console_errors.append((msg.text, str(loc.get("url", "") or "")))

    def on_request(req) -> None:
        url = req.url
        if re.search(r"\.(mp3|ogg)(\?|$)", url, re.IGNORECASE):
            rec.audio_requests.append(url)

    def on_response(resp) -> None:
        url = resp.url
        status = resp.status
        path_only = url.split("?", 1)[0]
        if url.startswith(base_url_prefix) and status >= 400:
            if path_only.endswith("/favicon.ico"):
                pass
            elif path_only.startswith(f"{base_url_prefix}/v1/") and status in (404, 501):
                # Static test server has no Puffin backend API (/v1/whoami, /v1/scores, /v1/cards, /v1/logins);
                # exempt local /v1/* 404/501 responses so real puffin-login.js offline fallback executes cleanly.
                pass
            else:
                rec.bad_responses.append((status, url))
        if re.search(r"\.(mp3|ogg)(\?|$)", url, re.IGNORECASE):
            rec.mp3_range_statuses.append((status, url))

    page.on("pageerror", on_pageerror)
    page.on("console", on_console)
    page.on("request", on_request)
    page.on("response", on_response)
    rec._base_url_prefix = base_url_prefix  # type: ignore[attr-defined]
    return rec


def check_clean_page(
    rec: PageRecorder,
    *,
    allow_offline_console: bool = False,
    allow_baseline_puffin_error: bool = False,
    strict_puffin_error: bool = False,
) -> None:
    errs = list(rec.pageerrors)
    if allow_baseline_puffin_error and not strict_puffin_error:
        errs = [e for e in errs if "Cannot use import statement outside a module" not in e]
    if errs:
        raise AssertionError(f"Uncaught pageerror(s): {errs}")
    if rec.bad_responses and not allow_offline_console:
        raise AssertionError(f"Broken local asset HTTP response(s): {rec.bad_responses}")
    if not allow_offline_console:
        base_prefix = getattr(rec, "_base_url_prefix", "")
        serious_console: list[str] = []
        for msg_text, loc_url in rec.console_errors:
            loc_path = loc_url.split("?", 1)[0]
            if "favicon.ico" in msg_text or loc_path.endswith("/favicon.ico"):
                continue
            if "ERR_INTERNET_DISCONNECTED" in msg_text:
                continue
            if base_prefix and loc_path.startswith(f"{base_prefix}/v1/") and ("404" in msg_text or "501" in msg_text):
                continue
            if allow_baseline_puffin_error and not strict_puffin_error and "404 (File not found)" in msg_text:
                continue
            serious_console.append(f"{msg_text} ({loc_url})" if loc_url else msg_text)
        if serious_console:
            raise AssertionError(f"Console error(s): {serious_console}")


class RunnerEnv:
    def __init__(self, browser, base_url: str, base_origin: str, args: argparse.Namespace) -> None:
        self.browser = browser
        self.base_url = base_url
        self.base_origin = base_origin
        self.args = args

    @property
    def baseline(self) -> bool:
        return bool(self.args.baseline)

    def new_session(
        self,
        viewport: dict[str, int] | None = None,
        offline: bool = False,
    ):
        ctx = self.browser.new_context(viewport=viewport or {"width": 1440, "height": 900})
        ctx.add_init_script(SPEECH_SPY_INIT_JS)
        if offline:
            ctx.set_offline(True)
        page = ctx.new_page()
        rec = attach_listeners(page, self.base_origin)
        return ctx, page, rec

    def goto_reader(
        self,
        page,
        query: str = "",
        wait_selector: str | None = ".kids-sentence-box",
        wait_until: str = "networkidle",
        dismiss_puffin_modal: bool = True,
    ) -> None:
        url = f"{self.base_url}{query}"
        page.goto(url, wait_until=wait_until)
        if wait_selector:
            page.wait_for_selector(wait_selector, timeout=10000)
        page.evaluate("() => document.fonts ? document.fonts.ready : Promise.resolve()")
        page.wait_for_timeout(120)
        if dismiss_puffin_modal:
            # Only act if PuffinLogin opened a top-layer blocking <dialog> (e.g. requireLogin: true)
            # so genuine unauthenticated state (require-login="false") is untouched.
            page.evaluate(
                """() => {
                    const w = document.getElementById('puffin-widget');
                    const dlg = w?.shadowRoot?.querySelector('dialog');
                    if (dlg && dlg.open) {
                        if (window.PuffinLogin && typeof window.PuffinLogin.loginAsGuest === 'function') {
                            window.PuffinLogin.loginAsGuest('Reader');
                        }
                        if (dlg.open) dlg.close();
                    }
                }"""
            )

    def has_petit_prince_assets(self) -> bool:
        return (REPO_ROOT / "books" / "petit-prince" / "kids_book_data.json").exists()

    def has_constitution(self) -> bool:
        return (REPO_ROOT / "docs" / "CONSTITUTION.md").exists()

    def has_bookshelf(self) -> bool:
        return (REPO_ROOT / "books" / "index.html").exists()

    def require_m1_m3(self, condition: bool, reason: str) -> None:
        if not condition:
            if self.baseline:
                raise SkipTest(f"pre-M1/M3 baseline: {reason}")
            raise AssertionError(reason)

    def require_m5(self, condition: bool, reason: str) -> None:
        if not condition:
            if self.baseline:
                raise SkipTest(f"pre-M5 baseline: {reason}")
            raise AssertionError(reason)


# ---------------------------------------------------------------------------
# Opaque-Box UI Helpers (re-query DOM dynamically after every render)
# ---------------------------------------------------------------------------
def is_kids_fullscreen(page) -> bool:
    return bool(page.evaluate("() => document.body.classList.contains('kids-fullscreen-book')"))


def get_active_book_info(page) -> dict[str, Any]:
    return page.evaluate(
        """() => {
            const leaves = Array.from(document.querySelectorAll('#openBookSpread .kids-watercolor-leaf'));
            const imgs = leaves.map(el => el.style.backgroundImage || '');
            const pages = leaves.map(el => Number(el.dataset.page || 0));
            const langs = leaves.map(el => el.getAttribute('lang') || '');
            const badges = Array.from(document.querySelectorAll('#openBookSpread .kids-book-page-num')).map(el => el.textContent.trim());
            const cat = window.KIDS_BOOKS_CATALOG || {};
            const activeSlug = typeof activeTab !== 'undefined' ? activeTab : null;
            const kb = activeSlug ? cat[activeSlug] : null;
            return {
                activeTab: activeSlug,
                storyId: kb?.story_id || activeSlug,
                totalPages: kb?.total_pages || kb?.pages?.length || 0,
                supportedLangs: kb?.supported_langs || [],
                defaultLang: kb?.default_lang || null,
                mode: typeof kidsBookMode !== 'undefined' ? kidsBookMode : null,
                lang: typeof currentLang !== 'undefined' ? currentLang : null,
                trLang: typeof kidsTranslationLang !== 'undefined' ? kidsTranslationLang : null,
                parallel: typeof kidsParallelMode !== 'undefined' ? Boolean(kidsParallelMode) : false,
                pages,
                langs,
                badges,
                images: imgs,
                catalogKeys: Object.keys(cat),
                url: window.location.href,
            };
        }"""
    )


def ensure_settings_popover(page, open_state: bool = True) -> None:
    pop = page.locator("#kidsSettingsPopover")
    is_vis = pop.is_visible() if pop.count() > 0 else False
    if is_vis != open_state:
        page.locator("#kidsNotebookFloatingBar .kids-settings-wrap > button").first.click()
        if open_state:
            pop.wait_for(state="visible", timeout=4000)
        else:
            pop.wait_for(state="hidden", timeout=4000)


def switch_book_lang(page, lang: str) -> None:
    label_map = {"it": "Italiano", "fr": "Français", "de": "Deutsch"}
    ensure_settings_popover(page, True)
    page.locator(
        f"#kidsSettingsPopover .kids-settings-lang-big-grid button:has-text('{label_map[lang]}')"
    ).first.click()
    page.wait_for_timeout(140)


def switch_translation_lang(page, tr_lang: str) -> None:
    label_map = {"en": "English", "it": "Italiano", "fr": "Français", "de": "Deutsch"}
    ensure_settings_popover(page, True)
    page.locator(
        f"#kidsSettingsPopover .kids-settings-row-small button.kids-pill-control:has-text('{label_map[tr_lang]}')"
    ).first.click()
    page.wait_for_timeout(140)


def set_parallel_mode(page, enabled: bool) -> None:
    is_on = get_active_book_info(page)["parallel"]
    if is_on != enabled:
        page.locator("#kidsNotebookFloatingBar button[aria-label*='Traduzione Pari Pari']").first.click()
        page.wait_for_timeout(150)


def set_grammar_mode(page, enabled: bool) -> None:
    is_on = bool(page.evaluate("() => document.querySelector('#openBookSpread .kids-watercolor-leaf')?.classList.contains('grammar-on')"))
    if is_on != enabled:
        page.locator(
            "#kidsNotebookFloatingBar button[title*='Grammatic'], "
            "#kidsNotebookFloatingBar button[title*='Grammaire'], "
            "#kidsNotebookFloatingBar button[title*='Grammatik']"
        ).first.click()
        page.wait_for_timeout(140)


def set_uppercase_mode(page, enabled: bool) -> None:
    is_on = bool(page.evaluate("() => document.querySelector('#openBookSpread .kids-sentence-box')?.classList.contains('uppercase-mode')"))
    if is_on != enabled:
        page.locator("#kidsNotebookFloatingBar button:has-text('a/A')").first.click()
        page.wait_for_timeout(140)


def set_tier(page, tier: str) -> None:
    cls_map = {"seby": ".tier-easy", "ale": ".tier-medium", "emma": ".tier-hard"}
    page.locator(f"#kidsNotebookFloatingBar {cls_map[tier]}").first.click()
    page.wait_for_timeout(140)


def _js_is_visible_fn() -> str:
    return """
        const isVisible = (el) => {
            if (!el) return false;
            if (el.hidden || el.closest('[hidden]')) return false;
            const st = getComputedStyle(el);
            if (st.display === 'none' || st.visibility === 'hidden' || st.opacity === '0') return false;
            if (el.offsetParent === null && st.position !== 'fixed') return false;
            const r = el.getBoundingClientRect();
            return r.width > 0 && r.height > 0;
        };
    """


def find_book_selector_state(page) -> dict[str, Any]:
    """Opaque-box discovery of a VISIBLE multi-book UI selector in the reader."""
    return page.evaluate(
        """() => {
            """ + _js_is_visible_fn() + """
            const roots = [
                { sel: '#kidsReadingLaunchBar', el: document.getElementById('kidsReadingLaunchBar') },
                { sel: '#kidsNotebookFloatingBar', el: document.getElementById('kidsNotebookFloatingBar') },
                { sel: '#kidsSettingsPopover', el: document.getElementById('kidsSettingsPopover') },
                { sel: 'header.topbar', el: document.querySelector('header.topbar') },
                { sel: '#bookViewport', el: document.getElementById('bookViewport') },
            ].filter(r => r.el && isVisible(r.el));

            const matchBook = (txt, val) => {
                const s = (String(txt || '') + ' ' + String(val || '')).toLowerCase();
                const isSar = /storia-sardegna|sardegn|sardaigne|sardinien|cala gonone|arbatax/.test(s);
                const isPp = /le-petit-prince|petit[\\s_-]*prince|piccolo principe|kleiner prinz/.test(s);
                if (isSar && !isPp) return 'sardegna';
                if (isPp && !isSar) return 'petit-prince';
                return null;
            };

            for (const root of roots) {
                for (const sel of root.el.querySelectorAll('select')) {
                    if (!isVisible(sel)) continue;
                    const opts = Array.from(sel.options).map(o => ({
                        value: o.value,
                        text: o.textContent.trim(),
                        book: matchBook(o.textContent, o.value),
                    }));
                    const books = opts.map(o => o.book).filter(Boolean);
                    if (books.includes('petit-prince') && books.includes('sardegna')) {
                        return { found: true, kind: 'select', rootSel: root.sel, selectId: sel.id || null, books, options: opts };
                    }
                }
                const bookButtons = Array.from(root.el.querySelectorAll('button, a, [role="option"], [role="tab"]'))
                    .filter(el => isVisible(el))
                    .map(el => {
                        const meta = (el.dataset.book || '') + ' ' + (el.getAttribute('aria-label') || '') + ' ' + (el.getAttribute('title') || '') + ' ' + (el.getAttribute('onclick') || '');
                        return {
                            text: (el.textContent || '').trim(),
                            val: meta.trim(),
                            book: matchBook(el.textContent, meta),
                        };
                    })
                    .filter(x => x.book);
                const uniq = Array.from(new Set(bookButtons.map(x => x.book)));
                if (uniq.includes('petit-prince') && uniq.includes('sardegna')) {
                    return { found: true, kind: 'buttons', rootSel: root.sel, books: uniq, options: bookButtons };
                }
            }
            return { found: false, kind: null, rootSel: null, books: [], options: [] };
        }"""
    )


def select_book_in_ui(page, target_book: str) -> None:
    """Switch book using the actual VISIBLE UI Book Selector via Playwright actions."""
    state = find_book_selector_state(page)
    if not state["found"]:
        settings_btn = page.locator("#kidsNotebookFloatingBar .kids-settings-wrap > button").first
        if settings_btn.count() > 0 and settings_btn.is_visible():
            ensure_settings_popover(page, True)
            state = find_book_selector_state(page)
    if not state["found"]:
        raise AssertionError("Visible UI Book Selector listing both Cala Gonone and Le Petit Prince not found")

    if state["kind"] == "select":
        opt = next(o for o in state["options"] if o["book"] == target_book)
        sel_loc = page.locator(f"#{state['selectId']}") if state.get("selectId") else page.locator(f"{state['rootSel']} select").first
        assert sel_loc.is_visible(), f"Book <select> in {state['rootSel']} is not visible"
        sel_loc.select_option(opt["value"])
    else:
        root_sel = state["rootSel"]
        btns = page.locator(f"{root_sel} button, {root_sel} a, {root_sel} [role='option'], {root_sel} [role='tab']")
        clicked = False
        for idx in range(btns.count()):
            btn = btns.nth(idx)
            if not btn.is_visible():
                continue
            matched = btn.evaluate(
                """(el) => {
                    const s = ((el.textContent || '') + ' ' + (el.dataset.book || '') + ' ' + (el.getAttribute('aria-label') || '') + ' ' + (el.getAttribute('title') || '') + ' ' + (el.getAttribute('onclick') || '')).toLowerCase();
                    const isSar = /storia-sardegna|sardegn|sardaigne|sardinien|cala gonone|arbatax/.test(s);
                    const isPp = /le-petit-prince|petit[\\s_-]*prince|piccolo principe|kleiner prinz/.test(s);
                    if (isSar && !isPp) return 'sardegna';
                    if (isPp && !isSar) return 'petit-prince';
                    return null;
                }"""
            )
            if matched == target_book:
                btn.click()
                clicked = True
                break
        if not clicked:
            raise AssertionError(f"Could not click visible UI Book Selector control for {target_book} in {root_sel}")
    page.wait_for_timeout(180)


def find_bookmark_button(page, action: str = "save"):
    """Find VISIBLE bookmark save or resume button via opaque-box semantic attributes."""
    info = page.evaluate(
        """(action) => {
            """ + _js_is_visible_fn() + """
            const roots = [
                document.getElementById('kidsNotebookFloatingBar'),
                document.getElementById('kidsSettingsPopover'),
                document.getElementById('bookViewport'),
            ].filter(Boolean);
            const isDismiss = (s) => /dismiss|chiudi|close/i.test(s);
            const isResume = (s, btn) => !isDismiss(s) && /bookmark-resume-jump|riprendi|resume|vai al segnalibro|restore|apri segnalibro|\b(aller|öffnen|vai)\b/i.test(s) && (
                /bookmark-resume-jump|bookmark|segnalibro|marque-page|lesezeichen|reprendre|riprendi|resume|restore/i.test(s) ||
                Boolean(btn.closest('#kidsBookmarkResumePill, [class*="bookmark"]'))
            );
            const isSave = (s, btn) => !isDismiss(s) && !isResume(s, btn) && /segnalibro|segna questa|marque-page|marquer|lesezeichen|bookmark|salva pagina|save bookmark|🔖/i.test(s);
            const all = [];
            const seen = new Set();
            for (const root of roots) {
                for (const btn of root.querySelectorAll('button')) {
                    if (seen.has(btn) || !isVisible(btn)) continue;
                    const meta = [
                        btn.id, btn.className, btn.textContent,
                        btn.getAttribute('aria-label') || '',
                        btn.getAttribute('title') || '',
                        btn.dataset.action || '',
                    ].join(' ');
                    if (action === 'resume' ? isResume(meta, btn) : isSave(meta, btn)) {
                        seen.add(btn);
                        const cs = getComputedStyle(btn);
                        all.push({
                            id: btn.id || '',
                            text: btn.textContent.trim(),
                            title: btn.getAttribute('title') || '',
                            aria: btn.getAttribute('aria-label') || '',
                            ariaPressed: btn.getAttribute('aria-pressed') || '',
                            cls: btn.className,
                            bg: cs.backgroundColor,
                            visible: true,
                        });
                    }
                }
            }
            return all;
        }""",
        action,
    )
    return info


def click_bookmark_button(page, action: str = "save") -> dict[str, Any]:
    """Click the visible bookmark save or resume button via real Playwright .click()."""
    hits = find_bookmark_button(page, action)
    if not hits:
        settings_btn = page.locator("#kidsNotebookFloatingBar .kids-settings-wrap > button").first
        if settings_btn.count() > 0 and settings_btn.is_visible():
            ensure_settings_popover(page, True)
            hits = find_bookmark_button(page, action)
    if not hits:
        raise AssertionError(f"Visible Bookmark ({action}) button not found in floating bar, pill, or settings popover")

    all_btns = page.locator("#kidsNotebookFloatingBar button, #kidsSettingsPopover button, #bookViewport button")
    for idx in range(all_btns.count()):
        btn = all_btns.nth(idx)
        if not btn.is_visible():
            continue
        match = btn.evaluate(
            """(el, action) => {
                """ + _js_is_visible_fn() + """
                if (!isVisible(el)) return null;
                const meta = [
                    el.id, el.className, el.textContent,
                    el.getAttribute('aria-label') || '',
                    el.getAttribute('title') || '',
                    el.dataset.action || '',
                ].join(' ');
                const isDismiss = /dismiss|chiudi|close/i.test(meta);
                const isResume = !isDismiss && /bookmark-resume-jump|riprendi|resume|vai al segnalibro|restore|apri segnalibro|\b(aller|öffnen|vai)\b/i.test(meta) && (
                    /bookmark-resume-jump|bookmark|segnalibro|marque-page|lesezeichen|reprendre|riprendi|resume|restore/i.test(meta) ||
                    Boolean(el.closest('#kidsBookmarkResumePill, [class*="bookmark"]'))
                );
                const isSave = !isDismiss && !isResume && /segnalibro|segna questa|marque-page|marquer|lesezeichen|bookmark|salva pagina|save bookmark|🔖/i.test(meta);
                if (action === 'resume' ? isResume : isSave) {
                    return { text: el.textContent.trim(), cls: el.className, title: el.getAttribute('title') || '' };
                }
                return null;
            }""",
            action,
        )
        if match:
            btn.click()
            page.wait_for_timeout(150)
            return match
    raise AssertionError(f"Visible Bookmark ({action}) button could not be clicked")


def get_bookmarks_storage(page) -> dict[str, Any]:
    return page.evaluate(
        """() => {
            const raw = localStorage.getItem('kos_kids_bookmarks_v1');
            return raw ? JSON.parse(raw) : null;
        }"""
    )


def assert_fit_metrics(metrics: list[dict[str, Any]], label: str) -> None:
    if not metrics:
        raise AssertionError(f"{label}: __kidsTextFitMetrics() returned empty")
    for m in metrics:
        if not m["fits"] or m["overflowY"] > MAX_OVERFLOW_PX or m["overflowX"] > MAX_OVERFLOW_PX:
            raise AssertionError(
                f"{label} P{m['page']} [{m['level']}/{m['lang']}] overflow: "
                f"overflowY={m['overflowY']}px overflowX={m['overflowX']}px "
                f"(scrollH={m['scrollHeight']} clientH={m['clientHeight']})"
            )
        if m["fillRatio"] < MIN_FILL_RATIO:
            raise AssertionError(
                f"{label} P{m['page']} [{m['level']}/{m['lang']}] underfill: "
                f"fillRatio={m['fillRatio']} < {MIN_FILL_RATIO}"
            )


def get_puffin_session_payload(player_id: str) -> dict[str, Any]:
    return {
        "id": f"e2e_{player_id}",
        "player_id": player_id,
        "app_id": "kids-own-stories",
        "logged_at": "2026-11-23T08:00:00.000Z",
        "auth_method": "offline_md5_seed",
        "offline_verified": True,
    }


def authenticate_puffin_profile(page, player_id: str, reload_url: str | None = None) -> None:
    """Authenticate a PuffinLogin profile via window.PuffinLogin or puffin_auth_v2 + reload."""
    has_puffin = page.evaluate("() => Boolean(window.PuffinLogin && document.getElementById('puffin-widget')?.shadowRoot)")
    if not has_puffin:
        raise AssertionError("window.PuffinLogin or #puffin-widget.shadowRoot is not initialized (check <script type='module'>)")
    page.evaluate(
        """({pid, payload}) => {
            localStorage.setItem('puffin_auth_v2', JSON.stringify(payload));
            const w = document.getElementById('puffin-widget');
            if (w && typeof w.saveActiveSession === 'function') {
                w.saveActiveSession(pid, true);
            }
        }""",
        {"pid": player_id, "payload": get_puffin_session_payload(player_id)},
    )
    if reload_url is not None:
        page.goto(reload_url, wait_until="networkidle")
        page.wait_for_selector(".kids-sentence-box", timeout=10000)
        page.wait_for_timeout(120)
    else:
        page.wait_for_timeout(140)


def active_book_targets(env: RunnerEnv) -> list[tuple[str, str]]:
    """Return [(alias, canonical_story_id)] selected by --book and baseline availability."""
    targets: list[tuple[str, str]] = []
    if env.args.book in ("sardegna", "all"):
        targets.append(("sardegna", SARDEGNA_ID))
    if env.args.book in ("petit-prince", "all"):
        if env.has_petit_prince_assets() or not env.baseline:
            targets.append(("petit-prince", PETIT_PRINCE_ID))
    return targets


def open_book_query(env: RunnerEnv, alias: str, extra: str = "") -> str:
    """Use ?book=<alias> normally, or legacy ?story=sardegna in --baseline mode for engine checks."""
    if alias == "sardegna" and env.baseline:
        base = "?story=sardegna&mode=seby"
        if "mode=" in extra:
            base = "?story=sardegna"
        return f"{base}{extra}"
    return f"?book={alias}{extra}"


def load_book_json(story_id: str) -> dict[str, Any]:
    if story_id == SARDEGNA_ID:
        p = REPO_ROOT / "stories" / "alessandro" / SARDEGNA_ID / "kids_book_data.json"
    elif story_id == PETIT_PRINCE_ID:
        p = REPO_ROOT / "books" / "petit-prince" / "kids_book_data.json"
    else:
        raise ValueError(story_id)
    if not p.exists():
        raise AssertionError(f"Missing book JSON: {p.relative_to(REPO_ROOT)}")
    return json.loads(p.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Opaque-Box Bookshelf (/books/) Helpers
# ---------------------------------------------------------------------------
def goto_bookshelf(
    page,
    env: RunnerEnv,
    path_query: str = "/books/",
    wait_until: str = "networkidle",
    wait_fonts: bool = True,
):
    url = f"{env.base_origin}{path_query}"
    resp = page.goto(url, wait_until=wait_until)
    if wait_fonts:
        page.evaluate("() => document.fonts ? document.fonts.ready : Promise.resolve()")
        page.wait_for_timeout(140)
    return resp


def inspect_bookshelf_cards(page) -> dict[str, dict[str, Any]]:
    """Opaque-box inspection of visible book cards on /books/ (Sardegna & Le Petit Prince)."""
    return page.evaluate(
        """() => {
            """ + _js_is_visible_fn() + """
            const isSarText = (s) => /vacanze in sardegna|sardegna|cala gonone|arbatax/i.test(String(s || ''));
            const isPpText = (s) => /petit[\\s_-]*prince|piccolo principe|kleiner prinz/i.test(String(s || ''));
            const matchBook = (s) => {
                const sar = isSarText(s);
                const pp = isPpText(s);
                if (sar && !pp) return 'sardegna';
                if (pp && !sar) return 'petit-prince';
                return null;
            };
            const elemMeta = (el) => [
                el.dataset?.book || '',
                el.getAttribute('href') || '',
                el.getAttribute('aria-label') || '',
                el.getAttribute('title') || '',
                el.id || '',
                el.className || '',
                el.innerText || '',
            ].join(' ');

            const candidates = Array.from(document.querySelectorAll('a, article, section, div, li'))
                .filter(el => isVisible(el))
                .map(el => {
                    const meta = elemMeta(el);
                    const linksStr = Array.from(el.querySelectorAll('a[href]')).map(a => a.getAttribute('href') || '').join(' ');
                    const combined = meta + ' ' + linksStr;
                    const sar = isSarText(combined);
                    const pp = isPpText(combined);
                    if (sar && pp) return null;
                    const book = sar ? 'sardegna' : (pp ? 'petit-prince' : null);
                    if (!book) return null;
                    const imgs = Array.from(el.querySelectorAll('img')).filter(isVisible);
                    if (imgs.length < 1) return null;
                    const imgMetrics = imgs
                        .map(im => {
                            const ir = im.getBoundingClientRect();
                            return { im, w: ir.width, h: ir.height, area: ir.width * ir.height };
                        })
                        .filter(x => x.area > 0);
                    if (!imgMetrics.length) return null;
                    const coverSized = imgMetrics.filter(x => x.w >= 100 && x.h >= 100);
                    if (!coverSized.length) return null;
                    coverSized.sort((a, b) => b.area - a.area);
                    const r = el.getBoundingClientRect();
                    return { el, book, img: coverSized[0].im, area: r.width * r.height, rect: r };
                })
                .filter(Boolean);

            const pickCard = (book) => {
                const hits = candidates.filter(c => c.book === book).sort((a, b) => b.area - a.area);
                if (!hits.length) return null;
                const { el, img, rect } = hits[0];
                const imgRect = img.getBoundingClientRect();

                const hasMatchingDescendant = (node) => Array.from(node.querySelectorAll('*'))
                    .some(ch => isVisible(ch) && matchBook(ch.innerText) === book);
                const innermostMatch = (root) => {
                    let cur = root;
                    while (cur) {
                        const children = Array.from(cur.children || [])
                            .filter(ch => isVisible(ch) && matchBook(ch.innerText) === book);
                        if (!children.length) break;
                        children.sort((a, b) => a.getBoundingClientRect().top - b.getBoundingClientRect().top);
                        cur = children[0];
                    }
                    return cur;
                };
                const primaryTitles = Array.from(el.querySelectorAll('h1, h2, h3, h4, [class*="title"], [class*="heading"], strong'))
                    .filter(t => isVisible(t) && matchBook(t.innerText) === book)
                    .map(innermostMatch)
                    .filter((t, idx, arr) => t && arr.indexOf(t) === idx && !hasMatchingDescendant(t))
                    .sort((a, b) => a.getBoundingClientRect().top - b.getBoundingClientRect().top);
                let titleEl = primaryTitles[0] || null;
                if (!titleEl) {
                    const headerEls = Array.from(el.querySelectorAll('header'))
                        .filter(t => isVisible(t) && matchBook(t.innerText) === book)
                        .map(innermostMatch)
                        .filter((t, idx, arr) => t && arr.indexOf(t) === idx && !hasMatchingDescendant(t))
                        .sort((a, b) => a.getBoundingClientRect().top - b.getBoundingClientRect().top);
                    titleEl = headerEls[0] || null;
                }
                if (!titleEl) {
                    const fallbackEls = Array.from(el.querySelectorAll('span, div, p'))
                        .filter(t => isVisible(t) && !t.querySelector('img') && matchBook(t.innerText) === book)
                        .map(innermostMatch)
                        .filter((t, idx, arr) => t && arr.indexOf(t) === idx && !hasMatchingDescendant(t))
                        .sort((a, b) => a.getBoundingClientRect().top - b.getBoundingClientRect().top);
                    titleEl = fallbackEls[0] || null;
                }
                const titleRect = titleEl ? titleEl.getBoundingClientRect() : null;
                const titleFontFamily = titleEl ? (getComputedStyle(titleEl).fontFamily || '') : '';
                const headerEl = el.querySelector('header, [class*="header"]');
                const headerText = headerEl && isVisible(headerEl) ? (headerEl.innerText || '').trim() : '';
                const authorEl = el.querySelector('[class*="author"], [class*="credit"], header p');
                const authorText = authorEl && isVisible(authorEl) ? (authorEl.innerText || '').trim() : '';

                const links = [];
                if (el.tagName === 'A' && el.getAttribute('href')) {
                    links.push({
                        href: el.getAttribute('href'),
                        absHref: el.href,
                        text: (el.innerText || '').trim(),
                        cls: el.className || '',
                    });
                }
                for (const a of el.querySelectorAll('a[href]')) {
                    if (!isVisible(a)) continue;
                    links.push({
                        href: a.getAttribute('href'),
                        absHref: a.href,
                        text: (a.innerText || '').trim(),
                        cls: a.className || '',
                    });
                }

                const resumeRe = /riprendi|resume|segnalibro|bookmark|marque-page|lesezeichen|page=\\d+/i;
                const resumeHits = Array.from(el.querySelectorAll('a, button, span, div, p, [class*="bookmark"], [class*="resume"]'))
                    .filter(x => isVisible(x) && x !== el && !x.querySelector('img'))
                    .filter(x => {
                        const m = [
                            x.className || '',
                            x.id || '',
                            x.getAttribute('aria-label') || '',
                            x.getAttribute('title') || '',
                            x.getAttribute('href') || '',
                            x.innerText || '',
                        ].join(' ');
                        return resumeRe.test(m);
                    })
                    .filter(x => {
                        const parentMatch = x.parentElement && x.parentElement !== el && !x.parentElement.querySelector('img') && resumeRe.test(x.parentElement.innerText || '');
                        return !parentMatch || x.tagName === 'A' || x.tagName === 'BUTTON';
                    })
                    .map(x => ({
                        tag: x.tagName.toLowerCase(),
                        text: (x.innerText || '').trim(),
                        href: x.getAttribute('href') || '',
                        cls: x.className || '',
                    }));

                return {
                    found: true,
                    cardRect: { left: rect.left, top: rect.top, right: rect.right, bottom: rect.bottom, width: rect.width, height: rect.height },
                    titleText: titleEl ? (titleEl.innerText || '').trim() : '',
                    titleFontFamily,
                    headerText,
                    authorText,
                    titleRect: titleRect ? { left: titleRect.left, top: titleRect.top, right: titleRect.right, bottom: titleRect.bottom, width: titleRect.width, height: titleRect.height } : null,
                    imgRect: { left: imgRect.left, top: imgRect.top, right: imgRect.right, bottom: imgRect.bottom, width: imgRect.width, height: imgRect.height },
                    img: {
                        src: img.currentSrc || img.getAttribute('src') || '',
                        complete: Boolean(img.complete),
                        naturalWidth: img.naturalWidth || 0,
                        naturalHeight: img.naturalHeight || 0,
                    },
                    links,
                    resumeHits,
                };
            };

            const out = {};
            for (const b of ['sardegna', 'petit-prince']) {
                const c = pickCard(b);
                if (c) out[b] = c;
            }
            return out;
        }"""
    )


def click_bookshelf_target(page, book_alias: str, prefer_resume: bool = False) -> None:
    """Click a book card (or its bookmark resume link/button) on /books/ via real Playwright .click()."""
    token = f"kos-shelf-{book_alias}-{'resume' if prefer_resume else 'open'}"
    found = page.evaluate(
        """({bookAlias, preferResume, token}) => {
            """ + _js_is_visible_fn() + """
            document.querySelectorAll('[data-e2e-click-target]').forEach(e => e.removeAttribute('data-e2e-click-target'));
            const isSarText = (s) => /vacanze in sardegna|sardegna|cala gonone|arbatax/i.test(String(s || ''));
            const isPpText = (s) => /petit[\\s_-]*prince|piccolo principe|kleiner prinz/i.test(String(s || ''));
            const matchBook = (s) => {
                const sar = isSarText(s);
                const pp = isPpText(s);
                if (sar && !pp) return 'sardegna';
                if (pp && !sar) return 'petit-prince';
                return null;
            };
            const all = Array.from(document.querySelectorAll('a, button, article, section, div'));
            const cardHits = all
                .map((el) => {
                    if (!isVisible(el)) return null;
                    const linksStr = Array.from(el.querySelectorAll('a[href]')).map(a => a.getAttribute('href') || '').join(' ');
                    const combined = [
                        el.dataset?.book || '', el.getAttribute('href') || '',
                        el.getAttribute('aria-label') || '', el.id || '', el.className || '',
                        el.innerText || '', linksStr,
                    ].join(' ');
                    if (matchBook(combined) !== bookAlias) return null;
                    const imgs = Array.from(el.querySelectorAll('img')).filter(isVisible);
                    if (imgs.length < 1) return null;
                    const hasCoverImg = imgs.some(im => {
                        const ir = im.getBoundingClientRect();
                        return ir.width >= 100 && ir.height >= 100;
                    });
                    if (!hasCoverImg) return null;
                    const r = el.getBoundingClientRect();
                    return { el, area: r.width * r.height };
                })
                .filter(Boolean)
                .sort((a, b) => b.area - a.area);
            if (!cardHits.length) return false;
            const card = cardHits[0].el;

            let target = null;
            if (preferResume) {
                const resumeRe = /riprendi|resume|segnalibro|bookmark|marque-page|lesezeichen|page=\\d+/i;
                const clickables = Array.from(card.querySelectorAll('a[href], button')).filter(isVisible);
                for (const c of clickables) {
                    const meta = [c.className || '', c.id || '', c.getAttribute('href') || '', c.getAttribute('aria-label') || '', c.getAttribute('title') || '', c.innerText || ''].join(' ');
                    if (resumeRe.test(meta)) {
                        target = c;
                        break;
                    }
                }
            }
            if (!target && card.tagName === 'A' && card.getAttribute('href')) {
                target = card;
            }
            if (!target) {
                const bookLinks = Array.from(card.querySelectorAll('a[href]')).filter(isVisible);
                target = bookLinks.find(a => /book=/.test(a.getAttribute('href') || '') && !/page=/.test(a.getAttribute('href') || ''))
                    || bookLinks.find(a => /book=/.test(a.getAttribute('href') || ''))
                    || bookLinks[0]
                    || card;
            }
            if (!target) return false;
            target.setAttribute('data-e2e-click-target', token);
            return true;
        }""",
        {"bookAlias": book_alias, "preferResume": prefer_resume, "token": token},
    )
    if not found:
        raise AssertionError(f"Could not locate clickable {'resume ' if prefer_resume else ''}target for '{book_alias}' on /books/")
    target_loc = page.locator(f'[data-e2e-click-target="{token}"]').first
    target_loc.click()
    try:
        page.evaluate(
            "(tok) => document.querySelectorAll('[data-e2e-click-target=\"' + tok + '\"]').forEach(e => e.removeAttribute('data-e2e-click-target'))",
            token,
        )
    except Exception:
        pass


def find_and_click_books_link(page) -> str:
    """Locate a visible light-DOM link/button to /books on index.html and click it via Playwright."""
    token = "kos-books-link-target"

    def _stamp_books_link() -> str | None:
        return page.evaluate(
            """(tok) => {
                """ + _js_is_visible_fn() + """
                document.querySelectorAll('[data-e2e-click-target]').forEach(e => e.removeAttribute('data-e2e-click-target'));
                const all = Array.from(document.querySelectorAll('a, button'));
                const booksRe = /(?:^|\\/|\\.\\/)books(?:\\/|\\?|$)/i;
                const labelRe = /libreria|bookshelf|tutti i libri|tous les livres|alle bücher|\\/books\\b/i;
                for (const el of all) {
                    if (!isVisible(el)) continue;
                    const href = el.getAttribute('href') || '';
                    const onclick = el.getAttribute('onclick') || '';
                    const dHref = el.dataset?.href || el.dataset?.url || '';
                    const meta = [el.id || '', el.className || '', el.getAttribute('aria-label') || '', el.getAttribute('title') || '', el.innerText || ''].join(' ');
                    if (booksRe.test(href) || /books\\/?['"`]/i.test(onclick) || booksRe.test(dHref) || labelRe.test(meta)) {
                        el.setAttribute('data-e2e-click-target', tok);
                        return href || el.getAttribute('title') || (el.innerText || '').trim();
                    }
                }
                return null;
            }""",
            token,
        )

    matched_label = _stamp_books_link()
    if matched_label is None:
        settings_btn = page.locator("#kidsNotebookFloatingBar .kids-settings-wrap > button").first
        if settings_btn.count() > 0 and settings_btn.is_visible():
            ensure_settings_popover(page, True)
            matched_label = _stamp_books_link()
    if matched_label is None:
        raise AssertionError("Expected visible link/button to /books in index.html")
    el = page.locator(f'[data-e2e-click-target="{token}"]').first
    el.click()
    try:
        page.evaluate(
            "(tok) => document.querySelectorAll('[data-e2e-click-target=\"' + tok + '\"]').forEach(e => e.removeAttribute('data-e2e-click-target'))",
            token,
        )
    except Exception:
        pass
    return matched_label


def inspect_reader_book_header(page, book_alias: str) -> dict[str, Any]:
    """Opaque-box check that the active book title/credit is visibly rendered in fullscreen reader mode."""
    return page.evaluate(
        """(alias) => {
            """ + _js_is_visible_fn() + """
            const titleRe = alias === 'petit-prince'
                ? /le petit prince|piccolo principe|kleiner prinz/i
                : /vacanze in sardegna|sardegna|cala gonone/i;
            const strictTitleRe = alias === 'petit-prince'
                ? /le petit prince/i
                : /vacanze in sardegna/i;
            const authorRe = alias === 'petit-prince'
                ? /saint-exup[eé]ry/i
                : /riccardo carlesso/i;
            const serifRe = /cormorant|garamond|playfair|crimson|georgia|times|(?:^|[\\s,'"])(?:ui-)?serif(?=$|[\\s,'"])/i;
            const spreadEl = document.getElementById('openBookSpread');
            const isLeafTitleEl = (el) => !Array.from(el.querySelectorAll('*'))
                .some(ch => isVisible(ch) && titleRe.test((ch.innerText || '').trim()));
            const candidates = Array.from(document.querySelectorAll(
                'header, h1, h2, h3, h4, p, strong, [class*="title"], [class*="header"], [class*="banner"], [class*="ribbon"], [id*="title" i], [id*="header" i], [id*="banner" i], span, div'
            ))
                .filter(el => isVisible(el))
                .filter(el => !spreadEl || (!el.contains(spreadEl) && !spreadEl.contains(el)))
                .filter(el => !el.closest('#kidsSettingsPopover, #openBookSpread, #indexView, #netflixView, #puffin-widget, #antolinQuizDialog, #antolinDashDialog'))
                .filter(el => !el.querySelector('select, button.kids-pill-control'))
                .filter(isLeafTitleEl)
                .map(el => {
                    const txt = (el.innerText || '').trim();
                    if (!txt || txt.length > 220 || !titleRe.test(txt)) return null;
                    const cs = getComputedStyle(el);
                    const r = el.getBoundingClientRect();
                    const parentTxt = (el.parentElement?.innerText || '').trim();
                    const combinedTxt = parentTxt.length <= 240 ? (txt + ' ' + parentTxt) : txt;
                    return {
                        tag: el.tagName.toLowerCase(),
                        id: el.id || '',
                        cls: el.className || '',
                        text: txt,
                        fontFamily: cs.fontFamily || '',
                        hasTitle: titleRe.test(txt),
                        hasStrictTitle: strictTitleRe.test(combinedTxt),
                        hasAuthor: authorRe.test(combinedTxt),
                        hasSerif: serifRe.test(cs.fontFamily || ''),
                        rect: { top: r.top, left: r.left, width: r.width, height: r.height },
                    };
                })
                .filter(Boolean);
            return { found: candidates.length > 0, matches: candidates };
        }""",
        book_alias,
    )


# ---------------------------------------------------------------------------
# Test Registry Infrastructure
# ---------------------------------------------------------------------------
@dataclass
class TestSpec:
    test_id: str
    tier: int
    feature: str
    scope_books: tuple[str, ...]
    requires_m1_m3: bool
    description: str
    fn: Callable[[RunnerEnv], None]
    requires_m5: bool = False


TESTS: list[TestSpec] = []


def register_test(
    test_id: str,
    tier: int,
    feature: str,
    scope_books: tuple[str, ...],
    requires_m1_m3: bool,
    description: str,
    requires_m5: bool = False,
):
    def deco(fn: Callable[[RunnerEnv], None]):
        TESTS.append(
            TestSpec(
                test_id=test_id,
                tier=tier,
                feature=feature,
                scope_books=scope_books,
                requires_m1_m3=requires_m1_m3,
                description=description,
                fn=fn,
                requires_m5=requires_m5,
            )
        )
        return fn

    return deco


# ===========================================================================
# TIER 1: 61 Single-Feature Tests (5 per feature F1-F12 + Escape)
# ===========================================================================

# --- F1: URL Routing & Legacy Compatibility (5) ---
@register_test("T1-F1-1", 1, "F1", ("sardegna",), True, "Load ?book=sardegna enters fullscreen studio with 16 pages (P1-P2)")
def t1_f1_1(env: RunnerEnv) -> None:
    if env.baseline:
        raise SkipTest("pre-M1/M3 baseline: ?book= URL routing not yet implemented")
    ctx, page, rec = env.new_session()
    try:
        env.goto_reader(page, "?book=sardegna")
        check_clean_page(rec)
        assert is_kids_fullscreen(page), "Expected body.kids-fullscreen-book on ?book=sardegna"
        info = get_active_book_info(page)
        assert info["storyId"] == SARDEGNA_ID, f"Expected {SARDEGNA_ID}, got {info['storyId']}"
        assert info["totalPages"] == 16, f"Expected 16 pages, got {info['totalPages']}"
        assert info["pages"] == [1, 2], f"Expected [1, 2], got {info['pages']}"
    finally:
        ctx.close()


@register_test("T1-F1-2", 1, "F1", ("petit-prince",), True, "Load ?book=petit-prince enters fullscreen studio, 26 pages, default fr")
def t1_f1_2(env: RunnerEnv) -> None:
    env.require_m1_m3(env.has_petit_prince_assets(), "books/petit-prince missing")
    ctx, page, rec = env.new_session()
    try:
        env.goto_reader(page, "?book=petit-prince")
        check_clean_page(rec)
        assert is_kids_fullscreen(page), "Expected body.kids-fullscreen-book on ?book=petit-prince"
        info = get_active_book_info(page)
        assert info["storyId"] == PETIT_PRINCE_ID, f"Expected {PETIT_PRINCE_ID}, got {info['storyId']}"
        assert info["totalPages"] == 26, f"Expected 26 pages, got {info['totalPages']}"
        assert info["lang"] == "fr", f"Expected default lang 'fr', got {info['lang']}"
        assert info["pages"] == [1, 2], f"Expected [1, 2], got {info['pages']}"
    finally:
        ctx.close()


@register_test("T1-F1-3", 1, "F1", ("sardegna",), False, "Legacy ?story=sardegna&mode=ale&lang=de resolves cleanly")
def t1_f1_3(env: RunnerEnv) -> None:
    ctx, page, rec = env.new_session()
    try:
        env.goto_reader(page, "?story=sardegna&mode=ale&lang=de")
        check_clean_page(rec, allow_baseline_puffin_error=env.baseline)
        info = get_active_book_info(page)
        assert info["storyId"] == SARDEGNA_ID, f"Expected {SARDEGNA_ID}, got {info['storyId']}"
        assert info["mode"] == "ale", f"Expected mode 'ale', got {info['mode']}"
        assert info["lang"] == "de", f"Expected lang 'de', got {info['lang']}"
        assert info["pages"] == [1, 2], f"Expected [1, 2], got {info['pages']}"
    finally:
        ctx.close()


@register_test("T1-F1-4", 1, "F1", ("sardegna", "petit-prince"), True, "Bare index.html lands in non-fullscreen mode; clicking Indice opens #indexView with 7 cards")
def t1_f1_4(env: RunnerEnv) -> None:
    if env.baseline:
        raise SkipTest("pre-M1/M3 baseline: M1 default landing / ?tab=indice flow not yet implemented")
    ctx, page, rec = env.new_session()
    try:
        env.goto_reader(page, "", wait_selector="#openBookSpread:visible, #indexView:visible")
        check_clean_page(rec)
        assert not is_kids_fullscreen(page), "Bare index.html must not enter kids fullscreen"
        assert not page.locator("#kidsNotebookFloatingBar").is_visible(), "#kidsNotebookFloatingBar must be hidden on bare landing"
        page.locator("#tabsStrip button[data-tab='indice']").click()
        page.locator("#indexView").wait_for(state="visible", timeout=5000)
        assert "tab=indice" in page.url, f"Expected ?tab=indice in URL after clicking Indice tab, got {page.url}"
        cards = page.locator("#indexView .index-card").count()
        assert cards == 7, f"Expected 7 story cards in index, got {cards}"
        check_clean_page(rec)
    finally:
        ctx.close()


@register_test("T1-F1-5", 1, "F1", ("petit-prince",), True, "?tab=studio and ?tab=kids open studio mode and ?book=petit-prince&page=5 opens P5-P6")
def t1_f1_5(env: RunnerEnv) -> None:
    env.require_m1_m3(env.has_petit_prince_assets(), "books/petit-prince missing")
    ctx, page, rec = env.new_session()
    try:
        for tab_q in ("?tab=studio", "?tab=kids"):
            env.goto_reader(page, tab_q)
            check_clean_page(rec)
            assert is_kids_fullscreen(page), f"Expected fullscreen studio on {tab_q}"
        env.goto_reader(page, "?book=petit-prince&page=5")
        check_clean_page(rec)
        info = get_active_book_info(page)
        assert info["storyId"] == PETIT_PRINCE_ID
        assert info["pages"] == [5, 6], f"Expected [5, 6], got {info['pages']}"
    finally:
        ctx.close()


@register_test("T1-F1-6", 1, "F1", ("sardegna", "petit-prince"), True, "Legacy ?story=<adult-slug>, ?story=<layer1-sardegna-slug>, and #<adult-slug> do not inherit savedMode from kos_app_state_v1")
def t1_f1_6(env: RunnerEnv) -> None:
    if env.baseline:
        raise SkipTest("pre-M1/M3 baseline: ?book= routing not yet implemented")
    zaino_slug = "storia-dello-zaino-del-drago-e-dei-puffins"
    ctx, page, rec = env.new_session()
    try:
        # 1. Seed kos_app_state_v1 via Kids Book visit (?book=sardegna&mode=ale&page=2)
        env.goto_reader(page, "?book=sardegna&mode=ale&page=2")
        check_clean_page(rec)
        saved_state = page.evaluate("() => JSON.parse(localStorage.getItem('kos_app_state_v1') || '{}')")
        assert saved_state.get("mode") == "ale", f"Expected kos_app_state_v1.mode == 'ale', got {saved_state}"

        # 2. Navigate to ?story=<adult-slug> without ?book= or ?mode= -> must open Layer-1 adult view
        env.goto_reader(page, f"?story={zaino_slug}", wait_selector="#openBookSpread .book-prose")
        check_clean_page(rec)
        info_zaino = get_active_book_info(page)
        assert info_zaino["mode"] is None, f"Expected kidsBookMode === null on ?story={zaino_slug}, got {info_zaino}"
        assert info_zaino["activeTab"] == zaino_slug, f"Expected activeTab == {zaino_slug}, got {info_zaino}"
        assert not is_kids_fullscreen(page), f"Unexpected kids fullscreen on ?story={zaino_slug}"
        assert "book=sardegna" not in info_zaino["url"] and (f"tab={zaino_slug}" in info_zaino["url"] or f"story={zaino_slug}" in info_zaino["url"]), (
            f"URL hijacked away from {zaino_slug}: {info_zaino['url']}"
        )
        prose_zaino = page.locator("#openBookSpread .book-prose").first
        assert prose_zaino.is_visible() and len(prose_zaino.inner_text().strip()) > 20, "Expected visible Layer-1 prose for zaino"

        # 3. Re-seed saved mode='ale', then verify legacy ?story=<layer1-sardegna-slug> without ?mode= opens Layer-1 adult view
        env.goto_reader(page, "?book=sardegna&mode=ale&page=2")
        env.goto_reader(page, f"?story={SARDEGNA_ID}", wait_selector="#openBookSpread .book-prose")
        check_clean_page(rec)
        info_sar_adult = get_active_book_info(page)
        assert info_sar_adult["mode"] is None, f"Expected kidsBookMode === null on ?story={SARDEGNA_ID}, got {info_sar_adult}"
        assert info_sar_adult["activeTab"] == SARDEGNA_ID, info_sar_adult
        assert not is_kids_fullscreen(page), f"Unexpected kids fullscreen on legacy ?story={SARDEGNA_ID}"
        assert "book=sardegna" not in info_sar_adult["url"] and (f"tab={SARDEGNA_ID}" in info_sar_adult["url"] or f"story={SARDEGNA_ID}" in info_sar_adult["url"]), (
            f"Unexpected URL on legacy ?story={SARDEGNA_ID}: {info_sar_adult['url']}"
        )
        prose_sar = page.locator("#openBookSpread .book-prose").first
        assert prose_sar.is_visible() and len(prose_sar.inner_text().strip()) > 20, "Expected visible Layer-1 prose for sardegna"

        # 4. Re-seed saved mode='ale', then verify #<adult-slug> without ?book= or ?mode= opens Layer-1 adult view
        env.goto_reader(page, "?book=sardegna&mode=ale&page=2")
        env.goto_reader(page, f"#{zaino_slug}", wait_selector="#openBookSpread .book-prose")
        check_clean_page(rec)
        info_hash = get_active_book_info(page)
        assert info_hash["mode"] is None, f"Expected kidsBookMode === null on #{zaino_slug}, got {info_hash}"
        assert info_hash["activeTab"] == zaino_slug, f"Expected activeTab == {zaino_slug}, got {info_hash}"
        assert not is_kids_fullscreen(page), f"Unexpected kids fullscreen on #{zaino_slug}"
        assert "book=sardegna" not in info_hash["url"], f"URL hijacked on #{zaino_slug}: {info_hash['url']}"
        assert page.locator("#openBookSpread .book-prose").first.is_visible(), "Expected visible Layer-1 prose on hash route"
    finally:
        ctx.close()


# --- F2: UI Book Selector (5) ---
@register_test("T1-F2-1", 1, "F2", ("sardegna", "petit-prince"), True, "UI Book Selector is visible and lists Cala Gonone and Le Petit Prince")
def t1_f2_1(env: RunnerEnv) -> None:
    env.require_m1_m3(env.has_petit_prince_assets(), "books/petit-prince missing")
    ctx, page, rec = env.new_session()
    try:
        env.goto_reader(page, "?book=sardegna")
        check_clean_page(rec)
        sel = find_book_selector_state(page)
        if not sel["found"]:
            ensure_settings_popover(page, True)
            sel = find_book_selector_state(page)
        assert sel["found"], f"Expected Book Selector listing both books, got {sel}"
    finally:
        ctx.close()


@register_test("T1-F2-2", 1, "F2", ("sardegna", "petit-prince"), True, "Switching sar->pp via Book Selector loads wc_p01/02 from books/petit-prince")
def t1_f2_2(env: RunnerEnv) -> None:
    env.require_m1_m3(env.has_petit_prince_assets(), "books/petit-prince missing")
    ctx, page, rec = env.new_session()
    try:
        env.goto_reader(page, "?book=sardegna")
        select_book_in_ui(page, "petit-prince")
        check_clean_page(rec)
        info = get_active_book_info(page)
        assert info["storyId"] == PETIT_PRINCE_ID, f"Expected {PETIT_PRINCE_ID}, got {info['storyId']}"
        assert info["totalPages"] == 26
        assert any("books/petit-prince/wc_p01.jpg" in img for img in info["images"]), info["images"]
        assert any("books/petit-prince/wc_p02.jpg" in img for img in info["images"]), info["images"]
    finally:
        ctx.close()


@register_test("T1-F2-3", 1, "F2", ("sardegna", "petit-prince"), True, "Switching back pp->sar restores Cala Gonone wc_p01.jpg & 16 pages")
def t1_f2_3(env: RunnerEnv) -> None:
    env.require_m1_m3(env.has_petit_prince_assets(), "books/petit-prince missing")
    ctx, page, rec = env.new_session()
    try:
        env.goto_reader(page, "?book=petit-prince")
        select_book_in_ui(page, "sardegna")
        check_clean_page(rec)
        info = get_active_book_info(page)
        assert info["storyId"] == SARDEGNA_ID
        assert info["totalPages"] == 16
        assert any("storia-sardegna-cala-gonone-arbatax-famiglia/wc_p01.jpg" in img for img in info["images"]), info["images"]
    finally:
        ctx.close()


@register_test("T1-F2-4", 1, "F2", ("sardegna", "petit-prince"), True, "Switching book updates URL and __kidsTextFitMetrics() reflects new book")
def t1_f2_4(env: RunnerEnv) -> None:
    env.require_m1_m3(env.has_petit_prince_assets(), "books/petit-prince missing")
    ctx, page, rec = env.new_session()
    try:
        env.goto_reader(page, "?book=sardegna")
        before_text = page.locator("#bookPageRight .kids-sentence-box").inner_text()
        select_book_in_ui(page, "petit-prince")
        check_clean_page(rec)
        info = get_active_book_info(page)
        assert ("petit-prince" in info["url"] or PETIT_PRINCE_ID in info["url"]), f"URL not updated: {info['url']}"
        after_text = page.locator("#bookPageRight .kids-sentence-box").inner_text()
        assert after_text != before_text, "Sentence box text did not update on book switch"
        metrics = page.evaluate("() => window.__kidsTextFitMetrics()")
        assert_fit_metrics(metrics, "T1-F2-4")
    finally:
        ctx.close()


@register_test("T1-F2-5", 1, "F2", ("sardegna", "petit-prince"), True, "Switching book preserves valid learning language (fr/it/de, never en)")
def t1_f2_5(env: RunnerEnv) -> None:
    env.require_m1_m3(env.has_petit_prince_assets(), "books/petit-prince missing")
    ctx, page, rec = env.new_session()
    try:
        env.goto_reader(page, "?book=sardegna&lang=de")
        select_book_in_ui(page, "petit-prince")
        check_clean_page(rec)
        info = get_active_book_info(page)
        assert info["lang"] in ("fr", "it", "de"), f"Invalid learning lang after switch: {info['lang']}"
        assert info["lang"] != "en"
    finally:
        ctx.close()


# --- F3: Bookmark (segnalibro) (5) ---
@register_test("T1-F3-1", 1, "F3", ("sardegna", "petit-prince"), True, "Bookmark control (segnalibro) is visible in fullscreen book mode")
def t1_f3_1(env: RunnerEnv) -> None:
    if env.baseline:
        raise SkipTest("pre-M1/M3 baseline: Bookmark UI not yet implemented")
    ctx, page, rec = env.new_session()
    try:
        env.goto_reader(page, "?book=sardegna")
        check_clean_page(rec)
        btns = find_bookmark_button(page, "save")
        if not btns:
            ensure_settings_popover(page, True)
            btns = find_bookmark_button(page, "save")
        assert btns, "Expected visible Bookmark (segnalibro) button in studio UI"
    finally:
        ctx.close()


@register_test("T1-F3-2", 1, "F3", ("petit-prince",), True, "Bookmark saves kos_kids_bookmarks_v1 with page, mode, lang, trLang, parallel, savedAt")
def t1_f3_2(env: RunnerEnv) -> None:
    env.require_m1_m3(env.has_petit_prince_assets(), "books/petit-prince missing")
    ctx, page, rec = env.new_session()
    try:
        env.goto_reader(page, "?book=petit-prince&page=7&mode=ale&lang=de")
        click_bookmark_button(page, "save")
        check_clean_page(rec)
        bm = get_bookmarks_storage(page)
        assert isinstance(bm, dict) and PETIT_PRINCE_ID in bm, f"Expected {PETIT_PRINCE_ID} in {bm}"
        entry = bm[PETIT_PRINCE_ID]
        for k in ("page", "mode", "lang", "trLang", "parallel", "savedAt"):
            assert k in entry, f"Bookmark entry missing key '{k}': {entry}"
        assert int(entry["page"]) in (7, 8) and entry["mode"] == "ale" and entry["lang"] == "de", entry
    finally:
        ctx.close()


@register_test("T1-F3-3", 1, "F3", ("petit-prince",), True, "Navigating to P1 and resuming bookmark restores P7-P8 + saved mode/lang")
def t1_f3_3(env: RunnerEnv) -> None:
    env.require_m1_m3(env.has_petit_prince_assets(), "books/petit-prince missing")
    ctx, page, rec = env.new_session()
    try:
        env.goto_reader(page, "?book=petit-prince&page=7&mode=ale&lang=de")
        click_bookmark_button(page, "save")
        env.goto_reader(page, "?book=petit-prince&page=1&mode=seby&lang=fr")
        click_bookmark_button(page, "resume")
        check_clean_page(rec)
        info = get_active_book_info(page)
        assert info["pages"] == [7, 8], f"Expected restored [7, 8], got {info['pages']}"
        assert info["mode"] == "ale" and info["lang"] == "de", info
    finally:
        ctx.close()


@register_test("T1-F3-4", 1, "F3", ("sardegna", "petit-prince"), True, "Per-book bookmark isolation (sardegna vs petit-prince)")
def t1_f3_4(env: RunnerEnv) -> None:
    env.require_m1_m3(env.has_petit_prince_assets(), "books/petit-prince missing")
    ctx, page, rec = env.new_session()
    try:
        env.goto_reader(page, "?book=petit-prince&page=7&mode=ale&lang=de")
        click_bookmark_button(page, "save")
        env.goto_reader(page, "?book=sardegna&page=5&mode=seby&lang=it")
        click_bookmark_button(page, "save")
        check_clean_page(rec)
        bm = get_bookmarks_storage(page)
        assert PETIT_PRINCE_ID in bm and SARDEGNA_ID in bm, bm
        assert int(bm[PETIT_PRINCE_ID]["page"]) in (7, 8) and bm[PETIT_PRINCE_ID]["lang"] == "de", bm
        assert int(bm[SARDEGNA_ID]["page"]) in (5, 6) and bm[SARDEGNA_ID]["lang"] == "it", bm
    finally:
        ctx.close()


@register_test("T1-F3-5", 1, "F3", ("sardegna",), True, "Bookmark UI displays visual saved state/badge after saving")
def t1_f3_5(env: RunnerEnv) -> None:
    if env.baseline:
        raise SkipTest("pre-M1/M3 baseline: Bookmark UI not yet implemented")
    ctx, page, rec = env.new_session()
    try:
        env.goto_reader(page, "?book=sardegna&page=5")
        before_btns = find_bookmark_button(page, "save")
        assert before_btns, "Expected visible save bookmark button before saving"
        before_btn = before_btns[0]
        click_bookmark_button(page, "save")
        check_clean_page(rec)
        after_btns = find_bookmark_button(page, "save")
        assert after_btns, "Bookmark button disappeared after saving"
        after_btn = after_btns[0]
        has_dom_active = (
            after_btn.get("ariaPressed") == "true"
            or "active" in after_btn.get("cls", "").split()
        )
        visual_changed = (
            after_btn.get("title") != before_btn.get("title")
            or after_btn.get("bg") != before_btn.get("bg")
            or any(tok in f"{after_btn['text']} {after_btn['title']} {after_btn['aria']}" for tok in ("5", "6", "✅", "Salvato", "Saved", "Rimuovi", "Retirer", "entfernen"))
        )
        assert has_dom_active and visual_changed, (
            f"Expected visible saved DOM state change, before={before_btn} after={after_btn}"
        )
        bm = get_bookmarks_storage(page)
        assert isinstance(bm, dict) and int(bm.get(SARDEGNA_ID, {}).get("page", 0)) in (5, 6), bm
        # Reload on a different spread (P7-P8) and verify #kidsBookmarkResumePill becomes visible with saved page
        env.goto_reader(page, "?book=sardegna&page=7")
        pill = page.locator("#kidsBookmarkResumePill")
        assert pill.is_visible(), "Expected #kidsBookmarkResumePill visible after reloading onto another spread"
        pill_txt = pill.inner_text()
        assert "5" in pill_txt or "6" in pill_txt, f"Expected bookmarked page in pill text, got {pill_txt}"
        check_clean_page(rec)
    finally:
        ctx.close()


@register_test("T1-F3-6", 1, "F3", ("sardegna", "petit-prince"), False, "Escape key on P5 saves kos_kids_bookmarks_v1, navigates to /books/ (preserving ?kid=), and remembers P5 on reopen", requires_m5=True)
def t1_f3_6(env: RunnerEnv) -> None:
    import urllib.parse

    env.require_m5(env.has_bookshelf(), "books/index.html and Escape bookmark-save/exit (M5) missing")
    for alias, sid in active_book_targets(env):
        ctx, page, rec = env.new_session()
        try:
            env.goto_reader(page, f"?book={alias}&page=1&mode=ale&lang=it&kid=alessandro")
            for _ in range(2):
                page.locator("#bookPageRight .kids-edge-nav-arrow.is-right-arrow").click()
                page.wait_for_timeout(120)
            assert get_active_book_info(page)["pages"] == [5, 6]
            assert is_kids_fullscreen(page), "Expected fullscreen before pressing Escape"

            page.keyboard.press("Escape")
            page.wait_for_url(re.compile(r"/books/?(\?.*)?$"), timeout=5000)
            page.wait_for_load_state("networkidle")
            assert page.url.split("?", 1)[0].endswith("/books/"), f"Expected Escape to navigate to /books/, got {page.url}"
            qs_after = urllib.parse.parse_qs(urllib.parse.urlparse(page.url).query)
            assert qs_after.get("kid") == ["alessandro"], f"Expected Escape -> /books/ to preserve kid=alessandro, got {page.url}"

            bm = get_bookmarks_storage(page)
            assert isinstance(bm, dict) and sid in bm, f"Expected {sid} saved in kos_kids_bookmarks_v1 on Escape, got {bm}"
            assert int(bm[sid]["page"]) in (5, 6), f"Expected saved page 5 or 6, got {bm[sid]}"

            # Verify /books/ displays the saved bookmark indicator right after Escape redirect
            cards = inspect_bookshelf_cards(page)
            assert alias in cards and cards[alias]["resumeHits"], f"{alias}: expected bookmark resume badge on /books/: {cards.get(alias)}"
            assert any("5" in h["text"] or "6" in h["text"] or "page=5" in h["href"] or "page=6" in h["href"] for h in cards[alias]["resumeHits"]), cards[alias]["resumeHits"]

            # Reopen without explicit ?page= -> must remember/resume [5, 6]
            env.goto_reader(page, f"?book={alias}")
            info = get_active_book_info(page)
            if info["pages"] != [5, 6]:
                click_bookmark_button(page, "resume")
                info = get_active_book_info(page)
            assert info["pages"] == [5, 6], f"{alias}: expected remembered/resumed [5, 6], got {info['pages']}"
            check_clean_page(rec)
        finally:
            ctx.close()


# --- F4: CEFR Tiers (seby, ale, emma) (5) ---
@register_test("T1-F4-1", 1, "F4", ("sardegna", "petit-prince"), False, "All 3 tier buttons (seby/ale/emma) exist with loaded avatar images")
def t1_f4_1(env: RunnerEnv) -> None:
    targets = active_book_targets(env)
    ctx, page, rec = env.new_session()
    try:
        for alias, _ in targets:
            env.goto_reader(page, open_book_query(env, alias))
            check_clean_page(rec, allow_baseline_puffin_error=env.baseline)
            imgs = page.evaluate(
                """() => ['.tier-easy', '.tier-medium', '.tier-hard'].map(sel => {
                    const btn = document.querySelector('#kidsNotebookFloatingBar ' + sel);
                    const img = btn?.querySelector('img');
                    return { sel, exists: Boolean(btn), complete: Boolean(img?.complete), w: img?.naturalWidth || 0 };
                })"""
            )
            for item in imgs:
                assert item["exists"] and item["complete"] and item["w"] > 0, f"{alias}: {item}"
    finally:
        ctx.close()


@register_test("T1-F4-2", 1, "F4", ("sardegna", "petit-prince"), False, "Seby (A2) tier activates .level-seby and satisfies word count budget")
def t1_f4_2(env: RunnerEnv) -> None:
    targets = active_book_targets(env)
    ctx, page, rec = env.new_session()
    try:
        for alias, sid in targets:
            env.goto_reader(page, open_book_query(env, alias, "&mode=ale"))
            set_tier(page, "seby")
            check_clean_page(rec, allow_baseline_puffin_error=env.baseline)
            expected_boxes = 1 if sid == PETIT_PRINCE_ID else 2
            assert page.locator("#openBookSpread .kids-sentence-box.level-seby").count() == expected_boxes
            kb = load_book_json(sid)
            lo, hi = (14, 25) if sid == PETIT_PRINCE_ID else (13, 26)
            for pg in kb["pages"]:
                if pg.get("is_frontispiece"):
                    continue
                for lang in ("fr", "it", "de"):
                    wc = len(pg["levels"]["seby"][lang]["text"].split())
                    assert lo <= wc <= hi, f"{alias} P{pg['page']} seby/{lang}: {wc}w outside [{lo}, {hi}]"
    finally:
        ctx.close()


@register_test("T1-F4-3", 1, "F4", ("sardegna", "petit-prince"), False, "Ale (B1) tier activates .level-ale and satisfies word count budget")
def t1_f4_3(env: RunnerEnv) -> None:
    targets = active_book_targets(env)
    ctx, page, rec = env.new_session()
    try:
        for alias, sid in targets:
            env.goto_reader(page, open_book_query(env, alias, "&mode=seby"))
            set_tier(page, "ale")
            check_clean_page(rec, allow_baseline_puffin_error=env.baseline)
            expected_boxes = 1 if sid == PETIT_PRINCE_ID else 2
            assert page.locator("#openBookSpread .kids-sentence-box.level-ale").count() == expected_boxes
            kb = load_book_json(sid)
            lo, hi = (26, 42) if sid == PETIT_PRINCE_ID else (22, 46)
            for pg in kb["pages"]:
                if pg.get("is_frontispiece"):
                    continue
                for lang in ("fr", "it", "de"):
                    wc = len(pg["levels"]["ale"][lang]["text"].split())
                    assert lo <= wc <= hi, f"{alias} P{pg['page']} ale/{lang}: {wc}w outside [{lo}, {hi}]"
    finally:
        ctx.close()


@register_test("T1-F4-4", 1, "F4", ("sardegna", "petit-prince"), False, "Emma (B2/C1) tier activates .level-emma and satisfies word count budget")
def t1_f4_4(env: RunnerEnv) -> None:
    targets = active_book_targets(env)
    ctx, page, rec = env.new_session()
    try:
        for alias, sid in targets:
            env.goto_reader(page, open_book_query(env, alias, "&mode=seby"))
            set_tier(page, "emma")
            check_clean_page(rec, allow_baseline_puffin_error=env.baseline)
            expected_boxes = 1 if sid == PETIT_PRINCE_ID else 2
            assert page.locator("#openBookSpread .kids-sentence-box.level-emma").count() == expected_boxes
            if sid == PETIT_PRINCE_ID:
                kb = load_book_json(sid)
                for pg in kb["pages"]:
                    if pg.get("is_frontispiece"):
                        continue
                    is_even = (pg["page"] % 2 == 0)
                    for lang in ("fr", "it", "de"):
                        wc = len(pg["levels"]["emma"][lang]["text"].split())
                        hi = 55 if is_even else 64
                        assert 40 <= wc <= hi, f"petit-prince P{pg['page']} emma/{lang}: {wc}w outside [40, {hi}]"
            else:
                # Verify rendered text is substantial B2/C1 prose on sardegna
                txt = page.locator("#bookPageLeft .kids-sentence-box").inner_text()
                assert len(txt.split()) >= 25, f"Expected literary Emma prose on sardegna, got {len(txt.split())}w"
    finally:
        ctx.close()


@register_test("T1-F4-5", 1, "F4", ("sardegna", "petit-prince"), False, "All 3 tiers x 3 learning langs fit <=2px overflow and >=0.42 fillRatio across spreads")
def t1_f4_5(env: RunnerEnv) -> None:
    targets = active_book_targets(env)
    ctx, page, rec = env.new_session()
    try:
        for alias, sid in targets:
            total_pages = 26 if sid == PETIT_PRINCE_ID else 16
            spreads = total_pages // 2
            for tier in ("seby", "ale", "emma"):
                for lang in ("fr", "it", "de"):
                    env.goto_reader(page, open_book_query(env, alias, f"&mode={tier}&lang={lang}&page=1"))
                    for s_idx in range(spreads):
                        if s_idx > 0:
                            page.locator("#bookPageRight .kids-edge-nav-arrow.is-right-arrow").click()
                            page.wait_for_timeout(110)
                        page.evaluate("() => window.fitKidsTextToPatch && fitKidsTextToPatch()")
                        metrics = page.evaluate("() => window.__kidsTextFitMetrics()")
                        assert_fit_metrics(metrics, f"{alias} spread={s_idx + 1}")
            check_clean_page(rec, allow_baseline_puffin_error=env.baseline)
            rec.clear()
    finally:
        ctx.close()


# --- F5: 3 Learning Languages (fr, it, de) (5) ---
@register_test("T1-F5-1", 1, "F5", ("sardegna", "petit-prince"), False, "Settings popover Book Language offers ONLY 3 learning langs (it, fr, de) - no EN")
def t1_f5_1(env: RunnerEnv) -> None:
    targets = active_book_targets(env)
    ctx, page, rec = env.new_session()
    try:
        for alias, _ in targets:
            env.goto_reader(page, open_book_query(env, alias))
            ensure_settings_popover(page, True)
            btns = page.locator("#kidsSettingsPopover .kids-settings-lang-big-grid button").all_inner_texts()
            assert len(btns) == 3, f"Expected 3 book language buttons, got {btns}"
            joined = " ".join(btns).lower()
            assert "english" not in joined, f"English must not appear in book learning languages: {btns}"
            assert all(x in joined for x in ("italiano", "français", "deutsch")), btns
            check_clean_page(rec, allow_baseline_puffin_error=env.baseline)
    finally:
        ctx.close()


@register_test("T1-F5-2", 1, "F5", ("sardegna", "petit-prince"), False, "KIDS_BOOKS_CATALOG supported_langs never contains 'en'")
def t1_f5_2(env: RunnerEnv) -> None:
    targets = active_book_targets(env)
    ctx, page, rec = env.new_session()
    try:
        env.goto_reader(page, open_book_query(env, targets[0][0]))
        check_clean_page(rec, allow_baseline_puffin_error=env.baseline)
        cat_langs = page.evaluate("() => Object.fromEntries(Object.entries(window.KIDS_BOOKS_CATALOG || {}).map(([k,v]) => [k, v.supported_langs]))")
        for _, sid in targets:
            assert sid in cat_langs, f"{sid} missing from KIDS_BOOKS_CATALOG: {list(cat_langs)}"
            langs = cat_langs[sid]
            assert set(langs) == {"fr", "it", "de"} and "en" not in langs, f"{sid} invalid supported_langs: {langs}"
    finally:
        ctx.close()


@register_test("T1-F5-3", 1, "F5", ("sardegna", "petit-prince"), False, "Switching FR -> IT -> DE updates sentence boxes, bubbles, and captions")
def t1_f5_3(env: RunnerEnv) -> None:
    targets = active_book_targets(env)
    ctx, page, rec = env.new_session()
    try:
        for alias, _ in targets:
            env.goto_reader(page, open_book_query(env, alias))
            seen_texts = {}
            for lang in ("fr", "it", "de"):
                switch_book_lang(page, lang)
                state = page.evaluate(
                    """() => ({
                        boxLangs: Array.from(document.querySelectorAll('#openBookSpread .kids-sentence-box')).map(e => e.getAttribute('lang')),
                        bubbleLangs: Array.from(document.querySelectorAll('#openBookSpread .kids-comic-bubble')).map(e => e.getAttribute('lang')),
                        captionLangs: Array.from(document.querySelectorAll('#openBookSpread .kids-figure-caption')).map(e => e.getAttribute('lang')),
                        text: document.querySelector('#bookPageRight .kids-sentence-box')?.innerText || '',
                    })"""
                )
                expected_cnt = 1 if alias == "petit-prince" else 2
                assert state["boxLangs"] == [lang] * expected_cnt, state
                assert all(x == lang for x in state["bubbleLangs"]), state
                assert state["captionLangs"] == [lang] * expected_cnt, state
                seen_texts[lang] = state["text"]
            assert len(set(seen_texts.values())) == 3, f"Expected distinct localized text per lang: {seen_texts}"
            check_clean_page(rec, allow_baseline_puffin_error=env.baseline)
    finally:
        ctx.close()


@register_test("T1-F5-4", 1, "F5", ("petit-prince",), True, "Le Petit Prince defaults to 'fr' when opened via ?book=petit-prince without &lang=")
def t1_f5_4(env: RunnerEnv) -> None:
    env.require_m1_m3(env.has_petit_prince_assets(), "books/petit-prince missing")
    ctx, page, rec = env.new_session()
    try:
        env.goto_reader(page, "?book=petit-prince")
        check_clean_page(rec)
        info = get_active_book_info(page)
        assert info["lang"] == "fr", f"Expected default lang 'fr', got {info['lang']}"
        assert info["langs"] == ["fr", "fr"], info
    finally:
        ctx.close()


@register_test("T1-F5-5", 1, "F5", ("sardegna", "petit-prince"), False, "Switching learning language updates Listen/Quiz labels and audio language prefix")
def t1_f5_5(env: RunnerEnv) -> None:
    targets = active_book_targets(env)
    ctx, page, rec = env.new_session()
    try:
        for alias, _ in targets:
            env.goto_reader(page, open_book_query(env, alias))
            for lang, expected_tag in (("fr", "(FR)"), ("it", "(IT)"), ("de", "(DE)")):
                switch_book_lang(page, lang)
                lbls = page.evaluate(
                    """() => {
                        const l = document.querySelector('#kidsNotebookFloatingBar .listen-pill');
                        const q = document.querySelector('#kidsNotebookFloatingBar .quiz-pill');
                        return {
                            listenAria: l?.getAttribute('aria-label') || '',
                            listenOnclick: l?.getAttribute('onclick') || '',
                            quizTitle: q?.getAttribute('title') || '',
                        };
                    }"""
                )
                assert expected_tag in lbls["listenAria"], lbls
                assert re.search(rf"/{lang}_(seby|ale|emma)", lbls["listenOnclick"]), lbls
                rec.clear()
                page.locator("#kidsNotebookFloatingBar .listen-pill").first.click()
                page.wait_for_timeout(120)
                assert any(re.search(rf"/{lang}_(seby|ale|emma)", u) for u in rec.audio_requests), (
                    f"{alias}/{lang}: expected audio request matching /{lang}_(seby|ale|emma), got {rec.audio_requests}"
                )
                page.locator("#kidsNotebookFloatingBar .listen-pill").first.click()
                page.wait_for_timeout(60)
            check_clean_page(rec, allow_baseline_puffin_error=env.baseline)
    finally:
        ctx.close()


# --- F6: Traduzione Pari Pari (en-GB + pairs) (5) ---
@register_test("T1-F6-1", 1, "F6", ("sardegna", "petit-prince"), False, "Translation selector offers EN, IT, FR, DE and defaults to 'en'")
def t1_f6_1(env: RunnerEnv) -> None:
    targets = active_book_targets(env)
    ctx, page, rec = env.new_session()
    try:
        env.goto_reader(page, open_book_query(env, targets[0][0]))
        check_clean_page(rec, allow_baseline_puffin_error=env.baseline)
        assert get_active_book_info(page)["trLang"] == "en"
        ensure_settings_popover(page, True)
        btns = page.locator("#kidsSettingsPopover .kids-settings-row-small button.kids-pill-control").all_inner_texts()
        joined = " ".join(btns)
        for expected in ("English", "Italiano", "Français", "Deutsch"):
            assert expected in joined, f"Missing {expected} in translation pills: {btns}"
    finally:
        ctx.close()


@register_test("T1-F6-2", 1, "F6", ("sardegna", "petit-prince"), False, "Parallel Mode shows same page on both leaves (1 · LANG vs 1 · EN)")
def t1_f6_2(env: RunnerEnv) -> None:
    targets = active_book_targets(env)
    ctx, page, rec = env.new_session()
    try:
        for alias, _ in targets:
            env.goto_reader(page, open_book_query(env, alias, "&lang=fr"))
            set_parallel_mode(page, True)
            check_clean_page(rec, allow_baseline_puffin_error=env.baseline)
            info = get_active_book_info(page)
            exp_pages = [2, 2] if alias == "petit-prince" else [1, 1]
            assert info["pages"] == exp_pages, f"Expected {exp_pages} in parallel mode, got {info['pages']}"
            assert info["badges"] == ["1 · FR", "1 · EN"], f"Expected ['1 · FR', '1 · EN'], got {info['badges']}"
    finally:
        ctx.close()


@register_test("T1-F6-3", 1, "F6", ("sardegna", "petit-prince"), False, "Turning page next in Parallel Mode advances by step=1")
def t1_f6_3(env: RunnerEnv) -> None:
    targets = active_book_targets(env)
    ctx, page, rec = env.new_session()
    try:
        for alias, _ in targets:
            env.goto_reader(page, open_book_query(env, alias, "&lang=fr&parallel=1"))
            p0 = 2 if alias == "petit-prince" else 1
            assert get_active_book_info(page)["pages"] == [p0, p0]
            page.locator("#bookPageRight .kids-edge-nav-arrow.is-right-arrow").click()
            page.wait_for_timeout(120)
            assert get_active_book_info(page)["pages"] == [p0 + 1, p0 + 1]
            page.locator("#bookPageRight .kids-edge-nav-arrow.is-right-arrow").click()
            page.wait_for_timeout(120)
            assert get_active_book_info(page)["pages"] == [p0 + 2, p0 + 2]
            check_clean_page(rec, allow_baseline_puffin_error=env.baseline)
    finally:
        ctx.close()


@register_test("T1-F6-4", 1, "F6", ("sardegna", "petit-prince"), False, "All 6 parallel pairs fit without overflow + full 26p en-GB translations & catalog parity")
def t1_f6_4(env: RunnerEnv) -> None:
    targets = active_book_targets(env)
    pairs = [("fr", "en"), ("it", "en"), ("de", "en"), ("de", "it"), ("fr", "it"), ("it", "fr")]
    ctx, page, rec = env.new_session()
    try:
        for alias, sid in targets:
            for b_lang, t_lang in pairs:
                env.goto_reader(page, open_book_query(env, alias, f"&mode=emma&lang={b_lang}&parallel=1"))
                switch_translation_lang(page, t_lang)
                page.evaluate("() => window.fitKidsTextToPatch && fitKidsTextToPatch()")
                info = get_active_book_info(page)
                assert info["badges"] == [f"1 · {b_lang.upper()}", f"1 · {t_lang.upper()}"], info
                metrics = page.evaluate("() => window.__kidsTextFitMetrics()")
                assert_fit_metrics(metrics, f"T1-F6-4 {alias} {b_lang}->{t_lang}")
            if sid == PETIT_PRINCE_ID:
                kb_disk = load_book_json(PETIT_PRINCE_ID)
                assert len(kb_disk["pages"]) == 26, f"Expected 26 pages, got {len(kb_disk['pages'])}"
                for pg in kb_disk["pages"]:
                    if pg.get("is_frontispiece"):
                        continue
                    en_tr = pg.get("translations", {}).get("en", {})
                    for tier in ("seby", "ale", "emma"):
                        txt = en_tr.get(tier, {}).get("text", "").strip()
                        assert txt, f"petit-prince P{pg['page']} missing translations.en.{tier}.text"
                cat_pp = page.evaluate("(id) => (window.KIDS_BOOKS_CATALOG || {})[id] || null", PETIT_PRINCE_ID)
                assert cat_pp == kb_disk, "window.KIDS_BOOKS_CATALOG[le-petit-prince] does not match books/petit-prince/kids_book_data.json"
            check_clean_page(rec, allow_baseline_puffin_error=env.baseline)
            rec.clear()
    finally:
        ctx.close()


@register_test("T1-F6-5", 1, "F6", ("sardegna", "petit-prince"), False, "EN Listen uses speechSynthesis en-GB with ZERO .mp3/.ogg requests + en_gloss popover")
def t1_f6_5(env: RunnerEnv) -> None:
    targets = active_book_targets(env)
    ctx, page, rec = env.new_session()
    try:
        for alias, _ in targets:
            env.goto_reader(page, open_book_query(env, alias, "&mode=emma&lang=fr&parallel=1"))
            switch_translation_lang(page, "en")
            rec.clear()
            page.evaluate("() => { window.__kosTtsCalls = []; }")
            right_listen = page.locator("#kidsNotebookFloatingBar .listen-pill").nth(1)
            right_listen.click()
            page.wait_for_timeout(150)
            calls = page.evaluate("() => window.__kosTtsCalls")
            assert len(calls) >= 1, f"{alias}: expected speechSynthesis.speak call for EN listen"
            assert calls[-1]["lang"] == "en-GB", f"{alias}: expected en-GB, got {calls[-1]}"
            assert not rec.audio_requests, f"{alias}: EN listen must trigger ZERO mp3/ogg requests, got {rec.audio_requests}"
            # Verify English gloss popover resolves on word hover (no silent skip)
            gloss_tok = page.locator("#bookPageLeft .kw-token.kw-has-gloss").first
            assert gloss_tok.count() > 0, f"{alias}: expected at least 1 .kw-token.kw-has-gloss on P1 emma/fr"
            gloss_tok.hover()
            page.wait_for_timeout(80)
            pop_text = gloss_tok.locator(".kw-gloss-popover").inner_text()
            assert pop_text.strip(), f"{alias}: expected non-empty English gloss popover text"
            check_clean_page(rec, allow_baseline_puffin_error=env.baseline)
    finally:
        ctx.close()


# --- F7: 5 Reading Speeds (5) ---
@register_test("T1-F7-1", 1, "F7", ("sardegna", "petit-prince"), False, "Settings popover renders exactly 5 reading speed buttons (0.75x..1.3x)")
def t1_f7_1(env: RunnerEnv) -> None:
    targets = active_book_targets(env)
    ctx, page, rec = env.new_session()
    try:
        env.goto_reader(page, open_book_query(env, targets[0][0]))
        ensure_settings_popover(page, True)
        speed_btns = page.locator("#kidsSettingsPopover button[onclick^='setKidsSpeedStep']")
        assert speed_btns.count() == 5, f"Expected 5 speed buttons, got {speed_btns.count()}"
        texts = [speed_btns.nth(i).inner_text().strip() for i in range(5)]
        assert texts == ["0.75×", "0.88×", "1.0×", "1.15×", "1.3×"], f"Unexpected speed labels: {texts}"
        check_clean_page(rec, allow_baseline_puffin_error=env.baseline)
    finally:
        ctx.close()


@register_test("T1-F7-2", 1, "F7", ("sardegna", "petit-prince"), False, "Clicking each speed button updates kos_kids_speed_step (0..4) and active highlight")
def t1_f7_2(env: RunnerEnv) -> None:
    targets = active_book_targets(env)
    ctx, page, rec = env.new_session()
    try:
        env.goto_reader(page, open_book_query(env, targets[0][0]))
        ensure_settings_popover(page, True)
        for idx in range(5):
            page.locator(f"#kidsSettingsPopover button[onclick='setKidsSpeedStep({idx})']").click()
            page.wait_for_timeout(80)
            stored = page.evaluate("() => localStorage.getItem('kos_kids_speed_step')")
            assert stored == str(idx), f"Expected kos_kids_speed_step='{idx}', got {stored}"
            bg = page.locator(f"#kidsSettingsPopover button[onclick='setKidsSpeedStep({idx})']").evaluate("el => el.style.background")
            assert "rgb(245, 158, 11)" in bg or "#f59e0b" in bg.lower(), f"Step {idx} not highlighted: {bg}"
        check_clean_page(rec, allow_baseline_puffin_error=env.baseline)
    finally:
        ctx.close()


@register_test("T1-F7-3", 1, "F7", ("sardegna", "petit-prince"), False, "Playing page audio sets #kidsStaticAudio.playbackRate per speed step")
def t1_f7_3(env: RunnerEnv) -> None:
    targets = active_book_targets(env)
    ctx, page, rec = env.new_session()
    try:
        env.goto_reader(page, open_book_query(env, targets[0][0], "&mode=seby&lang=it"))
        rates = {}
        for step in (0, 2, 4):
            ensure_settings_popover(page, True)
            page.locator(f"#kidsSettingsPopover button[onclick='setKidsSpeedStep({step})']").click()
            ensure_settings_popover(page, False)
            page.locator("#kidsNotebookFloatingBar .listen-pill").first.click()
            page.wait_for_timeout(150)
            rates[step] = page.evaluate("() => document.getElementById('kidsStaticAudio')?.playbackRate")
            # Pause before next step
            page.locator("#kidsNotebookFloatingBar .listen-pill").first.click()
            page.wait_for_timeout(80)
        assert rates[0] < 0.85 and 0.85 <= rates[2] <= 1.05 and rates[4] > 1.10, f"Unexpected playbackRates: {rates}"
        assert rates[0] < rates[2] < rates[4], rates
        check_clean_page(rec, allow_baseline_puffin_error=env.baseline)
    finally:
        ctx.close()


@register_test("T1-F7-4", 1, "F7", ("sardegna",), False, "Changing speed while audio is playing updates playbackRate live without resetting time")
def t1_f7_4(env: RunnerEnv) -> None:
    ctx, page, rec = env.new_session()
    try:
        env.goto_reader(page, open_book_query(env, "sardegna", "&mode=seby&lang=it"))
        page.locator("#kidsNotebookFloatingBar .listen-pill").first.click()
        page.wait_for_timeout(350)
        before = page.evaluate("() => { const a = document.getElementById('kidsStaticAudio'); return { paused: a.paused, t: a.currentTime, r: a.playbackRate }; }")
        assert not before["paused"] and before["t"] > 0.05, f"Expected active playback before speed switch: {before}"
        ensure_settings_popover(page, True)
        page.locator("#kidsSettingsPopover button[onclick='setKidsSpeedStep(4)']").click()
        page.wait_for_timeout(120)
        after = page.evaluate("() => { const a = document.getElementById('kidsStaticAudio'); return { paused: a.paused, t: a.currentTime, r: a.playbackRate }; }")
        assert after["r"] > before["r"] and after["t"] >= before["t"], f"Expected live rate increase without reset: {before} -> {after}"
        check_clean_page(rec, allow_baseline_puffin_error=env.baseline)
    finally:
        ctx.close()


@register_test("T1-F7-5", 1, "F7", ("sardegna", "petit-prince"), False, "Reloading page restores persisted kos_kids_speed_step")
def t1_f7_5(env: RunnerEnv) -> None:
    targets = active_book_targets(env)
    ctx, page, rec = env.new_session()
    try:
        env.goto_reader(page, open_book_query(env, targets[0][0]))
        ensure_settings_popover(page, True)
        page.locator("#kidsSettingsPopover button[onclick='setKidsSpeedStep(1)']").click()
        page.reload(wait_until="networkidle")
        page.wait_for_selector(".kids-sentence-box", timeout=10000)
        ensure_settings_popover(page, True)
        bg = page.locator("#kidsSettingsPopover button[onclick='setKidsSpeedStep(1)']").evaluate("el => el.style.background")
        assert "rgb(245, 158, 11)" in bg or "#f59e0b" in bg.lower(), f"Persisted speed step 1 not restored after reload: {bg}"
        check_clean_page(rec, allow_baseline_puffin_error=env.baseline)
    finally:
        ctx.close()


# --- F8: Montessori Grammar & DE Separable Verbs (5) ---
@register_test("T1-F8-1", 1, "F8", ("sardegna", "petit-prince"), False, "Grammar highlighting is OFF by default on initial load")
def t1_f8_1(env: RunnerEnv) -> None:
    targets = active_book_targets(env)
    ctx, page, rec = env.new_session()
    try:
        env.goto_reader(page, open_book_query(env, targets[0][0]))
        check_clean_page(rec, allow_baseline_puffin_error=env.baseline)
        has_cls = page.evaluate("() => Array.from(document.querySelectorAll('#openBookSpread .kids-watercolor-leaf')).some(e => e.classList.contains('grammar-on'))")
        assert not has_cls, "Expected grammar-on to be OFF by default"
    finally:
        ctx.close()


@register_test("T1-F8-2", 1, "F8", ("sardegna", "petit-prince"), False, "Toggling Grammar adds .grammar-on to both leaves and shows .kw-pos-icon spans")
def t1_f8_2(env: RunnerEnv) -> None:
    targets = active_book_targets(env)
    ctx, page, rec = env.new_session()
    try:
        for alias, _ in targets:
            env.goto_reader(page, open_book_query(env, alias))
            set_grammar_mode(page, True)
            res = page.evaluate(
                """() => ({
                    leavesOn: document.querySelectorAll('#openBookSpread .kids-watercolor-leaf.grammar-on').length,
                    visibleIcons: Array.from(document.querySelectorAll('#openBookSpread .kw-pos-icon')).filter(el => el.textContent.trim() && getComputedStyle(el).display !== 'none').length,
                })"""
            )
            assert res["leavesOn"] == 2 and res["visibleIcons"] >= 4, f"{alias}: {res}"
            check_clean_page(rec, allow_baseline_puffin_error=env.baseline)
    finally:
        ctx.close()


@register_test("T1-F8-3", 1, "F8", ("sardegna", "petit-prince"), False, "IT/FR noun/adj tokens carry data-gender m/f and .kw-end-m/.kw-end-f; DE has empty data-gender")
def t1_f8_3(env: RunnerEnv) -> None:
    targets = active_book_targets(env)
    ctx, page, rec = env.new_session()
    try:
        for alias, _ in targets:
            for lang in ("it", "fr"):
                env.goto_reader(page, open_book_query(env, alias, f"&mode=ale&lang={lang}"))
                set_grammar_mode(page, True)
                counts = page.evaluate(
                    """() => ({
                        gendered: document.querySelectorAll('#openBookSpread .kw-token[data-gender="m"], #openBookSpread .kw-token[data-gender="f"]').length,
                        endings: document.querySelectorAll('#openBookSpread .kw-end-m, #openBookSpread .kw-end-f').length,
                    })"""
                )
                assert counts["gendered"] >= 2 and counts["endings"] >= 2, f"{alias}/{lang}: {counts}"
            env.goto_reader(page, open_book_query(env, alias, "&mode=ale&lang=de"))
            set_grammar_mode(page, True)
            de_g = page.evaluate(
                "() => Array.from(document.querySelectorAll('#openBookSpread .kw-token')).filter(e => e.getAttribute('data-gender')).length"
            )
            assert de_g == 0, f"{alias}/de must not expose IT/FR gender markers, found {de_g}"
            check_clean_page(rec, allow_baseline_puffin_error=env.baseline)
    finally:
        ctx.close()


@register_test("T1-F8-4", 1, "F8", ("sardegna", "petit-prince"), False, "DE separable verb tokens and SVG arcs render on spreads containing separable verbs")
def t1_f8_4(env: RunnerEnv) -> None:
    targets = active_book_targets(env)
    ctx, page, rec = env.new_session()
    try:
        for alias, sid in targets:
            kb = load_book_json(sid)
            # Find first spread with a separable verb in DE
            sep_page = None
            for pg in kb["pages"]:
                for lvl in ("seby", "ale", "emma"):
                    toks = pg.get("levels", {}).get(lvl, {}).get("de", {}).get("tokens", [])
                    if any(t.get("sep_group") for t in toks):
                        sep_page = (pg["page"], lvl)
                        break
                if sep_page:
                    break
            assert sep_page is not None, f"{alias}: no DE separable verb found in catalog"
            pnum, lvl = sep_page
            env.goto_reader(page, open_book_query(env, alias, f"&mode={lvl}&lang=de&page={pnum}"))
            set_grammar_mode(page, True)
            page.wait_for_timeout(120)
            svg_info = page.evaluate(
                """() => {
                    const toks = document.querySelectorAll('#openBookSpread .kw-sep-verb[data-sep-group]');
                    const groups = Array.from(document.querySelectorAll('#openBookSpread svg.kids-sep-verb-arcs g.sep-verb-arc-group'));
                    const paths = groups.map(g => g.querySelector('path.sep-verb-arc-line')?.getAttribute('d') || '');
                    return { tokenCount: toks.length, arcCount: groups.length, paths };
                }"""
            )
            assert svg_info["tokenCount"] >= 2 and svg_info["arcCount"] >= 1, f"{alias}: {svg_info}"
            assert all(p.startswith("M ") and "NaN" not in p for p in svg_info["paths"]), svg_info
            check_clean_page(rec, allow_baseline_puffin_error=env.baseline)
    finally:
        ctx.close()


@register_test("T1-F8-5", 1, "F8", ("sardegna", "petit-prince"), False, "Hovering DE separable verb highlights both stem/prefix (.sep-brother-hover), SVG .active-arc & gloss")
def t1_f8_5(env: RunnerEnv) -> None:
    targets = active_book_targets(env)
    ctx, page, rec = env.new_session()
    try:
        for alias, sid in targets:
            kb = load_book_json(sid)
            sep_page = next(
                (pg["page"], lvl)
                for pg in kb["pages"]
                for lvl in ("seby", "ale", "emma")
                if any(t.get("sep_group") for t in pg.get("levels", {}).get(lvl, {}).get("de", {}).get("tokens", []))
            )
            pnum, lvl = sep_page
            env.goto_reader(page, open_book_query(env, alias, f"&mode={lvl}&lang=de&page={pnum}"))
            set_grammar_mode(page, True)
            tok = page.locator("#openBookSpread .kw-sep-verb[data-sep-group]").first
            gid = tok.get_attribute("data-sep-group")
            tok.hover()
            page.wait_for_timeout(100)
            hover_state = page.evaluate(
                """(gid) => ({
                    brothersHovered: document.querySelectorAll(`#openBookSpread .kw-token[data-sep-group="${gid}"].sep-brother-hover`).length,
                    activeArcs: document.querySelectorAll(`#openBookSpread .sep-verb-arc-group[data-sep-group="${gid}"].active-arc`).length,
                    glossText: document.querySelector(`#openBookSpread .kw-token[data-sep-group="${gid}"] .kw-gloss-popover`)?.textContent || '',
                })""",
                gid,
            )
            assert hover_state["brothersHovered"] >= 2, f"{alias}: {hover_state}"
            assert hover_state["activeArcs"] >= 1, f"{alias}: {hover_state}"
            assert hover_state["glossText"].strip(), f"{alias}: missing sep-verb gloss popover"
            check_clean_page(rec, allow_baseline_puffin_error=env.baseline)
    finally:
        ctx.close()


# --- F9: PuffinLogin Auto-Mapping (5) ---
@register_test("T1-F9-1", 1, "F9", ("sardegna", "petit-prince"), False, "#puffin-widget mounted, window.PuffinLogin initialized, puffin-seed.v1.json has 7 profiles")
def t1_f9_1(env: RunnerEnv) -> None:
    seed = json.loads((REPO_ROOT / "puffin-seed.v1.json").read_text(encoding="utf-8"))
    assert set(seed["profiles"].keys()) == {"riccardo", "kate", "ale", "seby", "lucilla", "guest", "saga"}
    ctx, page, rec = env.new_session()
    try:
        env.goto_reader(page, open_book_query(env, "sardegna"), dismiss_puffin_modal=False)
        check_clean_page(rec, strict_puffin_error=True)
        res = page.evaluate(
            """() => ({
                hasWidget: Boolean(document.getElementById('puffin-widget')),
                hasShadow: Boolean(document.getElementById('puffin-widget')?.shadowRoot),
                hasApi: Boolean(window.PuffinLogin && typeof window.PuffinLogin.getCurrentUser === 'function'),
            })"""
        )
        assert res["hasWidget"] and res["hasShadow"] and res["hasApi"], f"PuffinLogin not initialized: {res}"
    finally:
        ctx.close()


def _verify_puffin_profile_mapping(env: RunnerEnv, profile_id: str, exp_mode: str, exp_tr: str, exp_label: str) -> None:
    ctx, page, rec = env.new_session()
    try:
        q = open_book_query(env, "sardegna")
        # Remove &mode= so profile auto-mapping applies
        q_nomode = re.sub(r"&mode=[^&]+", "", q)
        if q_nomode == "?story=sardegna":
            q_nomode = "?tab=studio"
        env.goto_reader(page, q_nomode, dismiss_puffin_modal=False)
        check_clean_page(rec, strict_puffin_error=True)
        authenticate_puffin_profile(page, profile_id, reload_url=f"{env.base_url}{q_nomode}")
        info = get_active_book_info(page)
        assert info["mode"] == exp_mode, f"{profile_id}: expected mode {exp_mode}, got {info['mode']}"
        assert info["trLang"] == exp_tr, f"{profile_id}: expected trLang {exp_tr}, got {info['trLang']}"
        ensure_settings_popover(page, True)
        pop_text = page.locator("#kidsSettingsPopover").inner_text()
        assert exp_label in pop_text, f"{profile_id}: expected '{exp_label}' in popover: {pop_text}"
        check_clean_page(rec, strict_puffin_error=True)
    finally:
        ctx.close()


@register_test("T1-F9-2", 1, "F9", ("sardegna", "petit-prince"), False, "PuffinLogin 'seby' auto-maps tier to seby and trLang to it")
def t1_f9_2(env: RunnerEnv) -> None:
    _verify_puffin_profile_mapping(env, "seby", "seby", "it", "→ SEBY")


@register_test("T1-F9-3", 1, "F9", ("sardegna", "petit-prince"), False, "PuffinLogin 'ale' auto-maps tier to ale and trLang to it")
def t1_f9_3(env: RunnerEnv) -> None:
    _verify_puffin_profile_mapping(env, "ale", "ale", "it", "→ ALE")


@register_test("T1-F9-4", 1, "F9", ("sardegna", "petit-prince"), False, "PuffinLogin 'riccardo' auto-maps tier to emma and trLang to it")
def t1_f9_4(env: RunnerEnv) -> None:
    _verify_puffin_profile_mapping(env, "riccardo", "emma", "it", "→ EMMA")


@register_test("T1-F9-5", 1, "F9", ("sardegna", "petit-prince"), False, "PuffinLogin 'kate' auto-maps tier to emma and trLang to en (Base: EN)")
def t1_f9_5(env: RunnerEnv) -> None:
    _verify_puffin_profile_mapping(env, "kate", "emma", "en", "Base: EN")


# --- F10: Antolin Quizzes (5) ---
@register_test("T1-F10-1", 1, "F10", ("sardegna", "petit-prince"), False, "Antolin quiz schema: 13 spreads x 3 Qs on petit-prince (even pages) & 16x3 on sardegna")
def t1_f10_1(env: RunnerEnv) -> None:
    for _, sid in active_book_targets(env):
        kb = load_book_json(sid)
        if sid == PETIT_PRINCE_ID:
            even_pages = [p for p in kb["pages"] if p["page"] % 2 == 0]
            assert len(even_pages) == 13
            for p in even_pages:
                for lang in ("fr", "it", "de"):
                    qs = p["questions"][lang]
                    assert len(qs) == 3, f"petit-prince P{p['page']}/{lang}: expected 3 Qs"
                    diffs = [q["difficulty"] for q in qs]
                    assert diffs.count("easy") == 2 and diffs.count("hard") == 1, diffs
        else:
            assert len(kb["pages"]) == 16
            for p in kb["pages"]:
                for lang in ("it", "fr", "de"):
                    assert len(p["questions"][lang]) == 3


@register_test("T1-F10-2", 1, "F10", ("sardegna", "petit-prince"), False, "Clicking .quiz-pill opens #antolinQuizDialog with 3 questions and ⭐ 0 / 3")
def t1_f10_2(env: RunnerEnv) -> None:
    targets = active_book_targets(env)
    ctx, page, rec = env.new_session()
    try:
        for alias, _ in targets:
            env.goto_reader(page, open_book_query(env, alias))
            page.locator("#kidsNotebookFloatingBar .quiz-pill").click()
            page.wait_for_selector("#antolinQuizDialog[open]", timeout=4000)
            assert page.locator("#antolinQuizBody .antolin-question-card").count() == 3
            assert "⭐ 0 / 3" in page.locator("#antolinQuizBody").inner_text()
            page.locator("#antolinQuizDialog button:has-text('Torna'), #antolinQuizDialog button:has-text('Retour'), #antolinQuizDialog button:has-text('Zurück')").first.click()
            check_clean_page(rec, allow_baseline_puffin_error=env.baseline)
    finally:
        ctx.close()


@register_test("T1-F10-3", 1, "F10", ("sardegna", "petit-prince"), False, "Answering correctly marks .correct, increments ⭐ 1 / 3, and logs kos_antolin_question_logs_v1")
def t1_f10_3(env: RunnerEnv) -> None:
    targets = active_book_targets(env)
    ctx, page, rec = env.new_session()
    try:
        alias, sid = targets[-1]
        kb = load_book_json(sid)
        p2 = kb["pages"][1]
        lang = "fr" if sid == PETIT_PRINCE_ID else "it"
        correct_idx = p2["questions"][lang][0]["correct"]

        env.goto_reader(page, open_book_query(env, alias, f"&lang={lang}"))
        page.locator("#kidsNotebookFloatingBar .quiz-pill").click()
        page.wait_for_selector("#antolinQuizDialog[open]", timeout=4000)
        first_card = page.locator("#antolinQuizBody .antolin-question-card").first
        first_card.locator(".antolin-opt-btn").nth(correct_idx).click()
        page.wait_for_timeout(120)
        assert first_card.locator(".antolin-opt-btn").nth(correct_idx).evaluate("el => el.classList.contains('correct')")
        assert "⭐ 1 / 3" in page.locator("#antolinQuizBody").inner_text()
        logs = page.evaluate("() => JSON.parse(localStorage.getItem('kos_antolin_question_logs_v1') || '[]')")
        assert len(logs) >= 1 and logs[0]["isCorrect"] is True, logs
        check_clean_page(rec, allow_baseline_puffin_error=env.baseline)
    finally:
        ctx.close()


@register_test("T1-F10-4", 1, "F10", ("sardegna", "petit-prince"), False, "Answering wrongly marks .wrong AND reveals true .correct without incrementing score")
def t1_f10_4(env: RunnerEnv) -> None:
    targets = active_book_targets(env)
    ctx, page, rec = env.new_session()
    try:
        alias, sid = targets[-1]
        kb = load_book_json(sid)
        p2 = kb["pages"][1]
        lang = "fr" if sid == PETIT_PRINCE_ID else "it"
        correct_idx = p2["questions"][lang][0]["correct"]
        wrong_idx = (correct_idx + 1) % 3

        env.goto_reader(page, open_book_query(env, alias, f"&lang={lang}"))
        page.locator("#kidsNotebookFloatingBar .quiz-pill").click()
        page.wait_for_selector("#antolinQuizDialog[open]", timeout=4000)
        first_card = page.locator("#antolinQuizBody .antolin-question-card").first
        first_card.locator(".antolin-opt-btn").nth(wrong_idx).click()
        page.wait_for_timeout(120)
        assert first_card.locator(".antolin-opt-btn").nth(wrong_idx).evaluate("el => el.classList.contains('wrong')")
        assert first_card.locator(".antolin-opt-btn").nth(correct_idx).evaluate("el => el.classList.contains('correct')")
        assert "⭐ 0 / 3" in page.locator("#antolinQuizBody").inner_text()
        check_clean_page(rec, allow_baseline_puffin_error=env.baseline)
    finally:
        ctx.close()


@register_test("T1-F10-5", 1, "F10", ("sardegna", "petit-prince"), False, "Completing all 3 quiz questions updates .quiz-pill (❓ ⭐3/3) and logs all 3 entries")
def t1_f10_5(env: RunnerEnv) -> None:
    targets = active_book_targets(env)
    ctx, page, rec = env.new_session()
    try:
        alias, sid = targets[-1]
        kb = load_book_json(sid)
        p2 = kb["pages"][1]
        lang = "fr" if sid == PETIT_PRINCE_ID else "it"
        qs = p2["questions"][lang]

        env.goto_reader(page, open_book_query(env, alias, f"&lang={lang}"))
        page.locator("#kidsNotebookFloatingBar .quiz-pill").click()
        page.wait_for_selector("#antolinQuizDialog[open]", timeout=4000)
        for q_idx, q in enumerate(qs):
            card = page.locator("#antolinQuizBody .antolin-question-card").nth(q_idx)
            card.locator(".antolin-opt-btn").nth(q["correct"]).click()
            page.wait_for_timeout(80)
        assert "⭐ 3 / 3" in page.locator("#antolinQuizBody").inner_text()
        page.locator("#antolinQuizDialog button:has-text('Torna'), #antolinQuizDialog button:has-text('Retour'), #antolinQuizDialog button:has-text('Zurück')").first.click()
        pill_txt = page.locator("#kidsNotebookFloatingBar .quiz-pill").inner_text()
        assert "3/3" in pill_txt, f"Expected 3/3 on .quiz-pill, got {pill_txt}"
        logs = page.evaluate("() => JSON.parse(localStorage.getItem('kos_antolin_question_logs_v1') || '[]')")
        assert len(logs) >= 3, logs
        check_clean_page(rec, allow_baseline_puffin_error=env.baseline)
    finally:
        ctx.close()


# --- F11: Constitution, Copyright & Audio Invariant (5) ---
@register_test("T1-F11-1", 1, "F11", ("sardegna", "petit-prince"), True, "docs/CONSTITUTION.md exists and documents FR/IT/DE + en-GB translation-only + zero EN audio")
def t1_f11_1(env: RunnerEnv) -> None:
    const_path = REPO_ROOT / "docs" / "CONSTITUTION.md"
    env.require_m1_m3(const_path.exists(), "docs/CONSTITUTION.md does not exist")
    txt = const_path.read_text(encoding="utf-8")
    for token in ("FR", "IT", "DE", "en-GB"):
        assert token in txt, f"docs/CONSTITUTION.md missing '{token}'"
    assert re.search(r"(no|zero|non|never|mai).{0,40}(audio|tts|mp3)", txt, re.IGNORECASE), (
        "docs/CONSTITUTION.md must explicitly forbid EN studio TTS audio"
    )


@register_test("T1-F11-2", 1, "F11", ("petit-prince",), True, "README.md includes Le Petit Prince and CH/EU (2015) vs France (2032) public-domain note")
def t1_f11_2(env: RunnerEnv) -> None:
    readme_path = REPO_ROOT / "README.md"
    txt = readme_path.read_text(encoding="utf-8")
    env.require_m1_m3("Petit Prince" in txt, "README.md does not yet document Le Petit Prince")
    assert "2015" in txt and "2032" in txt, "README.md must mention CH/EU 2015 vs France 2032 public-domain status"


def _assert_valid_audio_file(rel: str, fmt_k: str, ctx_label: str) -> None:
    assert rel, f"{ctx_label} {fmt_k}: missing path"
    p = REPO_ROOT / rel
    assert p.exists() and p.stat().st_size > 512, f"{ctx_label} {fmt_k}: missing/empty {rel}"
    hdr = p.read_bytes()[:4]
    if fmt_k == "audio_mp3":
        is_mp3 = hdr[:3] == b"ID3" or (len(hdr) >= 2 and hdr[0] == 0xFF and (hdr[1] & 0xE0) == 0xE0)
        assert is_mp3, f"{ctx_label} {fmt_k}: {rel} invalid MP3 magic bytes {hdr!r}"
    elif fmt_k == "audio_ogg":
        assert hdr[:4] == b"OggS", f"{ctx_label} {fmt_k}: {rel} invalid OGG magic bytes {hdr!r}"


@register_test("T1-F11-3", 1, "F11", ("sardegna", "petit-prince"), False, "All story plates (25 petit-prince, 16 sardegna) in FR/IT/DE have valid .mp3 and .ogg studio audio")
def t1_f11_3(env: RunnerEnv) -> None:
    for _, sid in active_book_targets(env):
        kb = load_book_json(sid)
        for pg in kb["pages"]:
            if pg.get("is_frontispiece"):
                continue
            for lang in ("fr", "it", "de"):
                for lvl in ("seby", "ale"):
                    d = pg["levels"][lvl][lang]
                    for fmt_k in ("audio_mp3", "audio_ogg"):
                        _assert_valid_audio_file(d.get(fmt_k, ""), fmt_k, f"{sid} P{pg['page']} {lvl}/{lang}")
                if sid == PETIT_PRINCE_ID:
                    d_emma = pg["levels"]["emma"][lang]
                    for fmt_k in ("audio_mp3", "audio_ogg"):
                        _assert_valid_audio_file(d_emma.get(fmt_k, ""), fmt_k, f"{sid} P{pg['page']} emma/{lang}")
                sb = pg["speech_bubble"][lang]
                for fmt_k in ("audio_mp3", "audio_ogg"):
                    _assert_valid_audio_file(sb.get(fmt_k, ""), fmt_k, f"{sid} P{pg['page']} bubble/{lang}")


@register_test("T1-F11-4", 1, "F11", ("sardegna", "petit-prince"), False, "Zero EN studio audio invariant on disk and in catalog JSON")
def t1_f11_4(env: RunnerEnv) -> None:
    audio_dirs = [
        REPO_ROOT / "stories" / "alessandro" / SARDEGNA_ID / "kids_audio",
    ]
    if (REPO_ROOT / "books" / "petit-prince" / "kids_audio").exists():
        audio_dirs.append(REPO_ROOT / "books" / "petit-prince" / "kids_audio")
    for adir in audio_dirs:
        bad = [
            f.name for f in adir.iterdir()
            if f.is_file() and re.search(r"(?:^|[_-])en(?:[._-]|$)", f.name, re.IGNORECASE)
        ]
        assert not bad, f"Forbidden EN studio audio files in {adir}: {bad}"
    assert not (REPO_ROOT / "assets" / "words_audio" / "en").exists(), "assets/words_audio/en must not exist"
    for _, sid in active_book_targets(env):
        kb = load_book_json(sid)
        assert "en" not in kb.get("supported_langs", [])
        for pg in kb["pages"]:
            assert "en" not in (pg.get("levels") or {}), f"{sid} P{pg['page']} has forbidden levels.en"
            sb_en = (pg.get("speech_bubble") or {}).get("en") or {}
            assert not sb_en.get("audio_mp3") and not sb_en.get("audio_ogg"), sb_en
            tr_en = (pg.get("translations") or {}).get("en") or {}
            for lvl_k, lvl_v in tr_en.items():
                if isinstance(lvl_v, dict):
                    assert not lvl_v.get("audio_mp3") and not lvl_v.get("audio_ogg"), (
                        f"{sid} P{pg['page']} translations.en.{lvl_k} has forbidden audio field: {lvl_v}"
                    )


@register_test("T1-F11-5", 1, "F11", ("sardegna", "petit-prince"), False, "Every plate image is 896x1200 RGB JPEG and renders with naturalWidth=896, naturalHeight=1200")
def t1_f11_5(env: RunnerEnv) -> None:
    for alias, sid in active_book_targets(env):
        kb = load_book_json(sid)
        for pg in kb["pages"]:
            img_path = REPO_ROOT / pg["image"]
            assert img_path.exists(), f"Missing plate {img_path}"
            w, h, comps = parse_jpeg_info(img_path)
            assert (w, h, comps) == (896, 1200, 3), f"{pg['image']}: got {w}x{h} comps={comps}"
    ctx, page, rec = env.new_session()
    try:
        for alias, _ in active_book_targets(env):
            env.goto_reader(page, open_book_query(env, alias))
            dims = page.evaluate(
                """() => Promise.all(
                    Array.from(document.querySelectorAll('#openBookSpread .kids-watercolor-leaf')).map(leaf => {
                        const m = /url\\(["']?([^"')]+)["']?\\)/.exec(leaf.style.backgroundImage || '');
                        if (!m) return Promise.resolve({ ok: false });
                        return new Promise(res => {
                            const im = new Image();
                            im.onload = () => res({ ok: true, w: im.naturalWidth, h: im.naturalHeight, src: m[1] });
                            im.onerror = () => res({ ok: false, src: m[1] });
                            im.src = m[1];
                        });
                    })
                )"""
            )
            for d in dims:
                assert d["ok"] and d["w"] == 896 and d["h"] == 1200, f"{alias} plate render mismatch: {d}"
            check_clean_page(rec, allow_baseline_puffin_error=env.baseline)
    finally:
        ctx.close()


# --- F12: /books YouTube-Style Bookshelf Showcase (5) ---
@register_test("T1-F12-1", 1, "F12", ("sardegna", "petit-prince"), False, "Both /books and /books/ load cleanly (200 OK, ends with /books/, 0 pageerrors, 0 asset 404s)", requires_m5=True)
def t1_f12_1(env: RunnerEnv) -> None:
    import urllib.request

    env.require_m5(env.has_bookshelf(), "books/index.html missing")

    class _NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ARG002
            return None

    opener = urllib.request.build_opener(_NoRedirect)
    try:
        resp_raw = opener.open(f"{env.base_origin}/books")
        assert resp_raw.status == 200
    except urllib.error.HTTPError as err:
        assert err.code in (301, 302, 307, 308), f"Unexpected status on /books: {err.code}"
        loc = err.headers.get("Location", "")
        assert loc.endswith("/books/"), f"Expected /books redirect Location ending with /books/, got '{loc}'"

    ctx, page, rec = env.new_session()
    try:
        for path in ("/books", "/books/"):
            resp = goto_bookshelf(page, env, path, wait_fonts=False)
            page.wait_for_load_state("networkidle")
            page.evaluate("() => document.fonts ? document.fonts.ready : Promise.resolve()")
            assert resp is not None and resp.status == 200, f"{path}: expected HTTP 200, got {resp.status if resp else None}"
            url_path = page.url.split("?", 1)[0]
            assert url_path.endswith("/books/") or (path == "/books" and url_path.endswith("/books")), (
                f"{path}: expected URL ending with /books/ (or /books if served directly), got {page.url}"
            )
            html = page.content()
            assert "Directory listing for" not in html, f"{path}: served directory listing instead of books/index.html"
            check_clean_page(rec)
    finally:
        ctx.close()


@register_test("T1-F12-2", 1, "F12", ("sardegna", "petit-prince"), False, "/books/ displays side-by-side cards (1440x900) with deduplicated editorial serif title & author INSIDE cover", requires_m5=True)
def t1_f12_2(env: RunnerEnv) -> None:
    env.require_m5(env.has_bookshelf(), "books/index.html missing")
    ctx, page, rec = env.new_session(viewport={"width": 1440, "height": 900})
    try:
        resp = goto_bookshelf(page, env, "/books/")
        assert resp is not None and resp.status == 200
        check_clean_page(rec)
        cards = inspect_bookshelf_cards(page)
        assert "sardegna" in cards and "petit-prince" in cards, f"Expected both book cards on /books/, got {list(cards)}"
        card_a = cards["sardegna"]
        card_b = cards["petit-prince"]

        serif_re = re.compile(
            r"""cormorant|garamond|playfair|crimson|georgia|times|(?:^|[\s,'"])(?:ui-)?serif(?=$|[\s,'"])""",
            re.IGNORECASE,
        )
        for name, card in (("sardegna", card_a), ("petit-prince", card_b)):
            assert card["cardRect"]["width"] >= 240, f"{name}: expected substantial card width >= 240px, got {card['cardRect']}"
            assert card["titleRect"] is not None, f"{name}: missing visible card title inside cover"
            assert card["imgRect"]["top"] <= card["titleRect"]["top"], (
                f"{name}: title must sit inside upper cover parchment: title={card['titleRect']} img={card['imgRect']}"
            )
            assert card["titleRect"]["bottom"] <= card["imgRect"]["top"] + card["imgRect"]["height"] * 0.28, (
                f"{name}: title bottom exceeds upper 28% cover parchment band: title={card['titleRect']} img={card['imgRect']}"
            )
            assert card["imgRect"]["left"] <= card["titleRect"]["left"] and card["titleRect"]["right"] <= card["imgRect"]["right"], (
                f"{name}: title overflows horizontally outside cover bounds: title={card['titleRect']} img={card['imgRect']}"
            )
            assert serif_re.search(card.get("titleFontFamily", "")), (
                f"{name}: expected editorial serif font on card title, got {card.get('titleFontFamily')!r}"
            )
            header_blob = f"{card.get('titleText', '')} {card.get('headerText', '')} {card.get('authorText', '')}".lower()
            if name == "sardegna":
                assert "vacanze in sardegna" in card.get("titleText", "").lower(), (
                    f"{name}: expected card title 'Vacanze in Sardegna', got {card.get('titleText')!r}"
                )
                assert "riccardo carlesso" in header_blob, (
                    f"{name}: expected author credit 'Riccardo Carlesso' in card header, got {header_blob!r}"
                )
                assert "cala gonone" not in header_blob and "arbatax" not in header_blob, (
                    f"{name}: expected deduplicated single title (no 'Cala Gonone & Arbatax'), got {header_blob!r}"
                )
            else:
                assert "le petit prince" in card.get("titleText", "").lower(), (
                    f"{name}: expected card title 'Le Petit Prince', got {card.get('titleText')!r}"
                )
                assert re.search(r"saint-exup[eé]ry", header_blob), (
                    f"{name}: expected author credit 'Antoine de Saint-Exupéry' in card header, got {header_blob!r}"
                )
                assert "piccolo principe" not in header_blob, (
                    f"{name}: expected deduplicated single title (no 'Il Piccolo Principe'), got {header_blob!r}"
                )
            img = card["img"]
            assert img["complete"] and img["naturalWidth"] > 0 and img["naturalHeight"] > 0, f"{name}: broken cover img {img}"
            img_status = page.evaluate("(src) => fetch(src).then(r => r.status)", img["src"])
            assert img_status == 200, f"{name}: expected cover image HTTP 200, got {img_status} for {img['src']}"

        assert abs(card_a["cardRect"]["left"] - card_b["cardRect"]["left"]) >= 200, (
            f"Expected side-by-side horizontal separation on 1440x900: A={card_a['cardRect']} B={card_b['cardRect']}"
        )
        assert abs(card_a["cardRect"]["top"] - card_b["cardRect"]["top"]) <= 80, (
            f"Expected both cards on same desktop row: A={card_a['cardRect']} B={card_b['cardRect']}"
        )
        check_clean_page(rec)
    finally:
        ctx.close()


@register_test("T1-F12-3", 1, "F12", ("sardegna", "petit-prince"), False, "Clicking Sardegna and Le Petit Prince cards opens ?book=sardegna (16p) and ?book=petit-prince (26p)", requires_m5=True)
def t1_f12_3(env: RunnerEnv) -> None:
    env.require_m5(env.has_bookshelf(), "books/index.html missing")
    ctx, page, rec = env.new_session()
    try:
        goto_bookshelf(page, env, "/books/")
        click_bookshelf_target(page, "sardegna")
        page.wait_for_selector(".kids-sentence-box", timeout=10000)
        page.wait_for_timeout(140)
        check_clean_page(rec)
        info_sar = get_active_book_info(page)
        assert info_sar["storyId"] == SARDEGNA_ID and info_sar["totalPages"] == 16, info_sar
        assert is_kids_fullscreen(page)

        goto_bookshelf(page, env, "/books/")
        if env.baseline and not env.has_petit_prince_assets():
            cards = inspect_bookshelf_cards(page)
            pp = cards.get("petit-prince", {})
            assert any("petit-prince" in l.get("href", "") or "petit-prince" in l.get("absHref", "") for l in pp.get("links", [])), (
                f"Expected petit-prince card link href pointing to petit-prince: {pp}"
            )
            return

        env.require_m1_m3(env.has_petit_prince_assets(), "books/petit-prince missing")
        click_bookshelf_target(page, "petit-prince")
        page.wait_for_selector(".kids-sentence-box", timeout=10000)
        page.wait_for_timeout(140)
        check_clean_page(rec)
        info_pp = get_active_book_info(page)
        assert info_pp["storyId"] == PETIT_PRINCE_ID and info_pp["totalPages"] == 26, info_pp
        assert is_kids_fullscreen(page)
    finally:
        ctx.close()


@register_test("T1-F12-4", 1, "F12", ("sardegna",), False, "/books/ displays visible bookmark resume indicator for saved book and navigates to page 7", requires_m5=True)
def t1_f12_4(env: RunnerEnv) -> None:
    env.require_m5(env.has_bookshelf(), "books/index.html missing")
    ctx, page, rec = env.new_session()
    try:
        bm_payload = {
            SARDEGNA_ID: {
                "page": 7,
                "mode": "ale",
                "lang": "it",
                "trLang": "en",
                "parallel": False,
                "savedAt": "2026-11-23T19:00:00.000Z",
            }
        }
        ctx.add_init_script(f"localStorage.setItem('kos_kids_bookmarks_v1', {json.dumps(json.dumps(bm_payload))});")
        goto_bookshelf(page, env, "/books/")
        check_clean_page(rec)
        cards = inspect_bookshelf_cards(page)
        assert "sardegna" in cards, cards
        hits = cards["sardegna"]["resumeHits"]
        assert hits, f"Expected visible bookmark resume indicator on Sardegna card, got {cards['sardegna']}"
        assert any("7" in h["text"] or "page=7" in h["href"] for h in hits), f"Expected page 7 in resume indicator: {hits}"

        click_bookshelf_target(page, "sardegna", prefer_resume=True)
        page.wait_for_selector(".kids-sentence-box", timeout=10000)
        page.wait_for_timeout(140)
        check_clean_page(rec)
        info = get_active_book_info(page)
        assert info["storyId"] == SARDEGNA_ID and info["pages"] == [7, 8], info
    finally:
        ctx.close()


@register_test("T1-F12-5", 1, "F12", ("sardegna", "petit-prince"), False, "index.html renders active book title in fullscreen reader and provides a clean visible link to /books/", requires_m5=True)
def t1_f12_5(env: RunnerEnv) -> None:
    env.require_m5(env.has_bookshelf(), "books/index.html missing")
    ctx, page, rec = env.new_session()
    try:
        env.goto_reader(page, "?book=sardegna")
        check_clean_page(rec)
        hdr = inspect_reader_book_header(page, "sardegna")
        assert hdr["found"], f"Expected visible active book title ('Vacanze in Sardegna') in fullscreen reader: {hdr}"
        assert any(m["hasStrictTitle"] and m["hasSerif"] for m in hdr["matches"]), (
            f"Expected polished editorial serif title 'Vacanze in Sardegna' in reader header: {hdr['matches']}"
        )
        find_and_click_books_link(page)
        page.wait_for_url(re.compile(r"/books/?(\?.*)?$"), timeout=8000)
        page.wait_for_load_state("networkidle")
        assert page.url.split("?", 1)[0].endswith("/books/"), f"Expected navigation to /books/, got {page.url}"
        cards = inspect_bookshelf_cards(page)
        assert "sardegna" in cards and "petit-prince" in cards, cards
        check_clean_page(rec)
    finally:
        ctx.close()


# ===========================================================================
# TIER 2: 61 Boundary & Corner-Case Tests (5 per feature F1-F12 + Escape)
# ===========================================================================

# --- F1 Boundaries (5) ---
@register_test("T2-F1-1", 2, "F1", ("sardegna", "petit-prince"), True, "Unknown ?book=nonexistent falls back gracefully without crash")
def t2_f1_1(env: RunnerEnv) -> None:
    if env.baseline:
        raise SkipTest("pre-M1/M3 baseline: ?book= routing not yet implemented")
    ctx, page, rec = env.new_session()
    try:
        env.goto_reader(page, "?book=nonexistent-book-xyz", wait_selector="#openBookSpread:visible, #indexView:visible")
        check_clean_page(rec)
    finally:
        ctx.close()


@register_test("T2-F1-2", 2, "F1", ("petit-prince",), True, "Aliases petit_prince, piccolo-principe, der-kleine-prinz resolve to le-petit-prince")
def t2_f1_2(env: RunnerEnv) -> None:
    env.require_m1_m3(env.has_petit_prince_assets(), "books/petit-prince missing")
    ctx, page, rec = env.new_session()
    try:
        for alias in ("petit_prince", "piccolo-principe", "der-kleine-prinz"):
            env.goto_reader(page, f"?book={alias}")
            check_clean_page(rec)
            info = get_active_book_info(page)
            assert info["storyId"] == PETIT_PRINCE_ID, f"?book={alias} resolved to {info['storyId']}"
    finally:
        ctx.close()


@register_test("T2-F1-3", 2, "F1", ("petit-prince",), True, "?book=petit-prince&page=0 clamps to P1 and &page=999 clamps to P25-P26")
def t2_f1_3(env: RunnerEnv) -> None:
    env.require_m1_m3(env.has_petit_prince_assets(), "books/petit-prince missing")
    ctx, page, rec = env.new_session()
    try:
        env.goto_reader(page, "?book=petit-prince&page=0")
        assert get_active_book_info(page)["pages"] == [1, 2]
        env.goto_reader(page, "?book=petit-prince&page=999")
        assert get_active_book_info(page)["pages"] == [25, 26]
        check_clean_page(rec)
    finally:
        ctx.close()


@register_test("T2-F1-4", 2, "F1", ("sardegna", "petit-prince"), False, "?lang=en in Kids Book mode coerces to valid learning lang (fr/it/de), not empty text")
def t2_f1_4(env: RunnerEnv) -> None:
    targets = active_book_targets(env)
    ctx, page, rec = env.new_session()
    try:
        for alias, _ in targets:
            env.goto_reader(page, open_book_query(env, alias, "&lang=en"))
            check_clean_page(rec, allow_baseline_puffin_error=env.baseline)
            info = get_active_book_info(page)
            assert info["langs"][0] in ("fr", "it", "de") and info["langs"][0] != "en", info
            txt = page.locator("#openBookSpread .kids-sentence-box").first.inner_text().strip()
            assert len(txt) > 10, f"Expected valid coerced learning text, got '{txt}'"
    finally:
        ctx.close()


@register_test("T2-F1-5", 2, "F1", ("sardegna", "petit-prince"), True, "?book=petit-prince overrides stale localStorage and bare ?story=sardegna resolves to sardegna")
def t2_f1_5(env: RunnerEnv) -> None:
    if env.baseline:
        # Check bare ?story=sardegna without &mode= to expose baseline bug accurately if present
        ctx, page, rec = env.new_session()
        try:
            env.goto_reader(page, "?story=sardegna", wait_selector="#bookViewport")
            info = get_active_book_info(page)
            assert info["storyId"] == SARDEGNA_ID, (
                f"Bare ?story=sardegna fell back to {info['storyId']} instead of {SARDEGNA_ID}"
            )
        finally:
            ctx.close()
        return

    env.require_m1_m3(env.has_petit_prince_assets(), "books/petit-prince missing")
    ctx, page, rec = env.new_session()
    try:
        env.goto_reader(page, "?book=sardegna&page=5")
        env.goto_reader(page, "?book=petit-prince")
        check_clean_page(rec)
        assert get_active_book_info(page)["storyId"] == PETIT_PRINCE_ID
        env.goto_reader(page, "?story=sardegna", wait_selector="#bookViewport, #openBookSpread")
        assert get_active_book_info(page)["storyId"] == SARDEGNA_ID
    finally:
        ctx.close()


@register_test("T2-F1-6", 2, "F1", ("sardegna", "petit-prince"), True, "Prototype keys (?book=toString/__proto__), answerAntolinQuestion('toString'), negative page & hostile XSS bookmarks degrade safely")
def t2_f1_6(env: RunnerEnv) -> None:
    env.require_m5(env.has_bookshelf(), "books/index.html missing")
    hostile_bm = {
        "__proto__": {"page": 5},
        PETIT_PRINCE_ID: {"page": 999, "mode": "<img src=x onerror=window.__xss=1>", "lang": "en", "trLang": "evil"},
        SARDEGNA_ID: {"page": "7<script>window.__xss=2</script>", "mode": "ale"},
    }
    ctx, page, rec = env.new_session()
    try:
        ctx.add_init_script(f"localStorage.setItem('kos_kids_bookmarks_v1', {json.dumps(json.dumps(hostile_bm))});")
        for q in ("?book=toString", "?book=constructor", "?book=__proto__", "/books/?book=toString"):
            page.goto(f"{env.base_origin}/{q.lstrip('/')}", wait_until="networkidle")
            check_clean_page(rec)
        page.goto(f"{env.base_origin}/books//?book=sardegna", wait_until="networkidle")
        page.wait_for_url(lambda u: "/books" not in u.split("?", 1)[0], timeout=10000)
        page.wait_for_selector("#bookViewport, #openBookSpread", timeout=10000)
        assert get_active_book_info(page)["storyId"] == SARDEGNA_ID, get_active_book_info(page)
        check_clean_page(rec)
        env.goto_reader(page, "?book=petit-prince&page=-1")
        assert get_active_book_info(page)["pages"] == [1, 2], get_active_book_info(page)
        click_bookmark_button(page, "resume")
        info_bm = get_active_book_info(page)
        assert info_bm["pages"] == [25, 26] and info_bm["mode"] in ("seby", "ale", "emma") and info_bm["lang"] in ("fr", "it", "de"), info_bm
        assert page.evaluate("() => window.__xss || null") is None
        res_antolin = page.evaluate("async () => { await answerAntolinQuestion('toString', 1, 'q1', 0); return 'ok'; }")
        assert res_antolin == "ok", res_antolin
        goto_bookshelf(page, env, "/books/")
        assert page.evaluate("() => window.__xss || null") is None
        check_clean_page(rec)
    finally:
        ctx.close()


# --- F2 Boundaries (5) ---
@register_test("T2-F2-1", 2, "F2", ("sardegna", "petit-prince"), True, "Switching book pauses active #kidsStaticAudio playback")
def t2_f2_1(env: RunnerEnv) -> None:
    env.require_m1_m3(env.has_petit_prince_assets(), "books/petit-prince missing")
    ctx, page, rec = env.new_session()
    try:
        env.goto_reader(page, "?book=sardegna")
        page.locator("#kidsNotebookFloatingBar .listen-pill").first.click()
        page.wait_for_timeout(180)
        select_book_in_ui(page, "petit-prince")
        paused = page.evaluate("() => document.getElementById('kidsStaticAudio')?.paused !== false")
        assert paused, "Expected #kidsStaticAudio to pause on book switch"
        check_clean_page(rec)
    finally:
        ctx.close()


@register_test("T2-F2-2", 2, "F2", ("sardegna", "petit-prince"), True, "Switching book while #kidsSettingsPopover is open keeps UI responsive")
def t2_f2_2(env: RunnerEnv) -> None:
    env.require_m1_m3(env.has_petit_prince_assets(), "books/petit-prince missing")
    ctx, page, rec = env.new_session()
    try:
        env.goto_reader(page, "?book=sardegna")
        ensure_settings_popover(page, True)
        select_book_in_ui(page, "petit-prince")
        page.locator("#bookPageRight .kids-edge-nav-arrow.is-right-arrow").click()
        page.wait_for_timeout(120)
        assert get_active_book_info(page)["pages"] == [3, 4]
        check_clean_page(rec)
    finally:
        ctx.close()


@register_test("T2-F2-3", 2, "F2", ("sardegna", "petit-prince"), True, "Switching from petit-prince P25-P26 to sardegna (16p) clamps page safely <= 16")
def t2_f2_3(env: RunnerEnv) -> None:
    env.require_m1_m3(env.has_petit_prince_assets(), "books/petit-prince missing")
    ctx, page, rec = env.new_session()
    try:
        env.goto_reader(page, "?book=petit-prince&page=25")
        assert get_active_book_info(page)["pages"] == [25, 26]
        select_book_in_ui(page, "sardegna")
        info = get_active_book_info(page)
        assert info["storyId"] == SARDEGNA_ID
        assert all(1 <= p <= 16 for p in info["pages"]), f"Page out of bounds after switch: {info['pages']}"
        check_clean_page(rec)
    finally:
        ctx.close()


@register_test("T2-F2-4", 2, "F2", ("sardegna", "petit-prince"), True, "Switching books isolates _sharedGrammarIndexCache per bookId:lang")
def t2_f2_4(env: RunnerEnv) -> None:
    env.require_m1_m3(env.has_petit_prince_assets(), "books/petit-prince missing")
    ctx, page, rec = env.new_session()
    try:
        env.goto_reader(page, "?book=sardegna&mode=emma&lang=fr")
        select_book_in_ui(page, "petit-prince")
        page.locator("#kidsNotebookFloatingBar .listen-pill").first.click()
        page.wait_for_timeout(120)
        src = page.evaluate("() => document.getElementById('kidsStaticAudio')?.getAttribute('src') || ''")
        assert "books/petit-prince/" in src and "sardegna" not in src, f"Audio/cache leakage across books: {src}"
        check_clean_page(rec)
    finally:
        ctx.close()


@register_test("T2-F2-5", 2, "F2", ("sardegna", "petit-prince"), True, "Switching book in non-fullscreen mode via visible control updates active spread")
def t2_f2_5(env: RunnerEnv) -> None:
    env.require_m1_m3(env.has_petit_prince_assets(), "books/petit-prince missing")
    ctx, page, rec = env.new_session()
    try:
        env.goto_reader(page, "?book=sardegna")
        page.locator("#kidsNotebookFloatingBar button[title='Tutta Pagina']").click()
        page.wait_for_timeout(120)
        assert not is_kids_fullscreen(page)
        launch_bar = page.locator("#kidsReadingLaunchBar")
        assert launch_bar.is_visible(), "Expected #kidsReadingLaunchBar visible in non-fullscreen mode"
        select_book_in_ui(page, "petit-prince")
        info = get_active_book_info(page)
        assert info["storyId"] == PETIT_PRINCE_ID and info["pages"] == [1, 2]
        check_clean_page(rec)
    finally:
        ctx.close()


@register_test("T2-F2-6", 2, "F2", ("sardegna", "petit-prince"), True, "Tutta Pagina non-fullscreen & landscape phone (667x375/844x390/800x501/844x510/844x541/860x600/844x601) + mid-size (860/880/960x700) + Kids NF minHeight 520px + Adult Layer-1 (zaino, sardegna, scheletri up to 1280x768 + 390x844 + #kidsReadingLaunchBar) + #topbarRight <=960px wrap without overlap or clipping")
def t2_f2_6(env: RunnerEnv) -> None:
    env.require_m1_m3(env.has_petit_prince_assets(), "books/petit-prince missing")
    measure_fs_js = """() => {
        const els = ['#kidsFullscreenBooksLink', '#kidsBookTitleRibbon', '#kidsBookmarkResumePill', '#openBookSpread', '#kidsNotebookFloatingBar'];
        const rects = els.map(s => [s, document.querySelector(s)])
            .filter(([, el]) => el && !el.hidden && getComputedStyle(el).display !== 'none')
            .map(([s, el]) => ({ s, r: el.getBoundingClientRect() }))
            .filter(x => x.r.width > 0 && x.r.height > 0);
        let maxOv = 0;
        for (let i = 0; i < rects.length; i++) {
            for (let j = i + 1; j < rects.length; j++) {
                const a = rects[i].r, b = rects[j].r;
                const ox = Math.max(0, Math.min(a.right, b.right) - Math.max(a.left, b.left));
                const oy = Math.max(0, Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top));
                maxOv = Math.max(maxOv, ox * oy);
            }
        }
        const br = document.getElementById('openBookSpread').getBoundingClientRect();
        return {
            single: document.getElementById('openBookSpread').classList.contains('kids-single-page-mode'),
            maxOv, bw: br.width, bh: br.height,
            docOX: document.documentElement.scrollWidth - window.innerWidth,
            uppercase: Boolean(document.querySelector('#openBookSpread .kids-sentence-box')?.classList.contains('uppercase-mode')),
            fits: (window.__kidsTextFitMetrics ? window.__kidsTextFitMetrics() : []),
        };
    }"""
    for vw, vh in ((375, 667), (390, 844), (667, 375), (844, 390), (800, 501), (844, 510), (844, 541), (860, 600), (844, 601), (768, 1024), (860, 700), (880, 700), (960, 700), (1280, 720), (1440, 900)):
        ctx, page, rec = env.new_session(viewport={"width": vw, "height": vh})
        try:
            env.goto_reader(page, "?book=petit-prince&mode=emma&lang=fr&page=1")
            fs = page.evaluate(measure_fs_js)
            if vw > vh and vh <= 600:
                assert not fs["single"], f"{vw}x{vh} landscape should not force single-page mode: {fs}"
                assert fs["bw"] >= 300 and fs["bh"] >= 200, f"{vw}x{vh} FS too small: {fs}"
                if vh > 500:
                    assert fs["bh"] >= 400, f"{vw}x{vh} short landscape FS collapsed (breakpoint cliff): {fs}"
            elif vw >= 860:
                assert fs["bw"] >= 700 and fs["bh"] >= 450, f"{vw}x{vh} FS too small: {fs}"
            else:
                assert fs["bw"] >= 240 and fs["bh"] >= 320, f"{vw}x{vh} FS too small: {fs}"
            assert fs["maxOv"] == 0, f"{vw}x{vh} FS overlap: {fs}"
            assert fs["docOX"] <= 1, f"{vw}x{vh} FS horizontal overflow: {fs}"
            assert fs["fits"] and all(m["fits"] and m["overflowY"] <= 2 and m["overflowX"] <= 2 for m in fs["fits"]), f"{vw}x{vh} FS fit fail: {fs}"

            measure_nf_js = """() => {
                const els = ['#kidsReadingLaunchBar', '#kidsBookTitleRibbon', '#kidsBookmarkResumePill', '#openBookSpread', '#kidsNotebookFloatingBar'];
                const rects = els.map(s => [s, document.querySelector(s)])
                    .filter(([, el]) => el && !el.hidden && getComputedStyle(el).display !== 'none')
                    .map(([s, el]) => ({ s, r: el.getBoundingClientRect() }))
                    .filter(x => x.r.width > 0 && x.r.height > 0);
                let maxOv = 0;
                for (let i = 0; i < rects.length; i++) {
                    for (let j = i + 1; j < rects.length; j++) {
                        const a = rects[i].r, b = rects[j].r;
                        const ox = Math.max(0, Math.min(a.right, b.right) - Math.max(a.left, b.left));
                        const oy = Math.max(0, Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top));
                        maxOv = Math.max(maxOv, ox * oy);
                    }
                }
                const br = document.getElementById('openBookSpread').getBoundingClientRect();
                const stage = document.querySelector('#bookViewport .open-book-stage');
                return {
                    maxOv, bw: br.width, bh: br.height,
                    stageMinH: stage ? getComputedStyle(stage).minHeight : '',
                    docOX: document.documentElement.scrollWidth - window.innerWidth,
                    uppercase: Boolean(document.querySelector('#openBookSpread .kids-sentence-box')?.classList.contains('uppercase-mode')),
                    fits: (window.__kidsTextFitMetrics ? window.__kidsTextFitMetrics() : []),
                };
            }"""

            page.locator("#kidsNotebookFloatingBar button[title='Tutta Pagina']").click()
            page.wait_for_timeout(150)
            assert not is_kids_fullscreen(page)
            nf = page.evaluate(measure_nf_js)
            assert nf["maxOv"] == 0, f"{vw}x{vh} non-fullscreen overlap: {nf}"
            if vw >= 769 and vh >= 501:
                assert nf["stageMinH"] == "520px", f"{vw}x{vh} Kids NF stage minHeight altered: {nf}"
            if vh <= 500:
                assert nf["bw"] >= 300 and nf["bh"] >= 200, f"{vw}x{vh} NF collapsed book: {nf}"
            elif vw >= 860:
                assert nf["bw"] >= 760 and nf["bh"] >= 500, f"{vw}x{vh} NF collapsed book: {nf}"
            else:
                assert nf["bw"] >= 240 and nf["bh"] >= 320, f"{vw}x{vh} NF collapsed book: {nf}"
            assert nf["fits"] and all(m["fits"] and m["overflowY"] <= 2 and m["overflowX"] <= 2 for m in nf["fits"]), f"{vw}x{vh} NF fit fail: {nf}"
            assert nf["docOX"] <= 1, f"{vw}x{vh} horizontal overflow: {nf}"

            if vw > vh and vh <= 601:
                page.locator("#kidsNotebookFloatingBar button[title*='Maiuscolo']").first.click()
                page.wait_for_timeout(150)
                nf_uc_p1 = page.evaluate(measure_nf_js)
                assert nf_uc_p1["uppercase"], f"{vw}x{vh} P1 expected uppercase-mode ON: {nf_uc_p1}"
                assert nf_uc_p1["maxOv"] == 0, f"{vw}x{vh} P1 uppercase NF overlap: {nf_uc_p1}"
                assert nf_uc_p1["docOX"] <= 1, f"{vw}x{vh} P1 uppercase NF horizontal overflow: {nf_uc_p1}"
                assert nf_uc_p1["fits"] and all(m["fits"] and m["overflowY"] <= 2 and m["overflowX"] <= 2 for m in nf_uc_p1["fits"]), f"{vw}x{vh} P1 uppercase NF fit fail: {nf_uc_p1}"

                env.goto_reader(page, "?book=petit-prince&mode=emma&lang=fr&page=9")
                assert get_active_book_info(page)["pages"] == [9, 10]
                page.locator("#kidsNotebookFloatingBar button[title='Tutta Pagina']").click()
                page.wait_for_timeout(150)
                assert not is_kids_fullscreen(page)
                if not page.evaluate("() => Boolean(document.querySelector('#openBookSpread .kids-sentence-box')?.classList.contains('uppercase-mode'))"):
                    page.locator("#kidsNotebookFloatingBar button[title*='Maiuscolo']").first.click()
                    page.wait_for_timeout(150)
                nf_uc_p9 = page.evaluate(measure_nf_js)
                assert nf_uc_p9["uppercase"], f"{vw}x{vh} P9 expected uppercase-mode ON: {nf_uc_p9}"
                assert nf_uc_p9["maxOv"] == 0, f"{vw}x{vh} P9 uppercase NF overlap: {nf_uc_p9}"
                assert nf_uc_p9["docOX"] <= 1, f"{vw}x{vh} P9 uppercase NF horizontal overflow: {nf_uc_p9}"
                assert nf_uc_p9["fits"] and all(m["fits"] and m["overflowY"] <= 2 and m["overflowX"] <= 2 for m in nf_uc_p9["fits"]), f"{vw}x{vh} P9 uppercase NF fit fail: {nf_uc_p9}"

            page.locator("#kidsNotebookFloatingBar button[title='Tutta Pagina']").click()
            page.wait_for_timeout(140)
            assert is_kids_fullscreen(page)
            if vw > vh and vh <= 601:
                fs_uc = page.evaluate(measure_fs_js)
                assert fs_uc["maxOv"] == 0, f"{vw}x{vh} uppercase FS overlap: {fs_uc}"
                assert fs_uc["docOX"] <= 1, f"{vw}x{vh} uppercase FS horizontal overflow: {fs_uc}"
                assert fs_uc["fits"] and all(m["fits"] and m["overflowY"] <= 2 and m["overflowX"] <= 2 for m in fs_uc["fits"]), f"{vw}x{vh} uppercase FS fit fail: {fs_uc}"
            check_clean_page(rec)
        finally:
            ctx.close()

    # #topbarRight wrap check on <= 960px viewports (?tab=indice)
    for vw, vh in ((375, 667), (412, 915), (768, 1024), (900, 700), (960, 700)):
        ctx, page, rec = env.new_session(viewport={"width": vw, "height": vh})
        try:
            env.goto_reader(page, "?tab=indice", wait_selector="#indexView:visible")
            tb = page.evaluate("""() => {
                const tr = document.getElementById('topbarRight');
                const off = Array.from(tr.children).filter(c => c.getBoundingClientRect().right > window.innerWidth + 1)
                    .map(c => ({ id: c.id || c.className, right: c.getBoundingClientRect().right }));
                return { off, bodySW: document.body.scrollWidth, winW: window.innerWidth };
            }""")
            assert not tb["off"] and tb["bodySW"] <= tb["winW"] + 1, f"#topbarRight clipped on {vw}x{vh}: {tb}"
            check_clean_page(rec)
        finally:
            ctx.close()

    # Adult Layer-1 prose, overflow & #kidsReadingLaunchBar regression check across stories & viewports
    adult_layer1_cases = (
        ("storia-dello-zaino-del-drago-e-dei-puffins", False),
        ("storia-sardegna-cala-gonone-arbatax-famiglia", True),
        ("storia-scheletri-zombie-te", False),
    )
    adult_viewports = (
        (800, 501), (844, 510), (1280, 540), (800, 580),
        (901, 711), (960, 711), (1280, 720), (1280, 768), (390, 844),
    )
    for story_slug, expect_launch_bar in adult_layer1_cases:
        ctx, page, rec = env.new_session(viewport={"width": 1280, "height": 720})
        try:
            env.goto_reader(page, f"?story={story_slug}", wait_selector="#openBookSpread")
            assert not is_kids_fullscreen(page), f"{story_slug} entered fullscreen unexpectedly"
            for vw, vh in adult_viewports:
                page.set_viewport_size({"width": vw, "height": vh})
                page.evaluate("() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))")
                layer1 = page.evaluate("""() => {
                    const ov = (a, b) => {
                        if (!a || !b) return 0;
                        const ox = Math.max(0, Math.min(a.right, b.right) - Math.max(a.left, b.left));
                        const oy = Math.max(0, Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top));
                        return ox * oy;
                    };
                    const hdr = document.querySelector('header.topbar')?.getBoundingClientRect();
                    const lb = document.getElementById('kidsReadingLaunchBar');
                    const lbr = lb ? lb.getBoundingClientRect() : null;
                    const lbVis = Boolean(lb && !lb.hidden && getComputedStyle(lb).display !== 'none' && lbr && lbr.width > 0 && lbr.height > 0);
                    const book = document.getElementById('openBookSpread')?.getBoundingClientRect();
                    const ftr = document.querySelector('footer.carlessian-footer')?.getBoundingClientRect();
                    const prose = document.querySelector('.is-primary-page .book-prose, #bookPageLeft .book-prose');
                    const pr = prose ? prose.getBoundingClientRect() : null;
                    const nav = document.querySelector('.is-primary-page .book-nav-footer, #bookPageLeft .book-nav-footer')?.getBoundingClientRect();
                    return {
                        proseH: pr ? pr.height : 0,
                        proseScrollH: prose ? prose.scrollHeight : 0,
                        docOX: document.documentElement.scrollWidth - window.innerWidth,
                        lbVis,
                        lbH: lbr ? lbr.height : 0,
                        lbClipped: lbVis ? (lbr.left < -1 || lbr.right > window.innerWidth + 1) : false,
                        lbOvHdr: lbVis ? ov(lbr, hdr) : 0,
                        lbOvBook: lbVis ? ov(lbr, book) : 0,
                        bookOvFtr: ov(book, ftr),
                        proseOvNav: ov(pr, nav),
                    };
                }""")
                assert layer1["proseH"] >= 100, f"{story_slug} Adult Layer-1 prose collapsed at {vw}x{vh}: {layer1}"
                assert layer1["docOX"] <= 1, f"{story_slug} Adult Layer-1 horizontal overflow at {vw}x{vh}: {layer1}"
                assert layer1["bookOvFtr"] == 0 and layer1["proseOvNav"] == 0, f"{story_slug} Adult Layer-1 overlap at {vw}x{vh}: {layer1}"
                if expect_launch_bar:
                    assert layer1["lbVis"], f"{story_slug} expected #kidsReadingLaunchBar visible at {vw}x{vh}: {layer1}"
                    assert not layer1["lbClipped"] and layer1["lbOvHdr"] == 0 and layer1["lbOvBook"] == 0, (
                        f"{story_slug} #kidsReadingLaunchBar overlap/clip at {vw}x{vh}: {layer1}"
                    )
                else:
                    assert not layer1["lbVis"], f"{story_slug} unexpected #kidsReadingLaunchBar at {vw}x{vh}: {layer1}"
            check_clean_page(rec)
        finally:
            ctx.close()


# --- F3 Boundaries (5) ---
@register_test("T2-F3-1", 2, "F3", ("sardegna", "petit-prince"), True, "Corrupted JSON in kos_kids_bookmarks_v1 does not crash app boot")
def t2_f3_1(env: RunnerEnv) -> None:
    if env.baseline:
        raise SkipTest("pre-M1/M3 baseline: Bookmark storage not yet implemented")
    ctx, page, rec = env.new_session()
    try:
        ctx.add_init_script("localStorage.setItem('kos_kids_bookmarks_v1', '{broken-json!!');")
        env.goto_reader(page, "?book=sardegna")
        check_clean_page(rec)
        assert get_active_book_info(page)["pages"] == [1, 2]
    finally:
        ctx.close()


@register_test("T2-F3-2", 2, "F3", ("petit-prince",), True, "Bookmark saved at P24 restores cleanly to P23-P24 spread")
def t2_f3_2(env: RunnerEnv) -> None:
    env.require_m1_m3(env.has_petit_prince_assets(), "books/petit-prince missing")
    ctx, page, rec = env.new_session()
    try:
        env.goto_reader(page, "?book=petit-prince&page=24")
        click_bookmark_button(page, "save")
        env.goto_reader(page, "?book=petit-prince&page=1")
        click_bookmark_button(page, "resume")
        assert get_active_book_info(page)["pages"] == [23, 24]
        check_clean_page(rec)
    finally:
        ctx.close()


@register_test("T2-F3-3", 2, "F3", ("sardegna", "petit-prince"), True, "Bookmark with parallel=true & trLang=en restores parallel mode and trLang")
def t2_f3_3(env: RunnerEnv) -> None:
    if env.baseline:
        raise SkipTest("pre-M1/M3 baseline: Bookmark UI not yet implemented")
    ctx, page, rec = env.new_session()
    try:
        env.goto_reader(page, "?book=sardegna&lang=fr&parallel=1&page=3")
        switch_translation_lang(page, "en")
        click_bookmark_button(page, "save")
        env.goto_reader(page, "?book=sardegna&lang=it&page=1")
        click_bookmark_button(page, "resume")
        info = get_active_book_info(page)
        assert info["parallel"] is True and info["trLang"] == "en" and info["pages"] == [3, 3], info
        check_clean_page(rec)
    finally:
        ctx.close()


@register_test("T2-F3-4", 2, "F3", ("sardegna", "petit-prince"), True, "Bookmark saved on P1 restores P1-P2 cleanly")
def t2_f3_4(env: RunnerEnv) -> None:
    if env.baseline:
        raise SkipTest("pre-M1/M3 baseline: Bookmark UI not yet implemented")
    ctx, page, rec = env.new_session()
    try:
        env.goto_reader(page, "?book=sardegna&page=1")
        click_bookmark_button(page, "save")
        env.goto_reader(page, "?book=sardegna&page=9")
        click_bookmark_button(page, "resume")
        assert get_active_book_info(page)["pages"] == [1, 2]
        check_clean_page(rec)
    finally:
        ctx.close()


@register_test("T2-F3-5", 2, "F3", ("sardegna", "petit-prince"), True, "Bookmark survives switching to Indice and returning/reloading Studio")
def t2_f3_5(env: RunnerEnv) -> None:
    if env.baseline:
        raise SkipTest("pre-M1/M3 baseline: Bookmark UI not yet implemented")
    ctx, page, rec = env.new_session()
    try:
        env.goto_reader(page, "?book=sardegna&page=7")
        click_bookmark_button(page, "save")
        page.locator("#kidsNotebookFloatingBar button.exit-btn").click()
        page.wait_for_timeout(120)
        page.locator("#tabsStrip button[data-tab='indice']").click()
        page.locator("#indexView").wait_for(state="visible", timeout=5000)
        # Reload ?tab=studio so spread position resets to P1-P2 (not already on P7-P8)
        env.goto_reader(page, "?tab=studio")
        assert get_active_book_info(page)["pages"] != [7, 8], "Expected reset away from [7, 8] before bookmark resume"
        click_bookmark_button(page, "resume")
        assert get_active_book_info(page)["pages"] == [7, 8]
        check_clean_page(rec)
    finally:
        ctx.close()


@register_test("T2-F3-6", 2, "F3", ("sardegna", "petit-prince"), False, "Escape closes #kidsSettingsPopover or #antolinQuizDialog first without navigating away; next Escape saves & navigates to /books/", requires_m5=True)
def t2_f3_6(env: RunnerEnv) -> None:
    env.require_m5(env.has_bookshelf(), "books/index.html and Escape bookmark-save/exit (M5) missing")
    targets = active_book_targets(env)
    alias, sid = targets[0]
    ctx, page, rec = env.new_session()
    try:
        env.goto_reader(page, f"?book={alias}&page=5&mode=seby&lang=it")
        assert is_kids_fullscreen(page)

        # 1. With #kidsSettingsPopover open, Escape closes popover ONLY (stays on index.html in fullscreen)
        ensure_settings_popover(page, True)
        assert page.locator("#kidsSettingsPopover").is_visible()
        page.keyboard.press("Escape")
        page.wait_for_timeout(160)
        assert not page.locator("#kidsSettingsPopover").is_visible(), "Expected Escape to dismiss #kidsSettingsPopover first"
        assert "/books" not in page.url.split("?", 1)[0], f"Expected Escape dismissing popover NOT to navigate to /books/: {page.url}"
        assert is_kids_fullscreen(page), "Expected Escape dismissing settings popover NOT to exit fullscreen book mode"

        # 2. With #antolinQuizDialog open, Escape closes quiz dialog ONLY (stays on index.html in fullscreen)
        page.locator("#kidsNotebookFloatingBar .quiz-pill").click()
        page.wait_for_selector("#antolinQuizDialog[open]", timeout=4000)
        page.keyboard.press("Escape")
        page.wait_for_timeout(160)
        assert not page.locator("#antolinQuizDialog").evaluate("d => d.open"), "Expected Escape to close #antolinQuizDialog first"
        assert "/books" not in page.url.split("?", 1)[0], f"Expected Escape dismissing quiz dialog NOT to navigate to /books/: {page.url}"
        assert is_kids_fullscreen(page), "Expected Escape closing Antolin quiz dialog NOT to exit fullscreen book mode"

        # 3. With no overlay open, Escape saves current page to bookmark and navigates cleanly to /books/
        page.keyboard.press("Escape")
        page.wait_for_url(re.compile(r"/books/?(\?.*)?$"), timeout=5000)
        page.wait_for_load_state("domcontentloaded")
        assert page.url.split("?", 1)[0].endswith("/books/"), f"Expected second Escape (no overlay open) to navigate to /books/, got {page.url}"
        bm = get_bookmarks_storage(page)
        assert isinstance(bm, dict) and int(bm.get(sid, {}).get("page", 0)) in (5, 6), bm
        check_clean_page(rec)
    finally:
        ctx.close()


# --- F4 Boundaries (5) ---
@register_test("T2-F4-1", 2, "F4", ("sardegna", "petit-prince"), False, "Emma tier on tighter patch-top even pages stays <=2px overflow and >=0.42 fillRatio")
def t2_f4_1(env: RunnerEnv) -> None:
    targets = active_book_targets(env)
    ctx, page, rec = env.new_session()
    try:
        for alias, sid in targets:
            total = 26 if sid == PETIT_PRINCE_ID else 16
            for lang in ("fr", "it", "de"):
                env.goto_reader(page, open_book_query(env, alias, f"&mode=emma&lang={lang}&page=1"))
                for s_idx in range(total // 2):
                    if s_idx > 0:
                        page.locator("#bookPageRight .kids-edge-nav-arrow.is-right-arrow").click()
                        page.wait_for_timeout(90)
                    page.evaluate("() => window.fitKidsTextToPatch && fitKidsTextToPatch()")
                    metrics = page.evaluate("() => window.__kidsTextFitMetrics()")
                    even_m = [m for m in metrics if m["page"] % 2 == 0]
                    assert_fit_metrics(even_m, f"T2-F4-1 {alias} {lang}")
            check_clean_page(rec, allow_baseline_puffin_error=env.baseline)
            rec.clear()
    finally:
        ctx.close()


@register_test("T2-F4-2", 2, "F4", ("sardegna", "petit-prince"), False, "Uppercase mode (a/A) across seby/ale/emma stays <=2px overflow")
def t2_f4_2(env: RunnerEnv) -> None:
    targets = active_book_targets(env)
    ctx, page, rec = env.new_session()
    try:
        for alias, _ in targets:
            env.goto_reader(page, open_book_query(env, alias, "&mode=seby&lang=de"))
            set_uppercase_mode(page, True)
            for tier in ("seby", "ale", "emma"):
                set_tier(page, tier)
                page.evaluate("() => window.fitKidsTextToPatch && fitKidsTextToPatch()")
                metrics = page.evaluate("() => window.__kidsTextFitMetrics()")
                assert all(m["uppercase"] for m in metrics), metrics
                assert_fit_metrics(metrics, f"T2-F4-2 {alias}/{tier}")
            check_clean_page(rec, allow_baseline_puffin_error=env.baseline)
    finally:
        ctx.close()


@register_test("T2-F4-3", 2, "F4", ("sardegna", "petit-prince"), False, "Mobile viewport (412x915) renders Kids spread cleanly without JS errors or horizontal overflow")
def t2_f4_3(env: RunnerEnv) -> None:
    targets = active_book_targets(env)
    ctx, page, rec = env.new_session(viewport={"width": 412, "height": 915})
    try:
        for alias, _ in targets:
            env.goto_reader(page, open_book_query(env, alias, "&mode=ale&lang=it"))
            check_clean_page(rec, allow_baseline_puffin_error=env.baseline)
            ov = page.evaluate("() => document.documentElement.scrollWidth - window.innerWidth")
            assert ov <= 4, f"{alias} 412x915 horizontal overflow: {ov}px"
            assert page.locator("#kidsNotebookFloatingBar").is_visible()
    finally:
        ctx.close()


@register_test("T2-F4-4", 2, "F4", ("sardegna", "petit-prince"), False, "Switching tiers on P13-P14 preserves exact spread position (does not jump to P1)")
def t2_f4_4(env: RunnerEnv) -> None:
    targets = active_book_targets(env)
    ctx, page, rec = env.new_session()
    try:
        for alias, _ in targets:
            env.goto_reader(page, open_book_query(env, alias, "&mode=seby&page=13"))
            assert get_active_book_info(page)["pages"] == [13, 14]
            set_tier(page, "ale")
            assert get_active_book_info(page)["pages"] == [13, 14]
            set_tier(page, "emma")
            assert get_active_book_info(page)["pages"] == [13, 14]
            check_clean_page(rec, allow_baseline_puffin_error=env.baseline)
    finally:
        ctx.close()


@register_test("T2-F4-5", 2, "F4", ("sardegna", "petit-prince"), False, "Seby min-fill check: short plates scale font upward (<=40px) and keep fillRatio >= 0.42")
def t2_f4_5(env: RunnerEnv) -> None:
    targets = active_book_targets(env)
    ctx, page, rec = env.new_session()
    try:
        for alias, _ in targets:
            env.goto_reader(page, open_book_query(env, alias, "&mode=seby&lang=de"))
            page.evaluate("() => window.fitKidsTextToPatch && fitKidsTextToPatch()")
            metrics = page.evaluate("() => window.__kidsTextFitMetrics()")
            assert_fit_metrics(metrics, f"T2-F4-5 {alias}")
            assert all(10.5 <= m["fontSizePx"] <= 40.5 for m in metrics), metrics
            check_clean_page(rec, allow_baseline_puffin_error=env.baseline)
    finally:
        ctx.close()


@register_test("T2-F4-6", 2, "F4", ("petit-prince",), True, "Fullscreen top-edge controls, seeded bookmark pill & settings popover never overlap across mobile/landscape/tablet/desktop")
def t2_f4_6(env: RunnerEnv) -> None:
    env.require_m1_m3(env.has_petit_prince_assets(), "books/petit-prince missing")
    bm = {PETIT_PRINCE_ID: {"page": 7, "mode": "ale", "lang": "fr", "trLang": "en", "parallel": False, "savedAt": "2026-11-24T00:00:00Z"}}
    for vw, vh in ((375, 667), (390, 844), (667, 375), (844, 390), (768, 1024), (960, 700), (1280, 720)):
        ctx, page, rec = env.new_session(viewport={"width": vw, "height": vh})
        try:
            ctx.add_init_script(f"localStorage.setItem('kos_kids_bookmarks_v1', {json.dumps(json.dumps(bm))});")
            env.goto_reader(page, "?book=petit-prince&mode=ale&lang=fr&page=1")
            ensure_settings_popover(page, True)
            res = page.evaluate("""() => {
                const ids = ['kidsFullscreenBooksLink', 'kidsBookTitleRibbon', 'kidsBookmarkResumePill', 'openBookSpread', 'kidsNotebookFloatingBar'];
                const rects = ids.map(id => [id, document.getElementById(id)])
                    .filter(([, el]) => el && !el.hidden && getComputedStyle(el).display !== 'none')
                    .map(([id, el]) => ({ id, r: el.getBoundingClientRect() }))
                    .filter(x => x.r.width > 0 && x.r.height > 0);
                const hits = [];
                for (let i = 0; i < rects.length; i++) {
                    for (let j = i + 1; j < rects.length; j++) {
                        const a = rects[i].r, b = rects[j].r;
                        const ox = Math.max(0, Math.min(a.right, b.right) - Math.max(a.left, b.left));
                        const oy = Math.max(0, Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top));
                        if (ox * oy > 0.5) hits.push([rects[i].id, rects[j].id, ox * oy]);
                    }
                }
                const pop = document.getElementById('kidsSettingsPopover').getBoundingClientRect();
                return { hits, popClip: pop.top < 0 || pop.left < 0 || pop.right > window.innerWidth + 1 || pop.bottom > window.innerHeight + 1 };
            }""")
            assert not res["hits"] and not res["popClip"], f"{vw}x{vh}: {res}"
            check_clean_page(rec)
        finally:
            ctx.close()


# --- F5 Boundaries (5) ---
def _check_self_pair_guard(env: RunnerEnv, lang: str) -> None:
    targets = active_book_targets(env)
    ctx, page, rec = env.new_session()
    try:
        for alias, _ in targets:
            env.goto_reader(page, open_book_query(env, alias, f"&lang={lang}&parallel=1"))
            switch_translation_lang(page, lang)
            info = get_active_book_info(page)
            expected_right = "EN" if lang != "en" else "IT"
            assert info["badges"] == [f"1 · {lang.upper()}", f"1 · {expected_right}"], (
                f"{alias} self-pair guard failed: {info['badges']}"
            )
            check_clean_page(rec, allow_baseline_puffin_error=env.baseline)
    finally:
        ctx.close()


@register_test("T2-F5-1", 2, "F5", ("sardegna", "petit-prince"), False, "Self-pair guard: it + trLang='it' falls back to IT ↔ EN")
def t2_f5_1(env: RunnerEnv) -> None:
    _check_self_pair_guard(env, "it")


@register_test("T2-F5-2", 2, "F5", ("sardegna", "petit-prince"), False, "Self-pair guard: fr + trLang='fr' falls back to FR ↔ EN")
def t2_f5_2(env: RunnerEnv) -> None:
    _check_self_pair_guard(env, "fr")


@register_test("T2-F5-3", 2, "F5", ("sardegna", "petit-prince"), False, "Self-pair guard: de + trLang='de' falls back to DE ↔ EN")
def t2_f5_3(env: RunnerEnv) -> None:
    _check_self_pair_guard(env, "de")


@register_test("T2-F5-4", 2, "F5", ("sardegna", "petit-prince"), False, "Accents/umlauts/ligatures render cleanly without U+FFFD mojibake across FR/IT/DE")
def t2_f5_4(env: RunnerEnv) -> None:
    for _, sid in active_book_targets(env):
        kb = load_book_json(sid)
        joined = []
        for pg in kb["pages"]:
            if pg.get("is_frontispiece"):
                continue
            for lang in ("fr", "it", "de"):
                for lvl in ("seby", "ale"):
                    joined.append(pg["levels"][lvl][lang]["text"])
                if "emma" in pg["levels"] and lang in pg["levels"]["emma"]:
                    joined.append(pg["levels"]["emma"][lang]["text"])
        blob = " ".join(joined)
        assert "\ufffd" not in blob, f"{sid} contains replacement char U+FFFD"
        for ch in ("é", "è", "à", "ü", "ö", "ä"):
            assert ch in blob.lower(), f"{sid} missing expected diacritic '{ch}'"


@register_test("T2-F5-5", 2, "F5", ("sardegna", "petit-prince"), False, "Switching learning language stops/resets active karaoke audio cleanly")
def t2_f5_5(env: RunnerEnv) -> None:
    targets = active_book_targets(env)
    ctx, page, rec = env.new_session()
    try:
        env.goto_reader(page, open_book_query(env, targets[0][0], "&lang=fr"))
        page.locator("#kidsNotebookFloatingBar .listen-pill").first.click()
        page.wait_for_timeout(150)
        switch_book_lang(page, "de")
        state = page.evaluate(
            "() => ({ paused: document.getElementById('kidsStaticAudio')?.paused !== false, activeToks: document.querySelectorAll('.kw-token.active').length })"
        )
        assert state["paused"] and state["activeToks"] == 0, state
        check_clean_page(rec, allow_baseline_puffin_error=env.baseline)
    finally:
        ctx.close()


# --- F6 Boundaries (5) ---
@register_test("T2-F6-1", 2, "F6", ("sardegna", "petit-prince"), False, "Left arrow on P1 is disabled in both normal and parallel modes")
def t2_f6_1(env: RunnerEnv) -> None:
    targets = active_book_targets(env)
    ctx, page, rec = env.new_session()
    try:
        for alias, _ in targets:
            env.goto_reader(page, open_book_query(env, alias))
            assert page.locator("#bookPageLeft .kids-edge-nav-arrow.is-left-arrow").is_disabled()
            set_parallel_mode(page, True)
            assert page.locator("#bookPageLeft .kids-edge-nav-arrow.is-left-arrow").is_disabled()
            check_clean_page(rec, allow_baseline_puffin_error=env.baseline)
    finally:
        ctx.close()


@register_test("T2-F6-2", 2, "F6", ("sardegna", "petit-prince"), False, "Parallel right arrow: enabled on P(N-1) and disabled on last page P(N)")
def t2_f6_2(env: RunnerEnv) -> None:
    targets = active_book_targets(env)
    ctx, page, rec = env.new_session()
    try:
        for alias, sid in targets:
            last_p = 26 if sid == PETIT_PRINCE_ID else 16
            env.goto_reader(page, open_book_query(env, alias, f"&parallel=1&page={last_p - 1}"))
            right_arrow = page.locator("#bookPageRight .kids-edge-nav-arrow.is-right-arrow")
            assert not right_arrow.is_disabled(), f"{alias} P{last_p - 1} right arrow should be enabled in parallel mode"
            right_arrow.click()
            page.wait_for_timeout(120)
            assert get_active_book_info(page)["pages"] == [last_p, last_p]
            assert page.locator("#bookPageRight .kids-edge-nav-arrow.is-right-arrow").is_disabled()
            check_clean_page(rec, allow_baseline_puffin_error=env.baseline)
    finally:
        ctx.close()


@register_test("T2-F6-3", 2, "F6", ("sardegna", "petit-prince"), False, "Turning P1 -> P2 in parallel mode switches both leaves from .patch-bottom to .patch-top")
def t2_f6_3(env: RunnerEnv) -> None:
    targets = active_book_targets(env)
    ctx, page, rec = env.new_session()
    try:
        env.goto_reader(page, open_book_query(env, targets[0][0], "&parallel=1"))
        assert page.locator("#openBookSpread .kids-watercolor-leaf.patch-bottom").count() == 2
        page.locator("#bookPageRight .kids-edge-nav-arrow.is-right-arrow").click()
        page.wait_for_timeout(120)
        assert page.locator("#openBookSpread .kids-watercolor-leaf.patch-top").count() == 2
        check_clean_page(rec, allow_baseline_puffin_error=env.baseline)
    finally:
        ctx.close()


@register_test("T2-F6-4", 2, "F6", ("sardegna", "petit-prince"), False, "Toggling Parallel Mode OFF from P5 snaps spread cleanly back to P5-P6")
def t2_f6_4(env: RunnerEnv) -> None:
    targets = active_book_targets(env)
    ctx, page, rec = env.new_session()
    try:
        env.goto_reader(page, open_book_query(env, targets[0][0], "&parallel=1&page=5"))
        assert get_active_book_info(page)["pages"] == [5, 5]
        set_parallel_mode(page, False)
        assert get_active_book_info(page)["pages"] == [5, 6]
        check_clean_page(rec, allow_baseline_puffin_error=env.baseline)
    finally:
        ctx.close()


@register_test("T2-F6-5", 2, "F6", ("sardegna", "petit-prince"), False, "en_gloss popover resolves B2/C1 vocabulary in FR, IT, DE with trLang=en")
def t2_f6_5(env: RunnerEnv) -> None:
    targets = active_book_targets(env)
    ctx, page, rec = env.new_session()
    try:
        for alias, _ in targets:
            for lang in ("fr", "it", "de"):
                env.goto_reader(page, open_book_query(env, alias, f"&mode=emma&lang={lang}"))
                glosses = page.evaluate(
                    "() => Array.from(document.querySelectorAll('#openBookSpread .kw-token.kw-has-gloss .kw-gloss-popover')).map(e => e.textContent.trim()).filter(Boolean)"
                )
                assert len(glosses) >= 1, f"{alias} emma/{lang}: expected at least 1 en_gloss popover on spread 1"
            check_clean_page(rec, allow_baseline_puffin_error=env.baseline)
    finally:
        ctx.close()


# --- F7 Boundaries (5) ---
@register_test("T2-F7-1", 2, "F7", ("sardegna", "petit-prince"), False, "setKidsSpeedStep(-1) clamps to 0 and setKidsSpeedStep(99) clamps to 4")
def t2_f7_1(env: RunnerEnv) -> None:
    ctx, page, rec = env.new_session()
    try:
        env.goto_reader(page, open_book_query(env, "sardegna"))
        page.evaluate("() => setKidsSpeedStep(-1)")
        assert page.evaluate("() => localStorage.getItem('kos_kids_speed_step')") == "0"
        page.evaluate("() => setKidsSpeedStep(99)")
        assert page.evaluate("() => localStorage.getItem('kos_kids_speed_step')") == "4"
        check_clean_page(rec, allow_baseline_puffin_error=env.baseline)
    finally:
        ctx.close()


@register_test("T2-F7-2", 2, "F7", ("sardegna", "petit-prince"), False, "Non-numeric localStorage['kos_kids_speed_step']='abc' falls back to step 2 (1.0x)")
def t2_f7_2(env: RunnerEnv) -> None:
    ctx, page, rec = env.new_session()
    try:
        ctx.add_init_script("localStorage.setItem('kos_kids_speed_step', 'abc');")
        env.goto_reader(page, open_book_query(env, "sardegna"))
        ensure_settings_popover(page, True)
        bg = page.locator("#kidsSettingsPopover button[onclick='setKidsSpeedStep(2)']").evaluate("el => el.style.background")
        assert "rgb(245, 158, 11)" in bg or "#f59e0b" in bg.lower(), f"Expected step 2 active fallback, got {bg}"
        check_clean_page(rec, allow_baseline_puffin_error=env.baseline)
    finally:
        ctx.close()


@register_test("T2-F7-3", 2, "F7", ("sardegna", "petit-prince"), False, "Browser TTS fallback clamps utterance.rate within [0.55, 1.6] at steps 0 and 4")
def t2_f7_3(env: RunnerEnv) -> None:
    ctx, page, rec = env.new_session()
    try:
        env.goto_reader(page, open_book_query(env, "sardegna", "&lang=fr&parallel=1"))
        for step in (0, 4):
            ensure_settings_popover(page, True)
            page.locator(f"#kidsSettingsPopover button[onclick='setKidsSpeedStep({step})']").click()
            ensure_settings_popover(page, False)
            page.evaluate("() => { window.__kosTtsCalls = []; }")
            page.locator("#kidsNotebookFloatingBar .listen-pill").nth(1).click()
            page.wait_for_timeout(120)
            calls = page.evaluate("() => window.__kosTtsCalls")
            assert calls and 0.55 <= calls[-1]["rate"] <= 1.6, calls
        check_clean_page(rec, allow_baseline_puffin_error=env.baseline)
    finally:
        ctx.close()


@register_test("T2-F7-4", 2, "F7", ("sardegna",), False, "Clicking Play -> Pause -> Play on same .listen-pill toggles cleanly and preserves playbackRate")
def t2_f7_4(env: RunnerEnv) -> None:
    ctx, page, rec = env.new_session()
    try:
        env.goto_reader(page, open_book_query(env, "sardegna", "&mode=seby&lang=it"))
        ensure_settings_popover(page, True)
        page.locator("#kidsSettingsPopover button[onclick='setKidsSpeedStep(1)']").click()
        ensure_settings_popover(page, False)
        btn = page.locator("#kidsNotebookFloatingBar .listen-pill").first
        btn.click()
        page.wait_for_timeout(180)
        assert page.evaluate("() => !document.getElementById('kidsStaticAudio').paused")
        btn.click()
        page.wait_for_timeout(80)
        assert page.evaluate("() => document.getElementById('kidsStaticAudio').paused")
        btn.click()
        page.wait_for_timeout(150)
        st = page.evaluate("() => { const a = document.getElementById('kidsStaticAudio'); return { paused: a.paused, rate: a.playbackRate }; }")
        assert not st["paused"] and st["rate"] < 0.9, st
        check_clean_page(rec, allow_baseline_puffin_error=env.baseline)
    finally:
        ctx.close()


@register_test("T2-F7-5", 2, "F7", ("sardegna", "petit-prince"), False, "Clicking single word .kw-token applies playbackRate and sets .kw-token.active")
def t2_f7_5(env: RunnerEnv) -> None:
    targets = active_book_targets(env)
    ctx, page, rec = env.new_session()
    try:
        env.goto_reader(page, open_book_query(env, targets[0][0], "&mode=seby&lang=de"))
        ensure_settings_popover(page, True)
        page.locator("#kidsSettingsPopover button[onclick='setKidsSpeedStep(0)']").click()
        ensure_settings_popover(page, False)
        tok = page.locator("#bookPageLeft .kw-token[onclick*='assets/words_audio/de/']").first
        if tok.count() == 0:
            tok = page.locator("#bookPageLeft .kw-token").first
        tok.click()
        page.wait_for_timeout(120)
        st_slow = page.evaluate(
            "() => ({ active: document.querySelectorAll('#bookPageLeft .kw-token.active').length, rate: document.getElementById('kidsStaticAudio')?.playbackRate, defaultRate: document.getElementById('kidsStaticAudio')?.defaultPlaybackRate })"
        )
        assert st_slow["active"] >= 1, f"Expected .kw-token.active on word click: {st_slow}"
        assert st_slow["rate"] < 0.85, f"Expected slow playbackRate at speed step 0 on word click, got {st_slow}"

        ensure_settings_popover(page, True)
        page.locator("#kidsSettingsPopover button[onclick='setKidsSpeedStep(4)']").click()
        ensure_settings_popover(page, False)
        tok.click()
        page.wait_for_timeout(120)
        st_fast = page.evaluate(
            "() => ({ active: document.querySelectorAll('#bookPageLeft .kw-token.active').length, rate: document.getElementById('kidsStaticAudio')?.playbackRate })"
        )
        assert st_fast["rate"] > 1.05 and st_fast["rate"] > st_slow["rate"], f"Expected fast playbackRate at speed step 4, got {st_fast} vs {st_slow}"
        check_clean_page(rec, allow_baseline_puffin_error=env.baseline)
    finally:
        ctx.close()


# --- F8 Boundaries (5) ---
@register_test("T2-F8-1", 2, "F8", ("sardegna", "petit-prince"), False, "Toggling Grammar ON->OFF->ON keeps fitKidsTextToPatch() <= 2px overflow")
def t2_f8_1(env: RunnerEnv) -> None:
    targets = active_book_targets(env)
    ctx, page, rec = env.new_session()
    try:
        for alias, _ in targets:
            env.goto_reader(page, open_book_query(env, alias, "&mode=emma&lang=de"))
            for state in (True, False, True):
                set_grammar_mode(page, state)
                page.evaluate("() => window.fitKidsTextToPatch && fitKidsTextToPatch()")
                assert_fit_metrics(page.evaluate("() => window.__kidsTextFitMetrics()"), f"{alias} grammar={state}")
            check_clean_page(rec, allow_baseline_puffin_error=env.baseline)
    finally:
        ctx.close()


@register_test("T2-F8-2", 2, "F8", ("sardegna", "petit-prince"), False, "DE separable verb arc renders valid cubic Bezier path (M ... C ...)")
def t2_f8_2(env: RunnerEnv) -> None:
    targets = active_book_targets(env)
    ctx, page, rec = env.new_session()
    try:
        for alias, sid in targets:
            kb = load_book_json(sid)
            pnum, lvl = next(
                (pg["page"], lv)
                for pg in kb["pages"]
                for lv in ("seby", "ale", "emma")
                if any(t.get("sep_group") for t in pg.get("levels", {}).get(lv, {}).get("de", {}).get("tokens", []))
            )
            env.goto_reader(page, open_book_query(env, alias, f"&mode={lvl}&lang=de&page={pnum}"))
            set_grammar_mode(page, True)
            page.wait_for_timeout(120)
            paths = page.evaluate(
                "() => Array.from(document.querySelectorAll('#openBookSpread svg.kids-sep-verb-arcs path.sep-verb-arc-line')).map(p => p.getAttribute('d') || '')"
            )
            assert paths and all(re.match(r"^M\s+[\d.]+\s+[\d.]+\s+C\s+", p) for p in paths), paths
            check_clean_page(rec, allow_baseline_puffin_error=env.baseline)
    finally:
        ctx.close()


@register_test("T2-F8-3", 2, "F8", ("sardegna", "petit-prince"), False, "Hovering prefix highlights stem AND hovering stem highlights prefix (.sep-brother-hover)")
def t2_f8_3(env: RunnerEnv) -> None:
    targets = active_book_targets(env)
    ctx, page, rec = env.new_session()
    try:
        alias, sid = targets[-1]
        kb = load_book_json(sid)
        pnum, lvl = next(
            (pg["page"], lv)
            for pg in kb["pages"]
            for lv in ("seby", "ale", "emma")
            if any(t.get("sep_role") == "prefix" for t in pg.get("levels", {}).get(lv, {}).get("de", {}).get("tokens", []))
        )
        env.goto_reader(page, open_book_query(env, alias, f"&mode={lvl}&lang=de&page={pnum}"))
        set_grammar_mode(page, True)
        prefix_tok = page.locator("#openBookSpread .kw-sep-prefix").first
        gid = prefix_tok.get_attribute("data-sep-group")
        prefix_tok.hover()
        assert page.locator(f"#openBookSpread .kw-token[data-sep-group='{gid}'].sep-brother-hover").count() >= 2
        page.locator(f"#openBookSpread .kw-sep-stem[data-sep-group='{gid}']").first.hover()
        assert page.locator(f"#openBookSpread .kw-token[data-sep-group='{gid}'].sep-brother-hover").count() >= 2
        check_clean_page(rec, allow_baseline_puffin_error=env.baseline)
    finally:
        ctx.close()


@register_test("T2-F8-4", 2, "F8", ("sardegna", "petit-prince"), False, "Switching DE -> FR clears .kids-sep-verb-arcs and shows .kw-end-m/.kw-end-f")
def t2_f8_4(env: RunnerEnv) -> None:
    targets = active_book_targets(env)
    ctx, page, rec = env.new_session()
    try:
        alias, sid = targets[-1]
        kb = load_book_json(sid)
        pnum, lvl = next(
            (pg["page"], lv)
            for pg in kb["pages"]
            for lv in ("seby", "ale", "emma")
            if any(t.get("sep_group") for t in pg.get("levels", {}).get(lv, {}).get("de", {}).get("tokens", []))
        )
        env.goto_reader(page, open_book_query(env, alias, f"&mode={lvl}&lang=de&page={pnum}"))
        set_grammar_mode(page, True)
        assert page.locator("#openBookSpread svg.kids-sep-verb-arcs g.sep-verb-arc-group").count() >= 1
        switch_book_lang(page, "fr")
        assert page.locator("#openBookSpread svg.kids-sep-verb-arcs g.sep-verb-arc-group").count() == 0
        assert page.locator("#openBookSpread .kw-end-m, #openBookSpread .kw-end-f").count() >= 1
        check_clean_page(rec, allow_baseline_puffin_error=env.baseline)
    finally:
        ctx.close()


@register_test("T2-F8-5", 2, "F8", ("sardegna", "petit-prince"), False, "Window resize redraws DE separable verb SVG arcs without NaN coordinates")
def t2_f8_5(env: RunnerEnv) -> None:
    targets = active_book_targets(env)
    ctx, page, rec = env.new_session()
    try:
        alias, sid = targets[-1]
        kb = load_book_json(sid)
        pnum, lvl = next(
            (pg["page"], lv)
            for pg in kb["pages"]
            for lv in ("seby", "ale", "emma")
            if any(t.get("sep_group") for t in pg.get("levels", {}).get(lv, {}).get("de", {}).get("tokens", []))
        )
        env.goto_reader(page, open_book_query(env, alias, f"&mode={lvl}&lang=de&page={pnum}"))
        set_grammar_mode(page, True)
        page.set_viewport_size({"width": 1100, "height": 800})
        page.wait_for_timeout(160)
        paths = page.evaluate(
            "() => Array.from(document.querySelectorAll('#openBookSpread svg.kids-sep-verb-arcs path.sep-verb-arc-line')).map(p => p.getAttribute('d') || '')"
        )
        assert paths and all("NaN" not in p and "undefined" not in p for p in paths), paths
        check_clean_page(rec, allow_baseline_puffin_error=env.baseline)
    finally:
        ctx.close()


# --- F9 Boundaries (5) ---
@register_test("T2-F9-1", 2, "F9", ("sardegna", "petit-prince"), False, "Guest/logged-out user sees seby & ale launch buttons without crashing")
def t2_f9_1(env: RunnerEnv) -> None:
    ctx, page, rec = env.new_session()
    try:
        env.goto_reader(page, "?tab=indice", wait_selector="#indexView", dismiss_puffin_modal=False)
        check_clean_page(rec, strict_puffin_error=True)
        page.evaluate("() => window.PuffinLogin && window.PuffinLogin.loginAsGuest && window.PuffinLogin.loginAsGuest()")
        page.wait_for_timeout(120)
        btns = page.locator("#indexView .kids-img-launch-btn").count()
        assert btns >= 2, f"Expected >=2 launch buttons for guest, got {btns}"
        check_clean_page(rec, strict_puffin_error=True)
    finally:
        ctx.close()


@register_test("T2-F9-2", 2, "F9", ("sardegna", "petit-prince"), False, "Explicit ?mode=seby in URL is NOT overridden on initial load when logged in as riccardo")
def t2_f9_2(env: RunnerEnv) -> None:
    ctx, page, rec = env.new_session()
    try:
        ctx.add_init_script(f"localStorage.setItem('puffin_auth_v2', JSON.stringify({json.dumps(get_puffin_session_payload('riccardo'))}));")
        env.goto_reader(page, open_book_query(env, "sardegna", "&mode=seby"), dismiss_puffin_modal=False)
        check_clean_page(rec, strict_puffin_error=True)
        assert get_active_book_info(page)["mode"] == "seby"
        check_clean_page(rec, strict_puffin_error=True)
    finally:
        ctx.close()


@register_test("T2-F9-3", 2, "F9", ("sardegna", "petit-prince"), False, "Live profile switch while book is open updates reader tier immediately")
def t2_f9_3(env: RunnerEnv) -> None:
    ctx, page, rec = env.new_session()
    try:
        env.goto_reader(page, open_book_query(env, "sardegna", "&mode=seby"), dismiss_puffin_modal=False)
        check_clean_page(rec, strict_puffin_error=True)
        authenticate_puffin_profile(page, "riccardo", reload_url=None)
        assert get_active_book_info(page)["mode"] == "emma", "Live PuffinLogin switch to riccardo did not update mode to emma"
        check_clean_page(rec, strict_puffin_error=True)
    finally:
        ctx.close()


@register_test("T2-F9-4", 2, "F9", ("sardegna", "petit-prince"), False, "Offline / Airplane Mode MD5+seed auth via puffin-seed.v1.json works with network offline")
def t2_f9_4(env: RunnerEnv) -> None:
    seed_disk = json.loads((REPO_ROOT / "puffin-seed.v1.json").read_text(encoding="utf-8"))
    ctx, page, rec = env.new_session()
    try:
        env.goto_reader(page, open_book_query(env, "sardegna"), dismiss_puffin_modal=False)
        check_clean_page(rec, strict_puffin_error=True)
        ctx.set_offline(True)
        res = page.evaluate(
            """async (diskSeed) => {
                const cachedRaw = localStorage.getItem('puffin_offline_seed_v1');
                const cached = cachedRaw ? JSON.parse(cachedRaw) : null;
                const mod = await import('./src/puffin-login.js');
                mod.setAirplaneModeState(true);
                const badVerify = await mod.verifyPuffinCredentials('seby', '9999', { forceOffline: true });
                const guestVerify = await mod.verifyPuffinCredentials('guest', '', { forceOffline: true });
                const md5Sample = mod.computePuffinSecretMd5('seby', 'test-wrong', diskSeed.seed);
                const w = document.getElementById('puffin-widget');
                w.saveActiveSession('riccardo', true, { offline_verified: true, seed_used: diskSeed.seed });
                w.openModal({ tab: 'login' });
                const bannerEl = w.shadowRoot.querySelector('.offline-warning-banner');
                const bannerVis = Boolean(bannerEl && !bannerEl.hidden);
                const bannerText = bannerEl?.textContent || '';
                w.$dialog?.close();
                return {
                    cachedSeed: cached?.seed,
                    cachedProfilesMatch: Object.keys(diskSeed.profiles).every(k => cached?.profiles?.[k]?.secretMd5 === diskSeed.profiles[k].secretMd5),
                    badOk: badVerify.ok,
                    badMode: badVerify.auth_mode,
                    guestOk: guestVerify.ok,
                    guestOffline: guestVerify.offline_verified,
                    guestMode: guestVerify.auth_mode,
                    guestSeed: guestVerify.seed,
                    md5Len: md5Sample.length,
                    bannerVis,
                    bannerText,
                    user: window.PuffinLogin.getCurrentUser(),
                };
            }""",
            seed_disk,
        )
        assert res["cachedSeed"] == seed_disk["seed"] and res["cachedProfilesMatch"], f"puffin-seed.v1.json mismatch: {res}"
        assert res["badOk"] is False and res["badMode"] == "offline_md5_seed", res
        assert res["guestOk"] and res["guestOffline"] and res["guestMode"] == "offline_md5_seed", res
        assert res["guestSeed"] == seed_disk["seed"] and res["md5Len"] == 32, res
        assert res["bannerVis"] and seed_disk["seed"] in res["bannerText"], res
        assert res["user"]["id"] == "riccardo" and res["user"]["offline_verified"] is True, res
        assert get_active_book_info(page)["mode"] == "emma"
        check_clean_page(rec, allow_offline_console=True, strict_puffin_error=True)
    finally:
        ctx.close()


@register_test("T2-F9-5", 2, "F9", ("sardegna", "petit-prince"), False, "Wrong PIN 3 times in PuffinLogin triggers 3-strike lockout without breaking reader")
def t2_f9_5(env: RunnerEnv) -> None:
    ctx, page, rec = env.new_session()
    try:
        env.goto_reader(page, open_book_query(env, "sardegna"), dismiss_puffin_modal=False)
        check_clean_page(rec, strict_puffin_error=True)
        page.evaluate("() => document.getElementById('puffin-widget').shadowRoot.querySelector('.puffin-badge-btn').click()")
        page.wait_for_timeout(120)
        page.evaluate("() => document.getElementById('puffin-widget').shadowRoot.querySelector('.profile-card[data-profile-id=\"seby\"]').click()")
        page.wait_for_timeout(120)
        for _ in range(3):
            for digit in ("9", "8", "7", "6"):
                page.evaluate(
                    """(d) => document.getElementById('puffin-widget').shadowRoot.querySelector(`.cutie-key[data-digit="${d}"]`)?.click()""",
                    digit,
                )
                page.wait_for_timeout(40)
            page.wait_for_timeout(120)
        jammed = page.evaluate("() => Boolean(document.getElementById('puffin-widget').shadowRoot.querySelector('.jam-banner'))")
        assert jammed, "Expected .jam-banner after 3 wrong PIN attempts"
        # Reader behind dialog remains functional
        page.evaluate("() => { const d = document.getElementById('puffin-widget').shadowRoot.querySelector('dialog'); if (d?.open) d.close(); }")
        page.locator("#bookPageRight .kids-edge-nav-arrow.is-right-arrow").click()
        assert get_active_book_info(page)["pages"] == [3, 4]
        check_clean_page(rec, strict_puffin_error=True)
    finally:
        ctx.close()


# --- F10 Boundaries (5) ---
@register_test("T2-F10-1", 2, "F10", ("sardegna", "petit-prince"), True, "Opening Quiz in Parallel Mode on odd page (P1) resolves valid spread questions (not 0/0)")
def t2_f10_1(env: RunnerEnv) -> None:
    env.require_m1_m3(env.has_petit_prince_assets(), "books/petit-prince missing")
    ctx, page, rec = env.new_session()
    try:
        env.goto_reader(page, "?book=petit-prince&parallel=1&page=1&lang=fr")
        page.locator("#kidsNotebookFloatingBar .quiz-pill").click()
        page.wait_for_selector("#antolinQuizDialog[open]", timeout=4000)
        assert page.locator("#antolinQuizBody .antolin-question-card").count() == 3
        check_clean_page(rec)
    finally:
        ctx.close()


@register_test("T2-F10-2", 2, "F10", ("sardegna", "petit-prince"), False, "Quiz progress keys remain isolated by storyId_mode_lang_page_qId")
def t2_f10_2(env: RunnerEnv) -> None:
    targets = active_book_targets(env)
    ctx, page, rec = env.new_session()
    try:
        alias, sid = targets[-1]
        kb = load_book_json(sid)
        c_idx = kb["pages"][1]["questions"]["fr"][0]["correct"]
        env.goto_reader(page, open_book_query(env, alias, "&mode=seby&lang=fr"))
        page.locator("#kidsNotebookFloatingBar .quiz-pill").click()
        page.wait_for_selector("#antolinQuizDialog[open]", timeout=4000)
        page.locator("#antolinQuizBody .antolin-question-card").first.locator(".antolin-opt-btn").nth(c_idx).click()
        page.locator("#antolinQuizDialog button:has-text('Retour')").click()
        assert "1/3" in page.locator("#kidsNotebookFloatingBar .quiz-pill").inner_text()
        switch_book_lang(page, "de")
        assert "0/3" in page.locator("#kidsNotebookFloatingBar .quiz-pill").inner_text()
        check_clean_page(rec, allow_baseline_puffin_error=env.baseline)
    finally:
        ctx.close()


@register_test("T2-F10-3", 2, "F10", ("sardegna", "petit-prince"), False, "Last-spread quiz offers Dashboard CTA instead of Next Spread")
def t2_f10_3(env: RunnerEnv) -> None:
    targets = active_book_targets(env)
    ctx, page, rec = env.new_session()
    try:
        alias, sid = targets[-1]
        last_p = 26 if sid == PETIT_PRINCE_ID else 16
        env.goto_reader(page, open_book_query(env, alias, f"&page={last_p - 1}"))
        page.locator("#kidsNotebookFloatingBar .quiz-pill").click()
        page.wait_for_selector("#antolinQuizDialog[open]", timeout=4000)
        txt = page.locator("#antolinQuizBody").inner_text()
        assert "Dashboard" in txt or "Tableau" in txt, f"Expected Dashboard CTA on last spread, got: {txt}"
        check_clean_page(rec, allow_baseline_puffin_error=env.baseline)
    finally:
        ctx.close()


@register_test("T2-F10-4", 2, "F10", ("sardegna", "petit-prince"), False, "#antolinDashDialog blocks guest/unauth with lock screen and unlocks for authenticated adult")
def t2_f10_4(env: RunnerEnv) -> None:
    ctx, page, rec = env.new_session()
    try:
        env.goto_reader(page, open_book_query(env, "sardegna"), dismiss_puffin_modal=False)
        check_clean_page(rec, strict_puffin_error=True)
        page.evaluate("() => openAntolinDashboardModal()")
        page.wait_for_selector("#antolinDashDialog[open]", timeout=4000)
        assert "Privato" in page.locator("#antolinDashBody").inner_text()
        page.evaluate("() => document.getElementById('antolinDashDialog').close()")

        authenticate_puffin_profile(page, "riccardo", reload_url=None)
        page.evaluate("() => openAntolinDashboardModal()")
        page.wait_for_timeout(180)
        dash_txt = page.locator("#antolinDashBody").inner_text()
        assert "Privato" not in dash_txt and "Riccardo" in dash_txt, dash_txt
        check_clean_page(rec, strict_puffin_error=True)
    finally:
        ctx.close()


@register_test("T2-F10-5", 2, "F10", ("sardegna", "petit-prince"), False, "Quiz footer Next Spread button closes modal and advances spread cleanly")
def t2_f10_5(env: RunnerEnv) -> None:
    targets = active_book_targets(env)
    ctx, page, rec = env.new_session()
    try:
        env.goto_reader(page, open_book_query(env, targets[0][0], "&lang=fr"))
        page.locator("#kidsNotebookFloatingBar .quiz-pill").click()
        page.wait_for_selector("#antolinQuizDialog[open]", timeout=4000)
        page.locator("#antolinQuizBody button.page-turn-btn.primary").click()
        page.wait_for_timeout(140)
        assert not page.locator("#antolinQuizDialog").evaluate("d => d.open")
        assert get_active_book_info(page)["pages"] == [3, 4]
        check_clean_page(rec, allow_baseline_puffin_error=env.baseline)
    finally:
        ctx.close()


@register_test("T2-F10-6", 2, "F10", ("petit-prince",), True, "Antolin Quiz & Dashboard fit within mobile/tablet viewports and Esc dismisses Dashboard/Puffin without leaving book")
def t2_f10_6(env: RunnerEnv) -> None:
    env.require_m1_m3(env.has_petit_prince_assets(), "books/petit-prince missing")
    for vw, vh in ((375, 667), (390, 844), (768, 1024)):
        ctx, page, rec = env.new_session(viewport={"width": vw, "height": vh})
        try:
            env.goto_reader(page, "?book=petit-prince&mode=ale&lang=fr", dismiss_puffin_modal=False)
            page.locator("#kidsNotebookFloatingBar .quiz-pill").click()
            page.wait_for_selector("#antolinQuizDialog[open]", timeout=4000)
            oob = page.evaluate("""() => {
                const r = document.getElementById('antolinQuizDialog').getBoundingClientRect();
                return r.left < 0 || r.top < 0 || r.right > window.innerWidth + 1 || r.bottom > window.innerHeight + 1;
            }""")
            assert not oob, f"Quiz dialog out of bounds on {vw}x{vh}"
            page.keyboard.press("Escape")
            page.wait_for_timeout(150)
            assert not page.locator("#antolinQuizDialog").evaluate("d => d.open")
            assert "/books" not in page.url

            page.evaluate("() => openAntolinDashboardModal()")
            page.wait_for_selector("#antolinDashDialog[open]", timeout=4000)
            page.keyboard.press("Escape")
            page.wait_for_timeout(150)
            assert not page.locator("#antolinDashDialog").evaluate("d => d.open")
            assert "/books" not in page.url

            # Mobile 2-step Esc from #kidsSettingsPopover -> /books/
            ensure_settings_popover(page, True)
            page.keyboard.press("Escape")
            page.wait_for_timeout(150)
            assert not page.locator("#kidsSettingsPopover").is_visible()
            assert "/books" not in page.url
            page.keyboard.press("Escape")
            page.wait_for_url(re.compile(r"/books/?(\?.*)?$"), timeout=5000)
            check_clean_page(rec, strict_puffin_error=True)
        finally:
            ctx.close()


# --- F11 Boundaries (6) ---
@register_test("T2-F11-1", 2, "F11", ("sardegna", "petit-prince"), True, "docs/CONSTITUTION.md explicitly distinguishes learning langs (FR/IT/DE) from en-GB")
def t2_f11_1(env: RunnerEnv) -> None:
    const_path = REPO_ROOT / "docs" / "CONSTITUTION.md"
    env.require_m1_m3(const_path.exists(), "docs/CONSTITUTION.md missing")
    txt = const_path.read_text(encoding="utf-8")
    assert all(k in txt for k in ("FR", "IT", "DE", "en-GB"))
    assert re.search(r"traduzion|translat|pari pari|gloss", txt, re.IGNORECASE)


@register_test("T2-F11-2", 2, "F11", ("petit-prince",), True, "README.md includes copyright dates 2015 (CH/EU) and 2032 (France)")
def t2_f11_2(env: RunnerEnv) -> None:
    txt = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    env.require_m1_m3("Petit Prince" in txt, "README.md missing Le Petit Prince section")
    assert "2015" in txt and "2032" in txt and re.search(r"(CH|Svizzera|Switzerland|EU)", txt) and "France" in txt


@register_test("T2-F11-3", 2, "F11", ("sardegna", "petit-prince"), False, "Embedded RangeRequestHandler serves HTTP 206 Partial Content with Content-Range on .mp3")
def t2_f11_3(env: RunnerEnv) -> None:
    import urllib.request

    _, sid = active_book_targets(env)[-1]
    kb = load_book_json(sid)
    first_readable = next(p for p in kb["pages"] if not p.get("is_frontispiece"))
    rel = first_readable["levels"]["seby"]["fr"]["audio_mp3"]
    req = urllib.request.Request(f"{env.base_origin}/{rel}", headers={"Range": "bytes=0-1023"})
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 206, f"Expected HTTP 206, got {resp.status}"
        cr = resp.headers.get("Content-Range", "")
        assert cr.startswith("bytes 0-1023/"), f"Unexpected Content-Range: {cr}"
        assert len(resp.read()) == 1024


@register_test("T2-F11-4", 2, "F11", ("sardegna", "petit-prince"), False, "Token karaoke timings (s, e) are non-negative with s < e (and monotonic starts on petit-prince)")
def t2_f11_4(env: RunnerEnv) -> None:
    for _, sid in active_book_targets(env):
        kb = load_book_json(sid)
        for pg in kb["pages"]:
            if pg.get("is_frontispiece"):
                continue
            for lvl, langs_map in pg["levels"].items():
                for lang, obj in langs_map.items():
                    prev_s = -1.0
                    for tok in obj.get("tokens", []):
                        s, e = float(tok["s"]), float(tok["e"])
                        assert 0 <= s < e, f"{sid} P{pg['page']} {lvl}/{lang} {tok['w']}: s={s}, e={e}"
                        if sid == PETIT_PRINCE_ID:
                            assert s >= prev_s - 0.05, f"{sid} P{pg['page']} {lvl}/{lang} non-monotonic {s} < {prev_s}"
                        prev_s = s


@register_test("T2-F11-5", 2, "F11", ("sardegna", "petit-prince"), False, "stories.yaml keeps all 7 mic-recorded stories intact alongside multi-book catalog")
def t2_f11_5(env: RunnerEnv) -> None:
    import yaml

    data = yaml.safe_load((REPO_ROOT / "stories.yaml").read_text(encoding="utf-8"))
    stories = data.get("stories", [])
    assert len(stories) == 7, f"Expected 7 stories in stories.yaml, got {len(stories)}"
    for st in stories:
        assert st.get("status") == "complete" and not st.get("missing_assets"), st.get("slug")


@register_test("T2-F11-6", 2, "F11", ("petit-prince",), True, "Spread 1 has zero X-ray; Spread 2 Page 3 interactive boa/hat -> elephant X-ray reveal on hover, click/tap toggle, zero layout shift, non-fullscreen, mobile 390x844, and Parallel Mode")
def t2_f11_6(env: RunnerEnv) -> None:
    env.require_m1_m3(env.has_petit_prince_assets(), "books/petit-prince missing")

    inspect_xray_js = """(sel) => {
        const leaf = document.querySelector(sel);
        if (!leaf) return null;
        const ov = leaf.querySelector('.kids-page-xray-overlay');
        const hs = leaf.querySelector('.kids-xray-hotspot');
        const ovStyle = ov ? getComputedStyle(ov) : null;
        const hsStyle = hs ? getComputedStyle(hs) : null;
        return {
            page: leaf.dataset.page || '',
            hasRevealClass: leaf.classList.contains('has-xray-reveal'),
            active: leaf.classList.contains('boa-xray-active'),
            leafBg: leaf.style.backgroundImage || '',
            ovBg: ov ? (ov.style.backgroundImage || '') : '',
            ovOpacity: ovStyle ? parseFloat(ovStyle.opacity) : -1,
            ariaPressed: hs ? hs.getAttribute('aria-pressed') : null,
            cursor: hsStyle ? hsStyle.cursor : '',
            docOX: document.documentElement.scrollWidth - window.innerWidth,
        };
    }"""

    # 1. Spread 1 has zero X-ray; Spread 2 Page 3 desktop fullscreen + hover/unhover + click toggle + zero layout shift + non-fullscreen
    ctx, page, rec = env.new_session(viewport={"width": 1280, "height": 800})
    try:
        env.goto_reader(page, "?book=petit-prince&mode=emma&lang=fr&page=1", wait_selector="#openBookSpread .kids-watercolor-leaf")
        assert page.locator("#openBookSpread .has-xray-reveal").count() == 0, "Spread 1 must have zero .has-xray-reveal"
        assert page.locator("#openBookSpread .kids-xray-hotspot").count() == 0, "Spread 1 must have zero .kids-xray-hotspot"
        assert page.locator("#bookPageLeft .kids-watercolor-leaf.is-frontispiece").count() == 1, "Spread 1 Left must be .is-frontispiece"

        env.goto_reader(page, "?book=petit-prince&mode=emma&lang=fr&page=3")
        left_sel = "#bookPageLeft .kids-watercolor-leaf[data-page='3']"
        s0 = page.evaluate(inspect_xray_js, left_sel)
        assert s0 is not None and s0["hasRevealClass"], s0
        assert "wc_p03.jpg" in s0["leafBg"] and "wc_p03_xray.jpg" in s0["ovBg"], s0
        assert s0["ovOpacity"] <= 0.05 and s0["ariaPressed"] == "false" and not s0["active"], s0
        assert s0["cursor"] == "pointer", s0

        fits_before = page.evaluate("() => (window.__kidsTextFitMetrics ? window.__kidsTextFitMetrics() : [])")
        assert fits_before and all(m["fits"] and m["overflowY"] <= 2 and m["overflowX"] <= 2 for m in fits_before), fits_before

        # Hover reveal
        page.locator("#bookPageLeft .kids-xray-hotspot").hover()
        page.wait_for_timeout(480)
        s_hover = page.evaluate(inspect_xray_js, left_sel)
        assert s_hover["ovOpacity"] >= 0.99, s_hover

        # Move mouse away -> cross-fade back to closed boa/hat
        page.mouse.move(10, 10)
        page.wait_for_timeout(480)
        s_unhover = page.evaluate(inspect_xray_js, left_sel)
        assert s_unhover["ovOpacity"] <= 0.05, s_unhover

        # Click toggle ON -> stays active after moving mouse away
        page.locator("#bookPageLeft .kids-xray-hotspot").click()
        page.mouse.move(10, 10)
        page.wait_for_timeout(480)
        s_on = page.evaluate(inspect_xray_js, left_sel)
        assert s_on["active"] and s_on["ariaPressed"] == "true" and s_on["ovOpacity"] >= 0.99, s_on

        fits_after = page.evaluate("() => (window.__kidsTextFitMetrics ? window.__kidsTextFitMetrics() : [])")
        assert fits_after == fits_before, (fits_before, fits_after)

        # Click toggle OFF -> resets cleanly after moving mouse away
        page.locator("#bookPageLeft .kids-xray-hotspot").click()
        page.mouse.move(10, 10)
        page.wait_for_timeout(480)
        s_off = page.evaluate(inspect_xray_js, left_sel)
        assert (not s_off["active"]) and s_off["ariaPressed"] == "false" and s_off["ovOpacity"] <= 0.05, s_off

        # Non-fullscreen mode
        page.locator("#kidsNotebookFloatingBar button[title='Tutta Pagina']").click()
        page.wait_for_timeout(160)
        assert not is_kids_fullscreen(page)
        page.locator("#bookPageLeft .kids-xray-hotspot").click()
        page.mouse.move(10, 10)
        page.wait_for_timeout(480)
        s_nf = page.evaluate(inspect_xray_js, left_sel)
        assert s_nf["active"] and s_nf["ariaPressed"] == "true" and s_nf["ovOpacity"] >= 0.99, s_nf
        check_clean_page(rec)
    finally:
        ctx.close()

    # 2. Parallel Mode (?parallel=1&page=3): facing Page 3 leaves sync toggle
    ctx, page, rec = env.new_session(viewport={"width": 1280, "height": 800})
    try:
        env.goto_reader(page, "?book=petit-prince&mode=emma&lang=fr&parallel=1&page=3")
        page.locator("#bookPageLeft .kids-xray-hotspot").click()
        page.mouse.move(10, 10)
        page.wait_for_timeout(480)
        pl = page.evaluate(inspect_xray_js, "#bookPageLeft .kids-watercolor-leaf[data-page='3']")
        pr = page.evaluate(inspect_xray_js, "#bookPageRight .kids-watercolor-leaf[data-page='3']")
        assert pl and pr, (pl, pr)
        assert pl["active"] and pl["ariaPressed"] == "true" and pl["ovOpacity"] >= 0.99, pl
        assert pr["active"] and pr["ariaPressed"] == "true" and pr["ovOpacity"] >= 0.99, pr
        check_clean_page(rec)
    finally:
        ctx.close()

    # 3. Mobile 390x844 tap toggle + zero horizontal overflow
    ctx, page, rec = env.new_session(viewport={"width": 390, "height": 844})
    try:
        env.goto_reader(page, "?book=petit-prince&mode=seby&lang=fr&page=3")
        left_sel = "#bookPageLeft .kids-watercolor-leaf[data-page='3']"
        m0 = page.evaluate(inspect_xray_js, left_sel)
        assert m0 and m0["hasRevealClass"] and "wc_p03.jpg" in m0["leafBg"] and m0["ovOpacity"] <= 0.05, m0
        assert m0["docOX"] <= 1, m0
        page.locator("#bookPageLeft .kids-xray-hotspot").click()
        page.mouse.move(10, 10)
        page.wait_for_timeout(480)
        m1 = page.evaluate(inspect_xray_js, left_sel)
        assert m1["active"] and m1["ariaPressed"] == "true" and m1["ovOpacity"] >= 0.99 and m1["docOX"] <= 1, m1
        page.locator("#bookPageLeft .kids-xray-hotspot").click()
        page.mouse.move(10, 10)
        page.wait_for_timeout(480)
        m2 = page.evaluate(inspect_xray_js, left_sel)
        assert (not m2["active"]) and m2["ariaPressed"] == "false" and m2["ovOpacity"] <= 0.05, m2
        check_clean_page(rec)
    finally:
        ctx.close()


# --- F12 Boundaries (5) ---
@register_test("T2-F12-1", 2, "F12", ("sardegna", "petit-prince"), False, "/books/?kid=sebastian&mode=seby renders shelf and forwards kid & mode params in card links", requires_m5=True)
def t2_f12_1(env: RunnerEnv) -> None:
    import urllib.parse

    env.require_m5(env.has_bookshelf(), "books/index.html missing")
    ctx, page, rec = env.new_session()
    try:
        goto_bookshelf(page, env, "/books/?kid=sebastian&mode=seby")
        check_clean_page(rec)
        cards = inspect_bookshelf_cards(page)
        assert "sardegna" in cards and "petit-prince" in cards, cards
        for bname in ("sardegna", "petit-prince"):
            links = cards[bname]["links"]
            assert any(
                (qs := urllib.parse.parse_qs(urllib.parse.urlparse(l["absHref"]).query)).get("book") == [bname]
                and qs.get("kid") == ["sebastian"]
                and qs.get("mode") == ["seby"]
                for l in links
            ), f"{bname}: expected link preserving kid=sebastian&mode=seby, got {links}"

        click_bookshelf_target(page, "sardegna")
        page.wait_for_selector(".kids-sentence-box", timeout=10000)
        page.wait_for_timeout(140)
        qs_final = urllib.parse.parse_qs(urllib.parse.urlparse(page.url).query)
        assert qs_final.get("book") == ["sardegna"], page.url
        assert qs_final.get("kid") == ["sebastian"] and qs_final.get("mode") == ["seby"], page.url
        assert get_active_book_info(page)["mode"] == "seby"
        check_clean_page(rec)
    finally:
        ctx.close()


@register_test("T2-F12-2", 2, "F12", ("sardegna",), False, "/books/?book=sardegna&mode=seby&page=6&kid=sebastian redirects smoothly to /?book=sardegna&mode=seby&page=6&kid=sebastian", requires_m5=True)
def t2_f12_2(env: RunnerEnv) -> None:
    import urllib.parse

    env.require_m5(env.has_bookshelf(), "books/index.html missing")
    ctx, page, rec = env.new_session()
    try:
        goto_bookshelf(page, env, "/books/?book=sardegna&mode=seby&page=6&kid=sebastian", wait_fonts=False)
        page.wait_for_url(lambda u: "/books" not in u.split("?", 1)[0], timeout=8000)
        page.wait_for_selector(".kids-sentence-box", timeout=10000)
        page.evaluate("() => document.fonts ? document.fonts.ready : Promise.resolve()")
        page.wait_for_timeout(160)
        assert "/books" not in page.url.split("?", 1)[0], f"Expected redirect out of /books/, got {page.url}"
        qs = urllib.parse.parse_qs(urllib.parse.urlparse(page.url).query)
        assert qs.get("book") == ["sardegna"] and qs.get("mode") == ["seby"], page.url
        assert qs.get("kid") == ["sebastian"] and qs.get("page") == ["6"], page.url
        info = get_active_book_info(page)
        assert info["storyId"] == SARDEGNA_ID and info["mode"] == "seby" and info["pages"] == [5, 6], info
        check_clean_page(rec)
    finally:
        ctx.close()


@register_test("T2-F12-3", 2, "F12", ("petit-prince",), True, "/books/?book=petit-prince&mode=emma&lang=de&page=10 redirects preserving all params", requires_m5=True)
def t2_f12_3(env: RunnerEnv) -> None:
    import urllib.parse

    env.require_m5(env.has_bookshelf(), "books/index.html missing")
    env.require_m1_m3(env.has_petit_prince_assets(), "books/petit-prince missing")
    ctx, page, rec = env.new_session()
    try:
        goto_bookshelf(page, env, "/books/?book=petit-prince&mode=emma&lang=de&page=10", wait_fonts=False)
        page.wait_for_url(lambda u: "/books" not in u.split("?", 1)[0], timeout=8000)
        page.wait_for_selector(".kids-sentence-box", timeout=10000)
        page.evaluate("() => document.fonts ? document.fonts.ready : Promise.resolve()")
        page.wait_for_timeout(160)
        assert "/books" not in page.url.split("?", 1)[0], f"Expected redirect out of /books/, got {page.url}"
        qs = urllib.parse.parse_qs(urllib.parse.urlparse(page.url).query)
        assert qs.get("book") == ["petit-prince"] and qs.get("mode") == ["emma"], page.url
        assert qs.get("lang") == ["de"] and qs.get("page") == ["10"], page.url
        info = get_active_book_info(page)
        assert info["storyId"] == PETIT_PRINCE_ID and info["mode"] == "emma" and info["lang"] == "de" and info["pages"] == [9, 10], info
        check_clean_page(rec)
    finally:
        ctx.close()


@register_test("T2-F12-4", 2, "F12", ("sardegna", "petit-prince"), False, "/books/ renders cleanly with empty kos_kids_bookmarks_v1 AND corrupted JSON '{bad'", requires_m5=True)
def t2_f12_4(env: RunnerEnv) -> None:
    env.require_m5(env.has_bookshelf(), "books/index.html missing")
    # 1. Empty bookmarks
    ctx1, page1, rec1 = env.new_session()
    try:
        goto_bookshelf(page1, env, "/books/")
        check_clean_page(rec1)
        cards1 = inspect_bookshelf_cards(page1)
        assert "sardegna" in cards1 and "petit-prince" in cards1, cards1
        assert not cards1["sardegna"]["resumeHits"] and not cards1["petit-prince"]["resumeHits"], cards1
    finally:
        ctx1.close()

    # 2. Corrupted JSON bookmarks
    ctx2, page2, rec2 = env.new_session()
    try:
        ctx2.add_init_script("localStorage.setItem('kos_kids_bookmarks_v1', '{bad');")
        goto_bookshelf(page2, env, "/books/")
        check_clean_page(rec2)
        cards2 = inspect_bookshelf_cards(page2)
        assert "sardegna" in cards2 and "petit-prince" in cards2, cards2
        assert cards2["sardegna"]["img"]["complete"] and cards2["petit-prince"]["img"]["complete"]
    finally:
        ctx2.close()


@register_test("T2-F12-5", 2, "F12", ("sardegna", "petit-prince"), False, "Mobile viewport (412x915) on /books/ has zero horizontal overflow and title inside upper cover parchment", requires_m5=True)
def t2_f12_5(env: RunnerEnv) -> None:
    env.require_m5(env.has_bookshelf(), "books/index.html missing")
    ctx, page, rec = env.new_session(viewport={"width": 412, "height": 915})
    try:
        goto_bookshelf(page, env, "/books/")
        check_clean_page(rec)
        dims = page.evaluate("() => ({ sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth })")
        assert dims["sw"] <= dims["cw"] + 2, f"Horizontal overflow on 412x915 /books/: {dims}"
        cards = inspect_bookshelf_cards(page)
        assert "sardegna" in cards and "petit-prince" in cards, cards
        for name, card in cards.items():
            assert card["titleRect"] is not None, f"{name}: missing titleRect on mobile"
            assert card["imgRect"]["top"] <= card["titleRect"]["top"] and card["titleRect"]["bottom"] <= card["imgRect"]["top"] + card["imgRect"]["height"] * 0.30, (
                f"{name}: expected title inside upper cover parchment on mobile: {card}"
            )
            assert card["imgRect"]["left"] <= card["titleRect"]["left"] and card["titleRect"]["right"] <= card["imgRect"]["right"], card
            assert card["img"]["complete"] and card["img"]["naturalWidth"] > 0, card["img"]
        check_clean_page(rec)
    finally:
        ctx.close()


@register_test("T2-F12-6", 2, "F12", ("sardegna", "petit-prince"), False, "Libreria uses monochrome currentColor SVG + numeric badge (zero 📚) and /books/ renders minimal 3D brossura", requires_m5=True)
def t2_f12_6(env: RunnerEnv) -> None:
    env.require_m5(env.has_bookshelf(), "books/index.html missing")
    ctx, page, rec = env.new_session()
    try:
        env.goto_reader(page, "?book=petit-prince")
        fs = page.evaluate("""() => {
            const el = document.getElementById('kidsFullscreenBooksLink');
            const svg = el?.querySelector('svg');
            return {
                txt: el?.innerText || '',
                stroke: svg?.getAttribute('stroke'),
                fill: svg?.getAttribute('fill'),
                badge: el?.querySelector('.books-count-badge')?.textContent?.trim(),
            };
        }""")
        assert "📚" not in fs["txt"] and fs["stroke"] == "currentColor" and fs["fill"] == "none" and fs["badge"] == "2", fs

        goto_bookshelf(page, env, "/books/")
        sh = page.evaluate("""() => ({
            h1Txt: document.querySelector('.topbar-title')?.innerText || '',
            hasSvg: Boolean(document.querySelector('.topbar-title svg')),
            badge: document.getElementById('shelfBookCountBadge')?.textContent?.trim(),
            vols: document.querySelectorAll('.book-3d-volume').length,
            spines: document.querySelectorAll('.book-spine-sheen').length,
            btns: document.querySelectorAll('.book-card button').length,
        })""")
        assert "📚" not in sh["h1Txt"] and sh["hasSvg"] and sh["badge"] == "2", sh
        assert sh["vols"] == 2 and sh["spines"] == 2 and sh["btns"] == 0, sh
        check_clean_page(rec)
    finally:
        ctx.close()


# ===========================================================================
# TIER 3: 13 Pairwise Cross-Feature Combination Tests
# ===========================================================================

@register_test("T3-01", 3, "F2", ("sardegna", "petit-prince"), True, "Pairwise F2xF3: Book Selector x Bookmark per-book isolation")
def t3_01(env: RunnerEnv) -> None:
    env.require_m1_m3(env.has_petit_prince_assets(), "books/petit-prince missing")
    ctx, page, rec = env.new_session()
    try:
        env.goto_reader(page, "?book=petit-prince&page=9&mode=ale&lang=de")
        click_bookmark_button(page, "save")
        page.locator("#bookPageRight .kids-edge-nav-arrow.is-right-arrow").click()
        page.wait_for_timeout(120)
        select_book_in_ui(page, "sardegna")
        page.locator("#bookPageRight .kids-edge-nav-arrow.is-right-arrow").click()
        page.wait_for_timeout(120)
        set_tier(page, "seby")
        switch_book_lang(page, "it")
        click_bookmark_button(page, "save")
        select_book_in_ui(page, "petit-prince")
        click_bookmark_button(page, "resume")
        info = get_active_book_info(page)
        assert info["pages"] == [9, 10] and info["mode"] == "ale" and info["lang"] == "de", info
        check_clean_page(rec)
    finally:
        ctx.close()


@register_test("T3-02", 3, "F1", ("petit-prince",), True, "Pairwise F1xF6: ?book=petit-prince&mode=emma&lang=fr&parallel=1&page=19")
def t3_02(env: RunnerEnv) -> None:
    env.require_m1_m3(env.has_petit_prince_assets(), "books/petit-prince missing")
    ctx, page, rec = env.new_session()
    try:
        env.goto_reader(page, "?book=petit-prince&mode=emma&lang=fr&parallel=1&page=19")
        check_clean_page(rec)
        info = get_active_book_info(page)
        assert info["pages"] == [19, 19] and info["badges"] == ["18 · FR", "18 · EN"] and info["mode"] == "emma", info
        assert_fit_metrics(page.evaluate("() => window.__kidsTextFitMetrics()"), "T3-02")
    finally:
        ctx.close()


@register_test("T3-03", 3, "F4", ("sardegna", "petit-prince"), False, "Pairwise F4xF8: CEFR Tiers x Montessori Grammar & DE Separable Verbs")
def t3_03(env: RunnerEnv) -> None:
    targets = active_book_targets(env)
    ctx, page, rec = env.new_session()
    try:
        alias, sid = targets[-1]
        kb = load_book_json(sid)
        pnum = next(
            pg["page"]
            for pg in kb["pages"]
            if any(t.get("sep_group") for lv in ("seby", "ale", "emma") for t in pg.get("levels", {}).get(lv, {}).get("de", {}).get("tokens", []))
        )
        env.goto_reader(page, open_book_query(env, alias, f"&lang=de&page={pnum}"))
        set_grammar_mode(page, True)
        for tier in ("seby", "ale", "emma"):
            set_tier(page, tier)
            page.evaluate("() => window.fitKidsTextToPatch && fitKidsTextToPatch()")
            assert page.locator("#openBookSpread .kids-watercolor-leaf.grammar-on").count() == 2
            assert_fit_metrics(page.evaluate("() => window.__kidsTextFitMetrics()"), f"T3-03 {tier}")
        check_clean_page(rec, allow_baseline_puffin_error=env.baseline)
    finally:
        ctx.close()


@register_test("T3-04", 3, "F5", ("sardegna", "petit-prince"), False, "Pairwise F5xF6: 3 Learning Langs x Parallel Mode on P19 (or P5)")
def t3_04(env: RunnerEnv) -> None:
    targets = active_book_targets(env)
    ctx, page, rec = env.new_session()
    try:
        alias, sid = targets[-1]
        pnum = 19 if sid == PETIT_PRINCE_ID else 5
        disp = (pnum - 1) if sid == PETIT_PRINCE_ID else pnum
        for b_lang, t_lang in (("fr", "en"), ("it", "en"), ("de", "en"), ("de", "it"), ("fr", "it")):
            env.goto_reader(page, open_book_query(env, alias, f"&mode=emma&lang={b_lang}&parallel=1&page={pnum}"))
            switch_translation_lang(page, t_lang)
            info = get_active_book_info(page)
            assert info["badges"] == [f"{disp} · {b_lang.upper()}", f"{disp} · {t_lang.upper()}"], info
            if t_lang == "en":
                rec.clear()
                page.evaluate("() => { window.__kosTtsCalls = []; }")
                page.locator("#kidsNotebookFloatingBar .listen-pill").nth(1).click()
                page.wait_for_timeout(120)
                calls = page.evaluate("() => window.__kosTtsCalls")
                assert calls and calls[-1]["lang"] == "en-GB" and not rec.audio_requests
        check_clean_page(rec, allow_baseline_puffin_error=env.baseline)
    finally:
        ctx.close()


@register_test("T3-05", 3, "F9", ("sardegna", "petit-prince"), True, "Pairwise F9xF3: PuffinLogin (riccardo) x Bookmark persistence across reload")
def t3_05(env: RunnerEnv) -> None:
    if env.baseline:
        raise SkipTest("pre-M1/M3 baseline: Bookmark UI not yet implemented")
    ctx, page, rec = env.new_session()
    try:
        env.goto_reader(page, "?book=sardegna", dismiss_puffin_modal=False)
        check_clean_page(rec, strict_puffin_error=True)
        authenticate_puffin_profile(page, "riccardo", reload_url=f"{env.base_url}?book=sardegna&page=11")
        click_bookmark_button(page, "save")
        env.goto_reader(page, "?book=sardegna&page=1", dismiss_puffin_modal=False)
        click_bookmark_button(page, "resume")
        info = get_active_book_info(page)
        uid = page.evaluate("() => window.PuffinLogin.getCurrentUser()?.id")
        assert uid == "riccardo" and info["pages"] == [11, 12], (uid, info)
        check_clean_page(rec, strict_puffin_error=True)
    finally:
        ctx.close()


@register_test("T3-06", 3, "F9", ("sardegna", "petit-prince"), False, "Pairwise F9xF10: PuffinLogin (ale) x Antolin Quiz -> Dashboard telemetry")
def t3_06(env: RunnerEnv) -> None:
    ctx, page, rec = env.new_session()
    try:
        alias, sid = active_book_targets(env)[-1]
        kb = load_book_json(sid)
        qs = kb["pages"][1]["questions"]["fr"]
        env.goto_reader(page, open_book_query(env, alias, "&lang=fr"), dismiss_puffin_modal=False)
        check_clean_page(rec, strict_puffin_error=True)
        authenticate_puffin_profile(page, "ale", reload_url=f"{env.base_url}{open_book_query(env, alias, '&lang=fr')}")
        page.locator("#kidsNotebookFloatingBar .quiz-pill").click()
        page.wait_for_selector("#antolinQuizDialog[open]", timeout=4000)
        for idx, q in enumerate(qs):
            page.locator("#antolinQuizBody .antolin-question-card").nth(idx).locator(".antolin-opt-btn").nth(q["correct"]).click()
        page.locator("#antolinQuizDialog button:has-text('Retour')").click()
        page.evaluate("() => openAntolinDashboardModal()")
        page.wait_for_selector("#antolinDashDialog[open]", timeout=4000)
        page.wait_for_timeout(160)
        dash = page.locator("#antolinDashBody").inner_text()
        assert "Alessandro" in dash and "FR" in dash and "Pag. 2" in dash, dash
        check_clean_page(rec, strict_puffin_error=True)
    finally:
        ctx.close()


@register_test("T3-07", 3, "F7", ("sardegna", "petit-prince"), False, "Pairwise F7xF5: Reading Speeds x Learning Languages (0.75x FR vs 1.3x DE)")
def t3_07(env: RunnerEnv) -> None:
    targets = active_book_targets(env)
    ctx, page, rec = env.new_session()
    try:
        env.goto_reader(page, open_book_query(env, targets[0][0], "&lang=fr"))
        ensure_settings_popover(page, True)
        page.locator("#kidsSettingsPopover button[onclick='setKidsSpeedStep(0)']").click()
        ensure_settings_popover(page, False)
        page.locator("#kidsNotebookFloatingBar .listen-pill").first.click()
        page.wait_for_timeout(120)
        fr_rate = page.evaluate("() => document.getElementById('kidsStaticAudio')?.playbackRate")
        switch_book_lang(page, "de")
        ensure_settings_popover(page, True)
        page.locator("#kidsSettingsPopover button[onclick='setKidsSpeedStep(4)']").click()
        ensure_settings_popover(page, False)
        page.locator("#kidsNotebookFloatingBar .listen-pill").first.click()
        page.wait_for_timeout(120)
        de_rate = page.evaluate("() => document.getElementById('kidsStaticAudio')?.playbackRate")
        assert fr_rate < 0.80 and de_rate > 1.15, (fr_rate, de_rate)
        check_clean_page(rec, allow_baseline_puffin_error=env.baseline)
    finally:
        ctx.close()


@register_test("T3-08", 3, "F6", ("sardegna", "petit-prince"), False, "Pairwise F6xF10: Parallel Mode x Antolin Quizzes stay in book language (not EN)")
def t3_08(env: RunnerEnv) -> None:
    targets = active_book_targets(env)
    ctx, page, rec = env.new_session()
    try:
        alias, sid = targets[-1]
        kb = load_book_json(sid)
        expected_fr_qs = [q["q"] for q in kb["pages"][1]["questions"]["fr"]]
        env.goto_reader(page, open_book_query(env, alias, "&lang=fr&parallel=1&page=2"))
        page.locator("#kidsNotebookFloatingBar .quiz-pill").click()
        page.wait_for_selector("#antolinQuizDialog[open]", timeout=4000)
        title = page.locator("#antolinQuizTitle").inner_text()
        assert "Quiz Antolin" in title and ("Pages" in title or "Page" in title), title
        assert page.locator("#antolinQuizDialog button:has-text('Retour')").is_visible(), "Expected French 'Retour' button"
        cards = page.locator("#antolinQuizBody .antolin-question-card")
        assert cards.count() == 3
        body_txt = page.locator("#antolinQuizBody").inner_text()
        for q_text in expected_fr_qs:
            assert q_text in body_txt, f"Expected French question '{q_text}' in quiz body: {body_txt}"
        check_clean_page(rec, allow_baseline_puffin_error=env.baseline)
    finally:
        ctx.close()


@register_test("T3-09", 3, "F4", ("sardegna", "petit-prince"), False, "Pairwise F4xF8: Uppercase (a/A) + Grammar ON + Emma tier on even patch-top pages")
def t3_09(env: RunnerEnv) -> None:
    targets = active_book_targets(env)
    ctx, page, rec = env.new_session()
    try:
        alias, sid = targets[-1]
        pnum = 20 if sid == PETIT_PRINCE_ID else 2
        for lang in ("fr", "it", "de"):
            env.goto_reader(page, open_book_query(env, alias, f"&mode=emma&lang={lang}&page={pnum}"))
            set_grammar_mode(page, True)
            set_uppercase_mode(page, True)
            page.evaluate("() => window.fitKidsTextToPatch && fitKidsTextToPatch()")
            metrics = page.evaluate("() => window.__kidsTextFitMetrics()")
            assert_fit_metrics([m for m in metrics if m["page"] == pnum], f"T3-09 {alias}/{lang}")
        check_clean_page(rec, allow_baseline_puffin_error=env.baseline)
    finally:
        ctx.close()


@register_test("T3-10", 3, "F2", ("sardegna", "petit-prince"), True, "Pairwise F2xF9: Book Selector x PuffinLogin preserves seby tier across switch")
def t3_10(env: RunnerEnv) -> None:
    env.require_m1_m3(env.has_petit_prince_assets(), "books/petit-prince missing")
    ctx, page, rec = env.new_session()
    try:
        env.goto_reader(page, "?book=sardegna", dismiss_puffin_modal=False)
        check_clean_page(rec, strict_puffin_error=True)
        authenticate_puffin_profile(page, "seby", reload_url=f"{env.base_url}?book=sardegna")
        assert get_active_book_info(page)["mode"] == "seby"
        select_book_in_ui(page, "petit-prince")
        assert get_active_book_info(page)["mode"] == "seby"
        check_clean_page(rec, strict_puffin_error=True)
    finally:
        ctx.close()


@register_test("T3-11", 3, "F1", ("sardegna",), True, "Pairwise F1xF3: Legacy ?story=sardegna bookmark restores on ?book=sardegna")
def t3_11(env: RunnerEnv) -> None:
    if env.baseline:
        raise SkipTest("pre-M1/M3 baseline: ?book= and Bookmark UI not yet implemented")
    ctx, page, rec = env.new_session()
    try:
        env.goto_reader(page, "?story=sardegna&page=5")
        click_bookmark_button(page, "save")
        env.goto_reader(page, "?book=sardegna&page=1")
        click_bookmark_button(page, "resume")
        assert get_active_book_info(page)["pages"] == [5, 6]
        check_clean_page(rec)
    finally:
        ctx.close()


@register_test("T3-12", 3, "F11", ("sardegna", "petit-prince"), False, "Pairwise F11xF6xF7: Audio Invariant x Parallel en-GB x Speed 0.88x")
def t3_12(env: RunnerEnv) -> None:
    targets = active_book_targets(env)
    ctx, page, rec = env.new_session()
    try:
        env.goto_reader(page, open_book_query(env, targets[0][0], "&lang=fr&parallel=1"))
        ensure_settings_popover(page, True)
        page.locator("#kidsSettingsPopover button[onclick='setKidsSpeedStep(1)']").click()
        ensure_settings_popover(page, False)
        rec.clear()
        page.locator("#kidsNotebookFloatingBar .listen-pill").first.click()
        page.wait_for_timeout(180)
        assert any("fr_" in u or "/fr" in u for u in rec.audio_requests), f"Expected FR studio audio request: {rec.audio_requests}"
        rec.clear()
        page.evaluate("() => { window.__kosTtsCalls = []; }")
        page.locator("#kidsNotebookFloatingBar .listen-pill").nth(1).click()
        page.wait_for_timeout(120)
        calls = page.evaluate("() => window.__kosTtsCalls")
        assert calls and calls[-1]["lang"] == "en-GB" and calls[-1]["rate"] < 0.95, calls
        assert not rec.audio_requests, f"EN right page must fetch zero audio files: {rec.audio_requests}"
        check_clean_page(rec, allow_baseline_puffin_error=env.baseline)
    finally:
        ctx.close()


@register_test("T3-13", 3, "F12", ("sardegna", "petit-prince"), False, "Pairwise F12xF3xF1: Save P9 bookmark -> /books/ resume badge -> restore P9 -> /books/?book= redirect", requires_m5=True)
def t3_13(env: RunnerEnv) -> None:
    env.require_m5(env.has_bookshelf(), "books/index.html missing")
    ctx, page, rec = env.new_session()
    try:
        env.goto_reader(page, "?book=sardegna&page=9&mode=ale&lang=de")
        click_bookmark_button(page, "save")

        goto_bookshelf(page, env, "/books/")
        cards = inspect_bookshelf_cards(page)
        assert "sardegna" in cards and cards["sardegna"]["resumeHits"], cards
        assert any("9" in h["text"] or "page=9" in h["href"] for h in cards["sardegna"]["resumeHits"]), cards["sardegna"]

        click_bookshelf_target(page, "sardegna", prefer_resume=True)
        page.wait_for_selector(".kids-sentence-box", timeout=10000)
        page.wait_for_timeout(140)
        info = get_active_book_info(page)
        assert info["storyId"] == SARDEGNA_ID and info["pages"] == [9, 10], info

        goto_bookshelf(page, env, "/books/?book=sardegna&mode=ale&page=3", wait_fonts=False)
        page.wait_for_url(lambda u: "/books" not in u.split("?", 1)[0], timeout=8000)
        page.wait_for_selector(".kids-sentence-box", timeout=10000)
        page.evaluate("() => document.fonts ? document.fonts.ready : Promise.resolve()")
        page.wait_for_timeout(140)
        info2 = get_active_book_info(page)
        assert "/books" not in page.url.split("?", 1)[0]
        assert info2["storyId"] == SARDEGNA_ID and info2["mode"] == "ale" and info2["pages"] == [3, 4], info2
        check_clean_page(rec)
    finally:
        ctx.close()


# ===========================================================================
# TIER 4: 7 Realistic Family Application Scenarios
# ===========================================================================

@register_test("T4-01", 4, "F4", ("petit-prince",), True, "Scenario 1: Seby (6y A2) Le Petit Prince reading, audio, IT switch, P2 quiz, P3-4 bookmark & resume")
def t4_01(env: RunnerEnv) -> None:
    env.require_m1_m3(env.has_petit_prince_assets(), "books/petit-prince missing")
    kb = load_book_json(PETIT_PRINCE_ID)
    expected_audio = kb["pages"][1]["levels"]["seby"]["fr"]
    ctx, page, rec = env.new_session()
    try:
        env.goto_reader(page, "?book=petit-prince", dismiss_puffin_modal=False)
        check_clean_page(rec, strict_puffin_error=True)
        authenticate_puffin_profile(page, "seby", reload_url=f"{env.base_url}?book=petit-prince")
        info = get_active_book_info(page)
        assert info["mode"] == "seby" and info["lang"] == "fr"

        rec.clear()
        page.locator("#kidsNotebookFloatingBar .listen-pill").first.click()
        page.wait_for_timeout(160)
        assert any(
            expected_audio["audio_mp3"] in u or expected_audio.get("audio_ogg", "") in u
            for u in rec.audio_requests
        ), f"Expected request for {expected_audio['audio_mp3']}, got {rec.audio_requests}"

        switch_book_lang(page, "it")
        page.locator("#kidsNotebookFloatingBar .quiz-pill").click()
        page.wait_for_selector("#antolinQuizDialog[open]", timeout=4000)
        for i, q in enumerate(kb["pages"][1]["questions"]["it"]):
            page.locator("#antolinQuizBody .antolin-question-card").nth(i).locator(".antolin-opt-btn").nth(q["correct"]).click()
        page.locator("#antolinQuizBody button.page-turn-btn.primary").click()
        page.wait_for_timeout(120)
        assert get_active_book_info(page)["pages"] == [3, 4]
        click_bookmark_button(page, "save")
        env.goto_reader(page, "?book=petit-prince&page=1", dismiss_puffin_modal=False)
        click_bookmark_button(page, "resume")
        assert get_active_book_info(page)["pages"] == [3, 4]
        check_clean_page(rec, strict_puffin_error=True)
    finally:
        ctx.close()


@register_test("T4-02", 4, "F8", ("petit-prince",), True, "Scenario 2: Ale (8y B1) DE separable verbs, 0.88x speed, word audio & DE<->EN Pari Pari")
def t4_02(env: RunnerEnv) -> None:
    env.require_m1_m3(env.has_petit_prince_assets(), "books/petit-prince missing")
    ctx, page, rec = env.new_session()
    try:
        kb = load_book_json(PETIT_PRINCE_ID)
        pnum = next(
            pg["page"] for pg in kb["pages"]
            if any(t.get("sep_group") for t in pg["levels"]["ale"]["de"]["tokens"])
        )
        env.goto_reader(page, f"?book=petit-prince&lang=de&page={pnum}", dismiss_puffin_modal=False)
        check_clean_page(rec, strict_puffin_error=True)
        authenticate_puffin_profile(page, "ale", reload_url=f"{env.base_url}?book=petit-prince&lang=de&page={pnum}")
        assert get_active_book_info(page)["mode"] == "ale"
        set_grammar_mode(page, True)
        page.locator("#openBookSpread .kw-sep-verb[data-sep-group]").first.hover()
        assert page.locator("#openBookSpread .sep-brother-hover").count() >= 2
        ensure_settings_popover(page, True)
        page.locator("#kidsSettingsPopover button[onclick='setKidsSpeedStep(1)']").click()
        ensure_settings_popover(page, False)

        # Play BOTH DE studio page audio AND a German word token at 0.88x speed
        rec.clear()
        page.locator("#kidsNotebookFloatingBar .listen-pill").first.click()
        page.wait_for_timeout(150)
        de_studio_rate = page.evaluate("() => document.getElementById('kidsStaticAudio')?.playbackRate")
        assert de_studio_rate < 0.90, f"Expected 0.88x DE studio rate < 0.90, got {de_studio_rate}"
        assert any("de_" in u or "/de" in u for u in rec.audio_requests), rec.audio_requests
        page.locator("#kidsNotebookFloatingBar .listen-pill").first.click()
        page.wait_for_timeout(60)

        rec.clear()
        word_tok = page.locator("#openBookSpread .kw-token[onclick*='assets/words_audio/de/']").first
        assert word_tok.count() > 0, "Expected DE word token with assets/words_audio/de/ audio"
        word_tok.click()
        page.wait_for_timeout(150)
        de_word_rate = page.evaluate("() => document.getElementById('kidsStaticAudio')?.playbackRate")
        assert de_word_rate < 0.90, f"Expected 0.88x DE word rate < 0.90, got {de_word_rate}"
        assert any("assets/words_audio/de/" in u for u in rec.audio_requests), rec.audio_requests

        set_parallel_mode(page, True)
        switch_translation_lang(page, "en")
        rec.clear()
        page.evaluate("() => { window.__kosTtsCalls = []; }")
        page.locator("#kidsNotebookFloatingBar .listen-pill").nth(1).click()
        page.wait_for_timeout(120)
        assert not rec.audio_requests
        calls = page.evaluate("() => window.__kosTtsCalls")
        assert calls and calls[-1]["lang"] == "en-GB"
        check_clean_page(rec, strict_puffin_error=True)
    finally:
        ctx.close()


@register_test("T4-03", 4, "F10", ("petit-prince",), True, "Scenario 3: Emma & Papino Riccardo B2/C1 Fox spread (P19-P20) + en_gloss + quiz + Dashboard")
def t4_03(env: RunnerEnv) -> None:
    env.require_m1_m3(env.has_petit_prince_assets(), "books/petit-prince missing")
    ctx, page, rec = env.new_session()
    try:
        env.goto_reader(page, "?book=petit-prince&page=19&lang=fr", dismiss_puffin_modal=False)
        check_clean_page(rec, strict_puffin_error=True)
        authenticate_puffin_profile(page, "riccardo", reload_url=f"{env.base_url}?book=petit-prince&page=19&lang=fr")
        assert get_active_book_info(page)["mode"] == "emma"
        assert page.locator("#openBookSpread .kw-token.kw-has-gloss .kw-gloss-popover").count() >= 1
        page.locator("#kidsNotebookFloatingBar .quiz-pill").click()
        page.wait_for_selector("#antolinQuizDialog[open]", timeout=4000)
        kb = load_book_json(PETIT_PRINCE_ID)
        for i, q in enumerate(kb["pages"][19]["questions"]["fr"]):
            page.locator("#antolinQuizBody .antolin-question-card").nth(i).locator(".antolin-opt-btn").nth(q["correct"]).click()
        page.locator("#antolinQuizDialog button:has-text('Retour')").click()
        page.evaluate("() => openAntolinDashboardModal()")
        page.wait_for_selector("#antolinDashDialog[open]", timeout=4000)
        page.wait_for_timeout(150)
        assert "Pag. 20" in page.locator("#antolinDashBody").inner_text()
        check_clean_page(rec, strict_puffin_error=True)
    finally:
        ctx.close()


@register_test("T4-04", 4, "F6", ("sardegna", "petit-prince"), False, "Scenario 4: Mamma Kate (emma + en-GB Base) cross-language IT<->EN and FR<->EN reading")
def t4_04(env: RunnerEnv) -> None:
    targets = active_book_targets(env)
    ctx, page, rec = env.new_session()
    try:
        alias, _ = targets[-1]
        q_nomode = re.sub(r"&mode=[^&]+", "", open_book_query(env, alias))
        if q_nomode == "?story=sardegna":
            q_nomode = "?tab=studio"
        env.goto_reader(page, q_nomode, dismiss_puffin_modal=False)
        check_clean_page(rec, strict_puffin_error=True)
        authenticate_puffin_profile(page, "kate", reload_url=f"{env.base_url}{q_nomode}")
        info = get_active_book_info(page)
        assert info["mode"] == "emma" and info["trLang"] == "en", info
        set_parallel_mode(page, True)
        for lang in ("it", "fr"):
            switch_book_lang(page, lang)
            assert get_active_book_info(page)["badges"] == [f"1 · {lang.upper()}", "1 · EN"]
            rec.clear()
            page.evaluate("() => { window.__kosTtsCalls = []; }")
            page.locator("#kidsNotebookFloatingBar .listen-pill").nth(1).click()
            page.wait_for_timeout(120)
            calls = page.evaluate("() => window.__kosTtsCalls")
            assert calls and calls[-1]["lang"] == "en-GB" and not rec.audio_requests
        check_clean_page(rec, strict_puffin_error=True)
    finally:
        ctx.close()


@register_test("T4-05", 4, "F1", ("sardegna", "petit-prince"), True, "Scenario 5: Legacy ?story=sardegna link compatibility + Book Selector switch to petit-prince")
def t4_05(env: RunnerEnv) -> None:
    env.require_m1_m3(env.has_petit_prince_assets(), "books/petit-prince missing")
    ctx, page, rec = env.new_session()
    try:
        env.goto_reader(page, "?story=sardegna&mode=ale&lang=it&page=5")
        check_clean_page(rec)
        info = get_active_book_info(page)
        assert info["storyId"] == SARDEGNA_ID and info["pages"] == [5, 6] and info["totalPages"] == 16
        select_book_in_ui(page, "petit-prince")
        info2 = get_active_book_info(page)
        assert info2["storyId"] == PETIT_PRINCE_ID and info2["totalPages"] == 26
        check_clean_page(rec)
    finally:
        ctx.close()


@register_test("T4-06", 4, "F3", ("sardegna", "petit-prince"), True, "Scenario 6: Cross-book dual bookmark & Offline/Airplane Mode continuity")
def t4_06(env: RunnerEnv) -> None:
    env.require_m1_m3(env.has_petit_prince_assets(), "books/petit-prince missing")
    ctx, page, rec = env.new_session()
    try:
        # 1. Load sardegna online at P11 and save first bookmark
        env.goto_reader(page, "?book=sardegna&page=11&lang=it", dismiss_puffin_modal=False)
        check_clean_page(rec, strict_puffin_error=True)
        click_bookmark_button(page, "save")

        # 2. Switch offline (no page.goto while offline!), authenticate offline, switch to petit-prince & advance to P13-P14
        ctx.set_offline(True)
        page.evaluate("() => window.PuffinLogin.loginAsGuest('OfflineFamily')")
        select_book_in_ui(page, "petit-prince")
        for _ in range(6):
            page.locator("#bookPageRight .kids-edge-nav-arrow.is-right-arrow").click()
            page.wait_for_timeout(70)
        assert get_active_book_info(page)["pages"] == [13, 14]
        click_bookmark_button(page, "save")
        check_clean_page(rec, allow_offline_console=True, strict_puffin_error=True)

        # 3. Restore network, reload bare index.html, enter Studio, and verify both bookmarks persist & resume
        ctx.set_offline(False)
        rec.clear()
        env.goto_reader(page, "", wait_selector="#openBookSpread:visible, #indexView:visible", dismiss_puffin_modal=False)
        page.locator("#tabsStrip button[data-tab='studio']").click()
        page.wait_for_selector(".kids-sentence-box", timeout=10000)

        bm = get_bookmarks_storage(page)
        assert isinstance(bm, dict), bm
        assert int(bm[SARDEGNA_ID]["page"]) in (11, 12) and int(bm[PETIT_PRINCE_ID]["page"]) in (13, 14), bm

        # Resume petit-prince bookmark -> [13, 14], then switch to sardegna & resume -> [11, 12]
        if get_active_book_info(page)["storyId"] != PETIT_PRINCE_ID:
            select_book_in_ui(page, "petit-prince")
        click_bookmark_button(page, "resume")
        assert get_active_book_info(page)["pages"] == [13, 14]
        select_book_in_ui(page, "sardegna")
        click_bookmark_button(page, "resume")
        assert get_active_book_info(page)["pages"] == [11, 12]
        check_clean_page(rec, strict_puffin_error=True)
    finally:
        ctx.close()


@register_test("T4-07", 4, "F12", ("sardegna", "petit-prince"), False, "Scenario 7: Family living-room bookshelf session (/books/?kid=sebastian&mode=seby -> Cala Gonone P5 bookmark -> back to /books/)", requires_m5=True)
def t4_07(env: RunnerEnv) -> None:
    import urllib.parse

    env.require_m5(env.has_bookshelf(), "books/index.html missing")
    ctx, page, rec = env.new_session()
    try:
        # 1. Open /books/?kid=sebastian&mode=seby and verify both illustrated cards
        goto_bookshelf(page, env, "/books/?kid=sebastian&mode=seby")
        check_clean_page(rec)
        cards = inspect_bookshelf_cards(page)
        assert "sardegna" in cards and "petit-prince" in cards, cards
        for bname in ("sardegna", "petit-prince"):
            c = cards[bname]
            assert c["titleRect"] is not None, c
            assert c["imgRect"]["top"] <= c["titleRect"]["top"] <= c["titleRect"]["bottom"] <= c["imgRect"]["top"] + c["imgRect"]["height"] * 0.28, c
            assert c["img"]["complete"] and c["img"]["naturalWidth"] > 0, c["img"]

        # 2. Launch Cala Gonone from the bookshelf card
        click_bookshelf_target(page, "sardegna")
        page.wait_for_selector(".kids-sentence-box", timeout=10000)
        page.wait_for_timeout(140)
        info = get_active_book_info(page)
        assert info["storyId"] == SARDEGNA_ID and info["mode"] == "seby" and info["pages"] == [1, 2], info

        # 3. Turn to P5-P6 and save bookmark
        for _ in range(2):
            page.locator("#bookPageRight .kids-edge-nav-arrow.is-right-arrow").click()
            page.wait_for_timeout(110)
        assert get_active_book_info(page)["pages"] == [5, 6]
        click_bookmark_button(page, "save")

        # 4. Return to /books/ via index.html's /books link
        find_and_click_books_link(page)
        page.wait_for_url(re.compile(r"/books/?(\?.*)?$"), timeout=8000)
        page.wait_for_load_state("networkidle")
        cards_back = inspect_bookshelf_cards(page)
        assert "sardegna" in cards_back and cards_back["sardegna"]["resumeHits"], cards_back
        assert any("5" in h["text"] or "6" in h["text"] or "page=5" in h["href"] or "page=6" in h["href"] for h in cards_back["sardegna"]["resumeHits"]), cards_back["sardegna"]

        # 5. Verify Le Petit Prince card is visible and ready
        pp_card = cards_back["petit-prince"]
        assert pp_card["img"]["complete"] and pp_card["img"]["naturalWidth"] > 0
        assert any(
            urllib.parse.parse_qs(urllib.parse.urlparse(l["absHref"]).query).get("book") == ["petit-prince"]
            for l in pp_card["links"]
        ), pp_card["links"]
        check_clean_page(rec)
    finally:
        ctx.close()


# ---------------------------------------------------------------------------
# CLI & Execution Driver
# ---------------------------------------------------------------------------
def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Opaque-box Playwright E2E test suite (Tiers 1-4) for Kids' Own Stories Multi-Book Reader."
    )
    p.add_argument(
        "--tier",
        choices=("1", "2", "3", "4", "all"),
        default="all",
        help="Run a specific tier (1..4) or all tiers (default: all).",
    )
    p.add_argument(
        "--book",
        choices=("sardegna", "petit-prince", "all"),
        default="all",
        help="Filter tests by target book scope (default: all).",
    )
    p.add_argument(
        "--feature",
        action="append",
        default=[],
        help="Filter by feature ID(s), e.g. --feature F1 --feature F6,F10.",
    )
    p.add_argument(
        "--baseline",
        action="store_true",
        help="Pre-M3/M5 opt-in mode: skips tests requiring unimplemented M1-M3 or M5 artifacts while running all baseline sardegna checks.",
    )
    p.add_argument(
        "--headed",
        action="store_true",
        help="Run Google Chrome in visible headed mode for debugging.",
    )
    p.add_argument(
        "--json-report",
        type=Path,
        default=None,
        help="Write structured pass/fail/skip JSON summary to PATH.",
    )
    p.add_argument(
        "--list",
        action="store_true",
        help="List all registered E2E test cases and exit without launching Chrome.",
    )
    return p


def parse_feature_filters(raw: list[str]) -> set[str]:
    out: set[str] = set()
    for item in raw:
        for tok in item.split(","):
            t = tok.strip().upper()
            if t:
                out.add(t)
    return out


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()
    feat_filter = parse_feature_filters(args.feature)

    selected = [
        t for t in TESTS
        if (args.tier == "all" or t.tier == int(args.tier))
        and (not feat_filter or t.feature in feat_filter)
        and (args.book == "all" or args.book in t.scope_books)
    ]

    if args.list:
        print(f"Registered E2E tests: {len(TESTS)} total, {len(selected)} selected")
        for t in selected:
            m_tag = "M5" if t.requires_m5 else ("M1-M3" if t.requires_m1_m3 else "BASE")
            print(f"  [T{t.tier}][{t.feature:<3}][{m_tag:<5}] {t.test_id:<8} ({','.join(t.scope_books)}) — {t.description}")
        return 0

    from playwright.sync_api import sync_playwright

    httpd, port = start_range_server(REPO_ROOT)
    base_origin = f"http://127.0.0.1:{port}"
    base_url = f"{base_origin}/index.html"
    env_holder: dict[str, Any] = {}
    results: list[dict[str, Any]] = []

    try:
        with sync_playwright() as p:
            launch_kwargs: dict[str, Any] = {"headless": not args.headed}
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
            try:
                env = RunnerEnv(browser, base_url, base_origin, args)
                env_holder["env"] = env

                print(
                    f"\n🧪 Kids' Own Stories Multi-Book E2E Suite | "
                    f"tier={args.tier} book={args.book} baseline={args.baseline} | "
                    f"selected={len(selected)}/{len(TESTS)}"
                )
                print("-" * 92)

                for spec in selected:
                    t0 = time.monotonic()
                    if args.baseline and spec.requires_m1_m3 and (
                        not env.has_petit_prince_assets() or not env.has_constitution()
                    ):
                        status = "SKIP"
                        detail = "pre-M1/M3 baseline"
                    elif args.baseline and spec.requires_m5 and not env.has_bookshelf():
                        status = "SKIP"
                        detail = "pre-M5 baseline"
                    else:
                        try:
                            spec.fn(env)
                            status = "PASS"
                            detail = ""
                        except SkipTest as sk:
                            status = "SKIP"
                            detail = str(sk)
                        except Exception as exc:
                            status = "FAIL"
                            detail = str(exc)

                    dur = round(time.monotonic() - t0, 2)
                    icon = "✅" if status == "PASS" else ("⏭️" if status == "SKIP" else "❌")
                    line = f"{icon} [T{spec.tier}][{spec.feature:<3}] {spec.test_id:<8} {status:<4} ({dur:4.2f}s) — {spec.description}"
                    if detail:
                        line += f"\n    ↳ {detail}"
                    print(line, flush=True)
                    results.append(
                        {
                            "id": spec.test_id,
                            "tier": spec.tier,
                            "feature": spec.feature,
                            "scope_books": list(spec.scope_books),
                            "requires_m1_m3": spec.requires_m1_m3,
                            "requires_m5": spec.requires_m5,
                            "status": status,
                            "duration_s": dur,
                            "detail": detail,
                        }
                    )
            finally:
                browser.close()
    finally:
        httpd.shutdown()
        httpd.server_close()

    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    skipped = sum(1 for r in results if r["status"] == "SKIP")

    print("-" * 92)
    print(f"Summary: PASS={passed}  FAIL={failed}  SKIP={skipped}  TOTAL={len(results)}")

    if args.json_report:
        args.json_report.parent.mkdir(parents=True, exist_ok=True)
        args.json_report.write_text(
            json.dumps(
                {
                    "summary": {"pass": passed, "fail": failed, "skip": skipped, "total": len(results)},
                    "results": results,
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    if failed > 0:
        return 1
    if not args.baseline and skipped > 0:
        print("❌ Strict mode failure: unexpected skipped test(s).", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
