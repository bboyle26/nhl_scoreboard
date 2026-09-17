# Jumbotron 🏒 🏈

A full-screen, auto-refreshing **NHL + NFL** scoreboard built to run on a monitor — a basement jumbotron for game night. It shows live scores, period/quarter and clock, shots on goal, possession and down-and-distance, overtime and shootout states, finals, upcoming start times, records, broadcasts, and playoff series standings. Teams glow in their own colors, and the tiles size themselves to the screen: logos, names and scores scale together so a quiet night blows up to fill the board.

What the board will not do is shrink the tiles to nothing to cram a busy Sunday onto one screen. A tile has a floor — sized so a screenful shows about two and a half rows of them, which means it grows with your screen rather than shrinking with the slate. When the slate is longer than that, the board **sweeps**: it holds at the top, travels down at a walking pace, holds at the bottom and comes back up, over and over, so every game gets its turn at full size. A gold progress bar in the header shows where in the slate you are. There is no scrollbar and nothing to reach for — a 1080p screen runs a 40-game night at 69px scores in about 47 seconds a pass.

Games are grouped by the day they're actually played — today first, then upcoming, then the most recent finals — so an upcoming game is never mistaken for one happening right now.

## What's in this folder

| File | Purpose |
|------|---------|
| `nhl-jumbotron.html` | The scoreboard itself. The only file the browser loads. |
| `server.js` | Local server (Node) — serves the page and proxies both league APIs. |
| `server.py` | Local server (Python) — same thing, pick one. |
| `firebase.json` | Config for the hosted Firebase option. |
| `functions/index.js` | The API proxy as a Firebase Cloud Function. |
| `functions/package.json` | Dependencies for the Firebase function. |

You only need **one** way to run it. The local server is the simplest and needs no account. Firebase is for when you want it hosted on the internet.

> **Note:** the Firebase files in the table above are not in this folder — the local servers are what's actually here. If you want the hosted option, you'll need to create them; the proxy logic to copy is the `SOURCES` map and `/api/...` handler in `server.js`.

## Leagues

| League | Source | Served at |
|--------|--------|-----------|
| NHL | `api-web.nhle.com/v1/score/now` | `/api/nhl` |
| NFL | `site.api.espn.com/.../football/nfl/scoreboard` | `/api/nfl` |

Use the **ALL / NHL / NFL** buttons in the header to pick what's on the board. Your choice is remembered in the browser, so a dedicated screen comes back to the same view after a reboot. (`/api/score` still works and returns the NHL feed, so old bookmarks don't break.)

Each league is fetched independently — if one API is down, the board shows the other with a warning strip instead of going blank.

## Why a server is needed at all

Neither API sends CORS headers, so a browser refuses to read them directly — you'd get a CORS error. The fix is a tiny proxy: a server fetches the data (servers aren't subject to CORS) and hands it to the page from the same origin. Both run modes below do exactly this, so the same `nhl-jumbotron.html` works either way with no edits.

> Opening `nhl-jumbotron.html` directly as a `file://` URL will **not** work — there's no proxy there. Always go through one of the options below.

One quirk worth knowing if you touch the proxy code: **ESPN rejects unrecognized `User-Agent` headers with a 403.** The NFL request deliberately sends no `User-Agent` override and lets the runtime's default through. Setting a custom one there will break it.

---

## Option A — Run locally (no account, recommended for a basement display)

Keep `nhl-jumbotron.html` in the same folder as the server script.

### Using Node (needs Node 18 or newer)

```bash
node server.js
```

### Using Python (needs Python 3)

```bash
python3 server.py
```

Then open **http://localhost:3000** in a browser and click the **⛶ Fullscreen** button.

### Changing the port

If something else is using port 3000:

```bash
PORT=8080 node server.js
# or
PORT=8080 python3 server.py
```

Neither script installs anything — they use only what ships with Node or Python. Both cache each league's response for ~8 seconds so frequent refreshes stay light.

### Viewing from another device on your network

Find the host machine's local IP (e.g. `192.168.1.50`) and open `http://192.168.1.50:3000` from any device on the same Wi-Fi.

---

Your page then calls `/api/nhl` and `/api/nfl` on your Firebase domain, the function fetches the data behind the scenes, and there's no CORS error.

---

## Making it boot-ready for a dedicated screen

For a monitor that should just work after a power cycle, two optional touches:

### 1. Start the server automatically on boot (Linux / Raspberry Pi)

Create a systemd service at `/etc/systemd/system/jumbotron.service` (adjust the paths and user):

```ini
[Unit]
Description=Jumbotron
After=network-online.target
Wants=network-online.target

[Service]
ExecStart=/usr/bin/node /home/pi/jumbotron/server.js
WorkingDirectory=/home/pi/jumbotron
Restart=always
User=pi
Environment=PORT=3000

[Install]
WantedBy=multi-user.target
```

Then enable it:

```bash
sudo systemctl enable --now jumbotron
```

It will start on boot and restart itself if it ever crashes. (Swap the `ExecStart` line for `/usr/bin/python3 .../server.py` if you prefer the Python server.)

### 2. Launch the browser full-screen on boot (kiosk mode)

Chrome / Chromium can open straight into the board with no tabs or toolbars:

```bash
chromium-browser --kiosk --noerrdialogs --disable-infobars http://localhost:3000
```

On a Raspberry Pi running the desktop, add that line to your autostart so it opens after login.

---

## Tweaks

All of these live in `nhl-jumbotron.html`:

- **Refresh speed** — in the `scheduleNext` function. Default is every 10s when a game is live, 30s otherwise.
- **Tile size** — `TILES_DEEP` at the top of the fit engine is the one knob that matters: roughly how many rows of tiles a screenful should show. Lower it for bigger tiles and a longer sweep, raise it for smaller tiles and less travel. `MAX_U` caps how large a quiet night may blow up to (1.5), and `MIN_U` is the hard floor on any screen.
- **Sweep pace** — `SWEEP_PXPS` (65 pixels a second) and `SWEEP_HOLD` (4s at each end), in the auto-sweep section. A sweep that feels rushed wants a lower `SWEEP_PXPS`; one that keeps you waiting for the bottom of the slate wants a higher one, or a higher `TILES_DEEP`.
- **NHL team colors** — the `NHL_COLORS` map near the top of the script. NFL colors come from ESPN's feed automatically; `accentColor` lightens the near-black ones (Raiders, Steelers) so they stay visible on a dark screen.
- **Adding a league** — add an entry to `SOURCES` in both the page and your server, then write a `normalize<League>()` that returns the same shape the renderer uses (`start`, `state`, `label`, `clock`, `away`/`home`, `venue`, `note`, `mid`, `meta`).
- **Endpoints** — the board calls `/api/nhl` and `/api/nfl`; the proxy decides where those point. No need to touch the league URLs in the page.

## Troubleshooting

- **"Connection Lost" on screen** — the page can't reach its proxy. Confirm the server is running (or the Firebase function is deployed) and that you opened `http://localhost:3000`, not the HTML file directly.
- **A warning strip at the top of the board** — one league's feed failed; the other is still live. It clears itself on the next successful refresh.
- **"NO GAMES SCHEDULED"** — the normal off-season / off-day state for whichever leagues are selected.
- **The board keeps moving on its own** — that's the sweep, and the gold `AUTO` bar in the header says so. It only runs when the slate is taller than the screen. To stop it and go back to squeezing everything into one view, raise `TILES_DEEP` until the board fits.
- **NFL feed returns 403** — something is sending a custom `User-Agent` to ESPN. Remove it.
- **Port already in use** — start with a different `PORT` as shown above.
