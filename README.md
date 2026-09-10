# 🍷 Fortunata

An astrology-themed Discord bot for **Trimalchio's Dinner Party**. Built with
`discord.py`, hosted separately from your server (Railway by default — see
below), with its own SQLite database.

## Features

- **Verification gate.** New arrivals get an "Unverified" role and a panel
  with a button for each of the 12 Sun signs, plus a "Find My Sign" button
  that opens a dropdown of date ranges for anyone who doesn't know their
  sign offhand. Picking one assigns their Sun sign role and lets them into
  the rest of the server.
- **`/placements`** — a full natal chart. A modal asks for birth date, time
  (optional), and city. Fortunata geocodes the location, resolves its
  historical timezone, and calculates Sun, Moon, Mercury, Venus, Mars,
  Jupiter, Saturn, Uranus, Neptune, Pluto, and the Rising/Ascendant sign —
  handing out a role for every single one.
- **`/chinesezodiac`** — Chinese zodiac animal (Rat through Pig) *and* Wu
  Xing element (Wood/Fire/Earth/Metal/Water), correctly accounting for the
  Lunar New Year cutoff, each as its own role.
- **`/bloodtype`** — blood type personality astrology (A/B/AB/O), each with
  its own role.
- **`/profile`** — a shareable card summarizing everything Fortunata knows
  about you (or another member).
- **`/fortunata ...`** — admin commands to set up the verification panel,
  lock down the rest of the server from unverified members, bulk-create
  every role in advance, view config, and reset a member's data.

All of it is Trimalchio-themed in tone (see `utils/astrology.py`,
`utils/chinese.py`, `utils/blood.py` for the flavor text — edit freely).

## Project layout

```
bot.py                  entry point
config.py                loads .env / environment variables
utils/
  astrology.py            western zodiac sign data + date lookup
  chart.py                 geocoding + timezone + full natal chart (kerykeion)
  chinese.py               Chinese zodiac animal + element calculation
  blood.py                  blood type astrology data
  db.py                      SQLite persistence (aiosqlite)
  roles.py                   role naming + get-or-create helpers
cogs/
  verification.py          sun-sign verification gate
  placements.py              /placements full chart
  chinese_zodiac.py           /chinesezodiac
  blood_type.py                 /bloodtype
  profile.py                     /profile
  admin.py                        /fortunata setup & admin commands
```

## 1. Create the bot application

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications) → **New Application** → name it "Fortunata".
2. **Bot** tab → **Reset Token**, copy it (you'll put this in `.env` as `DISCORD_TOKEN`). Keep it secret — anyone with it can control the bot.
3. Still on the **Bot** tab, under **Privileged Gateway Intents**, turn on **Server Members Intent**. Fortunata needs this to manage roles on join and to look up members reliably. (Message Content Intent is *not* needed — everything is slash commands/buttons.)
4. **OAuth2 → URL Generator**:
   - Scopes: `bot`, `applications.commands`
   - Bot permissions: `Manage Roles`, `Send Messages`, `Embed Links`, `Read Message History`, `View Channels`, `Use Slash Commands` (also `Manage Channels` if you plan to use `/fortunata lockdown`)
   - Open the generated URL and invite the bot to your server.
5. In your server, drag the bot's role (Server Settings → Roles) **above** every role it will need to assign (all the zodiac/placement/Chinese/blood roles it creates, plus your Verified/Unverified roles). Discord bots can only manage roles positioned below their own highest role.

## 2. Run it locally first

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# edit .env: paste DISCORD_TOKEN, and (recommended while testing) your test
# server's ID as GUILD_ID so slash commands sync instantly instead of
# taking up to an hour globally
python bot.py
```

> **Note on dependencies:** `kerykeion` depends on `pyswisseph`, a compiled
> extension. Prebuilt wheels exist for common platforms (Linux/macOS/Windows,
> recent Python versions), so `pip install` should just work — but if your
> platform needs to build from source, install a C compiler first (on
> Debian/Ubuntu: `sudo apt install build-essential`). `LunarCalendar` has an
> optional dependency on `ephem`, also a compiled package with prebuilt
> wheels for most platforms.

In your test server, run `/fortunata setup` in the channel you want the
verification panel in, then try clicking a sign, then try `/placements`,
`/chinesezodiac`, `/bloodtype`, and `/profile`. Confirm role colors/names
look right before deploying.

## 3. Deploy to Railway

Railway hosts the bot as a background worker, completely separate from your
Discord server.

1. Push this project to a GitHub repo (`.env` is git-ignored — never commit it).
2. [Railway](https://railway.app) → **New Project** → **Deploy from GitHub repo** → pick the repo.
3. Railway will detect it as a Python app via Nixpacks (`requirements.txt` + `runtime.txt`) and use the `startCommand` in `railway.json` (`python bot.py`). If it doesn't pick that up automatically, set the service's **Start Command** manually to `python bot.py` in Settings → Deploy.
4. **Variables** tab → add:
   - `DISCORD_TOKEN` = your bot token
   - `GUILD_ID` = your server ID (optional but recommended — instant command sync instead of up to ~1 hour)
   - `DB_PATH` = `/data/fortunata.sqlite3`
5. **Add a Volume** (Settings → Volumes) mounted at `/data`, so the SQLite database (member birth data, verification status, etc.) survives redeploys instead of resetting every time Railway rebuilds the container.
6. Deploy. Check the **Deploy Logs** for `Fortunata is online as ...` to confirm it connected.

The included `Dockerfile` is there as a portable alternative if you ever
want to move off Railway to a plain VPS — build and run it there with
`docker build -t fortunata . && docker run -d --env-file .env -v fortunata_data:/app/data fortunata`.

## 4. Set up your server

Once the bot is online and invited:

1. `/fortunata setup channel:#verify` — posts the verification panel there, and creates `🍷 Verified` / `🔒 Unverified` roles if you don't pass your own.
2. *(Optional, recommended)* `/fortunata create-roles` — pre-creates every zodiac/placement/Chinese/blood role in advance, so you can reorder and recolor them in Server Settings → Roles before members start using the bot. (This can take a minute or two — it's creating well over a hundred roles.)
3. *(Optional)* `/fortunata lockdown` — hides every channel except the verification channel from anyone with the Unverified role, and reveals everything to Verified. If you'd rather manage channel permissions by hand, skip this and just set `@everyone` to deny **View Channel** on your main channels, with the Verified role allowing it (standard Discord verification-gate pattern).
4. Point new members at the verification channel — `/fortunata setup` already gives new joiners the Unverified role automatically and DMs them a pointer to it (if their DMs are open).

## Commands reference

| Command | Who | What it does |
|---|---|---|
| *(buttons in the verification panel)* | anyone | Claim Sun sign + get verified |
| `/placements` | anyone | Full natal chart from birth date/time/city, roles for all 10 planets + Rising |
| `/chinesezodiac` | anyone | Chinese zodiac animal + Five Element, from birth date |
| `/bloodtype` | anyone | Blood type astrology, pick from a dropdown |
| `/profile [member]` | anyone | Summary card of everything on file for a member |
| `/fortunata setup` | Manage Server | Post/move the verification panel |
| `/fortunata lockdown` | Manage Server | Hide non-verification channels from unverified members |
| `/fortunata create-roles` | Manage Server | Pre-create every role the bot uses |
| `/fortunata config` | Manage Server | Show current configuration |
| `/fortunata reset member:@user` | Manage Server | Wipe a member's stored data (and optionally their roles) |

## Notes

- **Birth data privacy.** Exact birth date/time/location are only ever shown
  back to the member themselves (`/placements` replies are private/ephemeral).
  `/profile` — which anyone can run on anyone — only ever shows sign names,
  never the raw birth details.
- **Geocoding.** Locations are looked up via OpenStreetMap's free Nominatim
  service (no API key needed) — it's rate-limited to be polite (about one
  request/second), which is more than enough for normal use. For a very
  high-traffic server, consider [running your own Nominatim instance](https://nominatim.org/release-docs/latest/admin/Installation/) or swapping in a paid geocoder in `utils/chart.py`.
  Ephemeris calculations happen locally via `kerykeion`/`pyswisseph` — no
  external chart API involved, no key needed there.
  Chinese New Year cutoff dates come from the `LunarCalendar` package
  (accurate for 1900–2100).
- **Role limits.** A Discord server allows up to 250 roles. With every
  feature in use (10 planets + Rising × 12 signs, 12 animals, 5 elements,
  4 blood types, plus Verified/Unverified) you'll land around 160 —
  comfortable headroom. If you want fewer roles, just don't run
  `/fortunata create-roles`; the bot only creates roles for placements
  someone actually claims.
- **Re-running commands** replaces a member's previous role in that category
  (e.g. re-running `/placements` swaps out their old Moon-sign role for the
  new one) rather than stacking duplicates.
- All astrology content here — Sun signs, Chinese zodiac, blood type — is
  presented for entertainment, in keeping with the dinner-party theme, not
  as scientific or medical claims.
