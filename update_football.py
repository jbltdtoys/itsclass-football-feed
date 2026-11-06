#!/usr/bin/env python3
"""Refresh public fixture cache; never embed a private key in the Android APK."""
import datetime as dt, json, os, time, urllib.request
from zoneinfo import ZoneInfo

LEAGUES = {"4328":"Premier League", "4329":"Championship", "4396":"League One", "4397":"League Two", "4330":"Scottish Premiership"}
API = "https://www.thesportsdb.com/api/v1/json/123/eventsseason.php?id={}&s={}"
now = dt.datetime.now(ZoneInfo("Europe/London"))
season = f"{now.year if now.month >= 7 else now.year-1}-{now.year+1 if now.month >= 7 else now.year}"
fixtures = []
errors = []
for league_id, league_name in LEAGUES.items():
    try:
        req = urllib.request.Request(API.format(league_id, season), headers={"User-Agent":"ItsclassTV-FixtureCache/1.0"})
        with urllib.request.urlopen(req, timeout=25) as response: payload = json.load(response)
        for event in payload.get("events") or []:
            stamp = event.get("strTimestamp")
            if not stamp: continue
            try: kickoff = dt.datetime.fromisoformat(stamp.replace("Z", "+00:00"))
            except ValueError: continue
            if kickoff.tzinfo is None: kickoff = kickoff.replace(tzinfo=dt.timezone.utc)
            # Cache today and tomorrow to allow timezone boundaries and scheduled refreshes.
           if not (now.date() <= kickoff.astimezone(ZoneInfo("Europe/London")).date() <= now.date()+dt.timedelta(days=14)): continue
            fixtures.append({"id": str(event.get("idEvent") or ""), "league":league_name,
                "home":event.get("strHomeTeam") or "", "away":event.get("strAwayTeam") or "",
                "kickoff_utc":kickoff.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "broadcasters":[]})  # Add only independently verified broadcasters.
        print(league_name, "OK")
    except Exception as exc:
        errors.append(f"{league_name}: {exc}")
    time.sleep(3)  # Respect free API rate limits.
if errors:
    print("Some feeds failed:", "; ".join(errors))
    # Do not overwrite previously good data with an incomplete refresh.
    raise SystemExit(1)
output = {"updated_at_utc":dt.datetime.now(dt.timezone.utc).isoformat(), "season":season, "fixtures":fixtures}
os.makedirs("docs", exist_ok=True)
with open("docs/football.json", "w", encoding="utf-8") as file: json.dump(output, file, indent=2)
print("Cached", len(fixtures), "fixtures")
