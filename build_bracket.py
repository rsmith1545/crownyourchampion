#!/usr/bin/env python3
"""
Parameterized bracket generator for Crown Your Champion.

Clones a reference band bracket (e.g. stones/index.html) and swaps in a new
band's data + tokens, producing <slug>/index.html, sw_<slug>.js and
manifest_<slug>.json.

Usage:
    python3 build_bracket.py --config build-configs/queen.json \
        --reference stones --slug queen [--root /tmp/cyc]
"""

import argparse
import html
import json
import os
import re
import shutil
import sys

R1_ORDER = [(1, 16), (8, 9), (5, 12), (4, 13), (6, 11), (3, 14), (7, 10), (2, 15)]
REGION_PREFIXES = ["SP", "WP", "AL", "DC"]


def scurve(overall):
    line = (overall - 1) // 4
    pos = (overall - 1) % 4
    region_seed = line + 1
    region_idx = pos if line % 2 == 0 else 3 - pos
    return region_idx, region_seed


def norm_title(t):
    t = t.lower()
    t = t.replace("&", " and ")
    t = re.sub(r"\(.*?\)", " ", t)
    t = re.sub(r"\s+-\s+.*$", " ", t)
    t = t.replace("’", "'")
    t = re.sub(r"[^a-z0-9]", "", t)
    return t


def build_songdb_map(songdb_path, artist):
    with open(songdb_path, encoding="utf-8") as f:
        raw = json.load(f)
    rows = raw["songs"] if isinstance(raw, dict) else raw
    m = {}
    for r in rows:
        if r.get("artist", "").strip().lower() != artist.strip().lower():
            continue
        key = norm_title(r.get("song", ""))
        if key and key not in m:
            m[key] = {"total": r.get("total", 0), "live": r.get("live", 0)}
    return m


def build_song_data(cfg, songdb_map):
    songs = cfg["songs"]
    regions = cfg["regions"]
    assert len(songs) == 64, "config must have exactly 64 songs"
    assert len(regions) == 4, "config must have exactly 4 regions"

    entries = []
    matched = 0
    fallbacks = []

    for i, name in enumerate(songs):
        overall = i + 1
        ridx, rseed = scurve(overall)
        region = regions[ridx]
        hit = songdb_map.get(norm_title(name))
        if hit is not None:
            matched += 1
            spotify = hit["total"]
            live = hit["live"]
        else:
            spotify = 3_000_000_000 - overall * 20_000_000
            live = None
            fallbacks.append(name)
        entries.append({
            "name": name, "overall": overall, "region_idx": ridx,
            "region": region, "seed": rseed, "spotify": spotify, "_live": live,
        })

    have_live = [e for e in entries if e["_live"] is not None]
    have_live.sort(key=lambda e: e["_live"], reverse=True)
    for rank, e in enumerate(have_live, start=1):
        e["liveRank"] = rank
    mid = len(have_live) + 1
    for e in entries:
        if e["_live"] is None:
            e["liveRank"] = mid

    return entries, matched, fallbacks


def render_all_songs(entries):
    lines = ["const ALL_SONGS = ["]
    for e in entries:
        nm = e["name"].replace('\\', '\\\\').replace('"', '\\"')
        rg = e["region"].replace('"', '\\"')
        lines.append(
            f'  {{name:"{nm}", seed:{e["seed"]}, region:"{rg}", '
            f'era:"{rg}", spotify:{e["spotify"]}, liveRank:{e["liveRank"]}}},'
        )
    lines.append("];")
    return "\n".join(lines)


def render_region_card_r1(entries, region_idx, prefix):
    by_seed = {}
    for e in entries:
        if e["region_idx"] == region_idx:
            by_seed[e["seed"]] = e
    rows = []
    for i, (hi, lo) in enumerate(R1_ORDER, start=1):
        pid = f"{prefix}-R2-{i}"
        hn = html.escape(by_seed[hi]["name"], quote=True)
        ln = html.escape(by_seed[lo]["name"], quote=True)
        rows.append(
            f'<div class="matchup">'
            f'<div class="slot" onclick="pick(this,\'{pid}\')"><span class="seed">{hi}</span>{hn}</div>'
            f'<div class="slot" onclick="pick(this,\'{pid}\')"><span class="seed">{lo}</span>{ln}</div>'
            f'</div>'
        )
    return rows


def replace_all_songs_block(text, new_block):
    start = text.index("const ALL_SONGS = [")
    end = text.index("];", start) + 2
    return text[:start] + new_block + text[end:]


def replace_region_headers(text, ref_regions, new_regions):
    for old, new in zip(ref_regions, new_regions):
        text = text.replace(
            f'<div class="region-header">{html.escape(old)}</div>',
            f'<div class="region-header">{html.escape(new)}</div>',
        )
    return text


def replace_region_r1(text, entries, ref_regions):
    for ridx, prefix in enumerate(REGION_PREFIXES):
        new_rows = render_region_card_r1(entries, ridx, prefix)
        for i, (hi, lo) in enumerate(R1_ORDER, start=1):
            pid = f"{prefix}-R2-{i}"
            pat = re.compile(
                r'<div class="matchup"><div class="slot" onclick="pick\(this,\''
                + re.escape(pid)
                + r"'\)\"><span class=\"seed\">"
                + re.escape(str(hi))
                + r'</span>.*?</div></div>'
            )
            m = pat.search(text)
            if not m:
                raise RuntimeError(f"could not find round-1 matchup {pid} seed {hi}")
            text = text[: m.start()] + new_rows[i - 1] + text[m.end():]
    return text


def short_band(b):
    return re.sub(r"^The\s+", "", b)


def swap_tokens(text, ref, out):
    rb = ref["band"]; rslug = ref["slug"]
    ob = out["band"]; oslug = out["slug"]
    rbs = short_band(rb)   # "Rolling Stones"  (no leading "The")
    obs = short_band(ob)
    subs = [
        (f"<title>{rb} — Crown Your Champion", f"<title>{ob} — Crown Your Champion"),
        (f'content="{rb} — Crown Your Champion"', f'content="{ob} — Crown Your Champion"'),
        (f"Crown {rb}'s greatest song", f"Crown {ob}'s greatest song"),
        (f"Crown {rb}’s greatest song", f"Crown {ob}’s greatest song"),
        (f"crownyourchampion.com/{rslug}/", f"crownyourchampion.com/{oslug}/"),
        (f'href="./manifest_{rslug}.json"', f'href="./manifest_{oslug}.json"'),
        # Firestore collections + any stones_* code/comment references
        (f"{rslug}_leaderboard", f"{oslug}_leaderboard"),
        (f"{rslug}_brackets", f"{oslug}_brackets"),
        (f"{rslug}_albumvote", f"{oslug}_albumvote"),
        (f'data-poll="{rslug}"', f'data-poll="{oslug}"'),
        # per-band localStorage keys
        (f"{rslug}-madness-v1-picks", f"{oslug}-madness-v1-picks"),
        (f"{rslug}-user-email", f"{oslug}-user-email"),
        # window globals
        (f'window.CYC_BAND="{rb}"', f'window.CYC_BAND="{ob}"'),
        (f"window.CONCERT_ARTIST = '{rb}'", f"window.CONCERT_ARTIST = '{ob}'"),
        # champ label / credits / favorites use the SHORT band form ("no The")
        (f"Your {rbs} Champion", f"Your {obs} Champion"),
        (f"Not affiliated with or endorsed by {rb}.", f"Not affiliated with or endorsed by {ob}."),
        (f"your favorite {rbs} songs", f"your favorite {obs} songs"),
        # print card uses full band name
        (f'<p class="band">{rb}</p>', f'<p class="band">{ob}</p>'),
        # itunes lookup artist (full name)
        (f"var artist = '{rb} ';", f"var artist = '{ob} ';"),
        # share header uses SHORT band, uppercased
        (f"{rbs.upper()} MADNESS — MY BRACKET", f"{obs.upper()} MADNESS — MY BRACKET"),
        (f"Play the {rbs} bracket → crownyourchampion.com/{rslug}",
         f"Play the {obs} bracket → crownyourchampion.com/{oslug}"),
        # quiz-menu chip (full band)
        (f'href="/{rslug}/">{rb}</a>', f'href="/{oslug}/">{ob}</a>'),
        # album-vote title uses SHORT band
        (f"Best {rbs} Album?", f"Best {obs} Album?"),
        # service worker registration
        (f"register('./sw_{rslug}.js')", f"register('./sw_{oslug}.js')"),
        # itunes title-match regex uses SHORT band, lowercased (/rolling stones/i)
        (f"/{rbs.lower()}/i", f"/{obs.lower()}/i"),
    ]
    for a, b in subs:
        text = text.replace(a, b)
    return text


def swap_album_vote(text, albums):
    if not albums:
        return text
    new_list = "|".join(f"{name}::{year}" for name, year in albums)
    return re.sub(r'data-albums="[^"]*"', f'data-albums="{new_list}"', text)


def make_service_worker(ref_sw, ref_slug, out_slug):
    sw = ref_sw
    sw = sw.replace(f"crown-champion-{ref_slug}-v2", f"crown-champion-{out_slug}-v1")
    sw = sw.replace(f"crown-champion-{ref_slug}-v1", f"crown-champion-{out_slug}-v1")
    sw = sw.replace(f"manifest_{ref_slug}.json", f"manifest_{out_slug}.json")
    return sw


def make_manifest(ref_manifest, ref_band, ref_slug, out_band, out_slug):
    m = json.loads(ref_manifest)
    m["name"] = f"Crown Your Champion — {out_band} Madness"
    desc = m.get("description", "")
    # swap both full ("The Rolling Stones") and short ("Rolling Stones") forms
    desc = desc.replace(ref_band, out_band).replace(short_band(ref_band), short_band(out_band))
    m["description"] = desc.replace(ref_slug, out_slug)
    m["start_url"] = m.get("start_url", "./index.html").replace(ref_slug, out_slug)
    m["scope"] = m.get("scope", "./").replace(ref_slug, out_slug)
    return json.dumps(m, indent=2, ensure_ascii=False)


def build_celebrate_block(slogan):
    marker = "CROWN YOUR CHAMPION"
    idx = slogan.upper().rfind(marker)
    if idx != -1:
        main = slogan[:idx].strip().rstrip(".").strip()
    else:
        main = slogan.strip()
    main_esc = html.escape(main)
    return (
        '<div class="celebrate-text" id="celebrateText">\n'
        f'    <div class="ct-main">{main_esc}</div>\n'
        '    <div class="ct-cyc">Crown Your Champion</div>\n'
        '</div>'
    )


def replace_celebrate(text, new_block):
    pat = re.compile(
        r'<div class="celebrate-text" id="celebrateText">.*?</div>\s*</div>',
        re.DOTALL,
    )
    m = pat.search(text)
    if not m:
        raise RuntimeError("could not find #celebrateText block")
    return text[: m.start()] + new_block + text[m.end():]


QUEEN_ALBUMS = [
    ("Queen", "1973"), ("Queen II", "1974"), ("Sheer Heart Attack", "1974"),
    ("A Night at the Opera", "1975"), ("A Day at the Races", "1976"),
    ("News of the World", "1977"), ("Jazz", "1978"), ("The Game", "1980"),
    ("Flash Gordon", "1980"), ("Hot Space", "1982"), ("The Works", "1984"),
    ("A Kind of Magic", "1986"), ("The Miracle", "1989"), ("Innuendo", "1991"),
    ("Made in Heaven", "1995"),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--reference", default="stones")
    ap.add_argument("--slug", default=None)
    ap.add_argument("--root", default="/tmp/cyc")
    ap.add_argument("--ref-band", default="The Rolling Stones")
    ap.add_argument("--ref-regions", default="Hot Lips,Steel Wheels,Exile Outlaws,Dartford Station")
    ap.add_argument("--albums", default=None)
    args = ap.parse_args()

    root = args.root
    ref_slug = args.reference
    ref_band = args.ref_band
    ref_regions = [r.strip() for r in args.ref_regions.split(",")]

    with open(args.config, encoding="utf-8") as f:
        cfg = json.load(f)
    out_slug = args.slug or cfg["slug"]
    out_band = cfg["name"]
    out_regions = cfg["regions"]

    ref_dir = os.path.join(root, ref_slug)
    out_dir = os.path.join(root, out_slug)
    os.makedirs(out_dir, exist_ok=True)

    songdb_map = build_songdb_map(os.path.join(root, "songdb.json"), out_band)
    entries, matched, fallbacks = build_song_data(cfg, songdb_map)

    with open(os.path.join(ref_dir, "index.html"), encoding="utf-8") as f:
        text = f.read()

    text = replace_all_songs_block(text, render_all_songs(entries))
    text = replace_region_r1(text, entries, ref_regions)
    text = replace_region_headers(text, ref_regions, out_regions)
    for old, new in zip(ref_regions, out_regions):
        text = text.replace(f">{html.escape(old)} Winner<", f">{html.escape(new)} Winner<")

    ref = {"band": ref_band, "slug": ref_slug}
    out = {"band": out_band, "slug": out_slug}
    text = swap_tokens(text, ref, out)

    albums = None
    if args.albums:
        albums = [(p.split("::")[0], (p.split("::")[1] if "::" in p else ""))
                  for p in args.albums.split("|") if p.strip()]
    elif out_slug == "queen":
        albums = QUEEN_ALBUMS
    text = swap_album_vote(text, albums)

    text = replace_celebrate(text, build_celebrate_block(cfg["slogan"]))

    with open(os.path.join(out_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(text)

    with open(os.path.join(ref_dir, f"sw_{ref_slug}.js"), encoding="utf-8") as f:
        ref_sw = f.read()
    with open(os.path.join(out_dir, f"sw_{out_slug}.js"), "w", encoding="utf-8") as f:
        f.write(make_service_worker(ref_sw, ref_slug, out_slug))

    with open(os.path.join(ref_dir, f"manifest_{ref_slug}.json"), encoding="utf-8") as f:
        ref_manifest = f.read()
    with open(os.path.join(out_dir, f"manifest_{out_slug}.json"), "w", encoding="utf-8") as f:
        f.write(make_manifest(ref_manifest, ref_band, ref_slug, out_band, out_slug))

    for fname in ["crown.png", "cyc-logo.png"]:
        src = os.path.join(ref_dir, fname)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(out_dir, fname))

    print(f"[build] {out_band} -> {out_dir}")
    print(f"[build] songdb match: {matched}/64  (fallbacks: {len(fallbacks)})")
    if fallbacks:
        print("[build] fallback songs:", ", ".join(fallbacks))
    return 0


if __name__ == "__main__":
    sys.exit(main())
