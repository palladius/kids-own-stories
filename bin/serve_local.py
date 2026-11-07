#!/usr/bin/env python3
"""
Local HTTP/1.1 development server on port 8088 with full HTTP Byte-Range (206 Partial Content)
support so Chrome/Safari <audio> and <video> elements can seek (currentTime = ...) instantly.
"""

from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class RangeRequestHandler(SimpleHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def end_headers(self):
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

    def copyfile(self, source, outputfile):
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


if __name__ == "__main__":
    os.chdir(ROOT)
    server = ThreadingHTTPServer(("127.0.0.1", 8088), RangeRequestHandler)
    print("Serving Kids' Own Stories on http://127.0.0.1:8088 (with HTTP 206 Range support)", flush=True)
    server.serve_forever()
