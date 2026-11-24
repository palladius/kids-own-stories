#!/usr/bin/env python3
"""
Local HTTP/1.1 development server on port 8088 with full HTTP Byte-Range (206 Partial Content)
support so Chrome/Safari <audio> and <video> elements can seek (currentTime = ...) instantly.
"""

from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import os
import re
import socket
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class RangeRequestHandler(SimpleHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def end_headers(self):
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def send_head(self):
        self._range_remaining = None
        path = self.translate_path(self.path)
        if os.path.isdir(path):
            # Normalize leading // to avoid protocol-relative Location redirects in urlsplit
            if self.path.startswith("//"):
                self.path = "/" + self.path.lstrip("/")
            return super().send_head()
        if not os.path.exists(path):
            self.send_error(404, "File not found")
            return None

        range_header = self.headers.get("Range")
        if not range_header:
            return super().send_head()

        m = re.match(r"bytes=(\d*)-(\d*)$", range_header.strip())
        if not m or (not m.group(1) and not m.group(2)):
            return super().send_head()

        f = open(path, "rb")
        fs = os.fstat(f.fileno())
        file_len = fs.st_size
        if not m.group(1):
            suffix_len = int(m.group(2))
            if suffix_len <= 0 or file_len == 0:
                f.close()
                self.send_response(416, "Requested Range Not Satisfiable")
                self.send_header("Content-Range", f"bytes */{file_len}")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return None
            start = max(0, file_len - suffix_len)
            end = file_len - 1
        else:
            start = int(m.group(1))
            end = int(m.group(2)) if m.group(2) else file_len - 1
            end = min(end, file_len - 1)

        if start >= file_len or start > end:
            f.close()
            self.send_response(416, "Requested Range Not Satisfiable")
            self.send_header("Content-Range", f"bytes */{file_len}")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return None

        length = end - start + 1
        ctype = self.guess_type(path)
        self.send_response(206, "Partial Content")
        self.send_header("Content-type", ctype)
        self.send_header("Content-Range", f"bytes {start}-{end}/{file_len}")
        self.send_header("Content-Length", str(length))
        self.send_header("Last-Modified", self.date_time_string(fs.st_mtime))
        self.end_headers()
        if self.command != "HEAD":
            f.seek(start)
            self._range_remaining = length
        return f

    def copyfile(self, source, outputfile):
        remaining = getattr(self, "_range_remaining", None)
        self._range_remaining = None
        try:
            if remaining is None:
                return super().copyfile(source, outputfile)
            bufsize = 64 * 1024
            while remaining > 0:
                chunk = source.read(min(bufsize, remaining))
                if not chunk:
                    break
                outputfile.write(chunk)
                remaining -= len(chunk)
        except (BrokenPipeError, ConnectionResetError):
            pass


class DualStackServer(ThreadingHTTPServer):
    address_family = socket.AF_INET6

    def server_bind(self):
        self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
        return super().server_bind()


if __name__ == "__main__":
    os.chdir(ROOT)
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8088
    server = DualStackServer(("::", port), RangeRequestHandler)
    print(f"Serving Kids' Own Stories on http://localhost:{port} (IPv4+IPv6 with HTTP 206 Range support)", flush=True)
    server.serve_forever()
