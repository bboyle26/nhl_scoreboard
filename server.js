// Jumbotron — local server (no dependencies, needs Node 18+)
//
//   node server.js
//   then open http://localhost:3000
//
// Serves nhl-jumbotron.html and proxies the league APIs at /api/nhl and
// /api/nfl so the browser makes same-origin requests — which sidesteps CORS.

const http = require("http");
const fs = require("fs");
const path = require("path");

const PORT = process.env.PORT || 3000;
const HTML = path.join(__dirname, "nhl-jumbotron.html");

// ESPN's edge rejects unrecognized User-Agent strings with a 403, so the NFL
// request deliberately sends no User-Agent override and lets Node's default
// through. The NHL API is happy either way.
const SOURCES = {
  nhl: {
    url: "https://api-web.nhle.com/v1/score/now",
    headers: { "User-Agent": "jumbotron-local/1.0" },
  },
  nfl: {
    url: "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard",
    headers: {},
  },
};

const CACHE_MS = 8000;
const cache = new Map(); // league -> { at, body }

function sendJson(res, status, body) {
  res.writeHead(status, { "Content-Type": "application/json", "Cache-Control": "no-store" });
  res.end(body);
}

async function serveScores(res, league) {
  const hit = cache.get(league);
  if (hit && Date.now() - hit.at < CACHE_MS) return sendJson(res, 200, hit.body);

  try {
    const r = await fetch(SOURCES[league].url, { headers: SOURCES[league].headers });
    if (!r.ok) {
      return sendJson(res, 502, JSON.stringify({ error: league.toUpperCase() + " API returned " + r.status }));
    }
    const body = await r.text();
    cache.set(league, { at: Date.now(), body });
    sendJson(res, 200, body);
  } catch (e) {
    sendJson(res, 502, JSON.stringify({
      error: "Failed to reach the " + league.toUpperCase() + " API",
      detail: String(e),
    }));
  }
}

const server = http.createServer(async (req, res) => {
  const [pathname, query] = req.url.split("?");

  if (pathname.startsWith("/api/")) {
    // /api/nhl and /api/nfl; /api/score stays for older bookmarks (?league=nfl works too).
    let league = pathname.slice(5).toLowerCase();
    if (league === "score" || league === "scores") {
      league = new URLSearchParams(query || "").get("league") || "nhl";
    }
    if (!SOURCES[league]) {
      return sendJson(res, 404, JSON.stringify({ error: "Unknown league: " + league }));
    }
    return serveScores(res, league);
  }

  // Everything else serves the scoreboard page.
  fs.readFile(HTML, (err, data) => {
    if (err) {
      res.writeHead(404, { "Content-Type": "text/plain" });
      return res.end("nhl-jumbotron.html not found — keep it in the same folder as server.js");
    }
    res.writeHead(200, { "Content-Type": "text/html" });
    res.end(data);
  });
});

server.listen(PORT, () => {
  console.log(`\n  Jumbotron running at http://localhost:${PORT}`);
  console.log("  NHL + NFL scores. Open that in your browser and hit Fullscreen.\n");
});
