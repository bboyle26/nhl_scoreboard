#!/usr/bin/env python3
# Jumbotron — local server (Python 3, standard library only)
#
#   python3 server.py
#   then open http://localhost:3000
#
# Serves nhl-jumbotron.html and proxies the league APIs at /api/nhl and
# /api/nfl so the browser makes same-origin requests — which sidesteps CORS.

import http.server
import socketserver
import urllib.request
import urllib.parse
import json
import os
import time

PORT = int(os.environ.get("PORT", 3000))
HTML = os.path.join(os.path.dirname(os.path.abspath(__file__)), "nhl-jumbotron.html")

# ESPN's edge rejects unrecognized User-Agent strings with a 403, so the NFL
# request deliberately sends no User-Agent override and lets urllib's default
# through. The NHL API is happy either way.
SOURCES = {
    "nhl": (
        "https://api-web.nhle.com/v1/score/now",
        {"User-Agent": "jumbotron-local/1.0"},
    ),
    "nfl": (
        "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard",
        {},
    ),
}

CACHE_SECONDS = 8
_cache = {}  # league -> (fetched_at, body)


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        path, _, query = self.path.partition("?")
        if path.startswith("/api/"):
            # /api/nhl and /api/nfl; /api/score stays for older bookmarks.
            league = path[len("/api/"):].lower()
            if league in ("score", "scores"):
                league = urllib.parse.parse_qs(query).get("league", ["nhl"])[0].lower()
            if league not in SOURCES:
                self.send_json(404, {"error": "Unknown league: " + league})
            else:
                self.serve_scores(league)
        else:
            self.serve_html()

    def send_json(self, status, obj):
        body = json.dumps(obj).encode() if not isinstance(obj, (bytes, bytearray)) else obj
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def serve_scores(self, league):
        try:
            now = time.time()
            cached = _cache.get(league)
            if cached and now - cached[0] < CACHE_SECONDS:
                body = cached[1]
            else:
                url, headers = SOURCES[league]
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=10) as r:
                    body = r.read()
                _cache[league] = (now, body)
            self.send_json(200, body)
        except Exception:
            self.send_json(502, {"error": "Failed to reach the %s API" % league.upper()})

    def serve_html(self):
        try:
            with open(HTML, "rb") as f:
                data = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(data)
        except FileNotFoundError:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"nhl-jumbotron.html not found - keep it next to server.py")

    def log_message(self, *args):
        pass  # keep the console quiet


if __name__ == "__main__":
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"\n  Jumbotron running at http://localhost:{PORT}")
        print("  NHL + NFL scores. Open that in your browser and hit Fullscreen.\n")
        httpd.serve_forever()
