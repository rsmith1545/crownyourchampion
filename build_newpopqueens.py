#!/usr/bin/env python3
"""
Wrapper generator for the "New Pop Queens" special bracket.

Unlike a standard bracket (which places 64 flat songs via an S-curve), this
bracket assigns regions EXPLICITLY: each config song object carries its own
region ("Region 1".."Region 4") and region-seed (1-16). Region index is
(region number - 1); region_names[region_idx] is the display label.

songdb spotify/live are joined per-artist (each region = one artist) by
normalized title. liveRank is computed by ranking all 64 by songdb `live` desc.

Reuses helpers + token/album/manifest/sw plumbing from build_bracket.py.
"""

import html
import json
import os
import shutil
import sys

import build_bracket as bb

ROOT = "/tmp/cyc"
REF_SLUG = "stones"
REF_BAND = "The Rolling Stones"
REF_REGIONS = ["Hot Lips", "Steel Wheels", "Exile Outlaws", "Dartford Station"]

# Artist name normalization: config uses "Billy Eilish"; songdb has "Billie Eilish".
ARTIST_FIX = {"Billy Eilish": "Billie Eilish"}

NEWPOPQUEENS_ALBUMS = [
    ("When We All Fall Asleep, Where Do We Go?", "2019"),
    ("Happier Than Ever", "2021"),
    ("Hit Me Hard and Soft", "2024"),
    ("SOUR", "2021"),
    ("GUTS", "2023"),
    ("emails i can't send", "2022"),
    ("Short n' Sweet", "2024"),
    ("Good Riddance", "2023"),
    ("The Secret of Us", "2024"),
]


def build_artist_songdb_maps(songdb_path, artists):
    """Return {artist: {norm_title: {total, live}}} for the given artists."""
    with open(songdb_path, encoding="utf-8") as f:
        raw = json.load(f)
    rows = raw["songs"] if isinstance(raw, dict) else raw
    maps = {a: {} for a in artists}
    for r in rows:
        a = r.get("artist", "").strip()
        if a not in maps:
            continue
        key = bb.norm_title(r.get("song", ""))
        if key and key not in maps[a]:
            maps[a][key] = {"total": r.get("total", 0), "live": r.get("live", 0)}
    return maps


def build_song_data_explicit(cfg):
    songs = cfg["songs"]
    region_names = cfg["region_names"]
    assert len(songs) == 64, "config must have exactly 64 songs"
    assert len(region_names) == 4, "config must have exactly 4 region_names"

    # canonical artist per song
    artists = sorted({ARTIST_FIX.get(s["artist"].strip(), s["artist"].strip())
                      for s in songs})
    maps = build_artist_songdb_maps(os.path.join(ROOT, "songdb.json"), artists)

    entries = []
    matched = 0
    fallbacks = []

    for s in songs:
        artist = ARTIST_FIX.get(s["artist"].strip(), s["artist"].strip())
        region_num = int(s["region"].split()[1])   # "Region 1" -> 1
        ridx = region_num - 1
        rseed = int(s["seed"])
        region_label = region_names[ridx]
        name = s["song"]

        hit = maps[artist].get(bb.norm_title(name))
        if hit is not None:
            matched += 1
            spotify = hit["total"]
            live = hit["live"]
        else:
            # deterministic fallback based on ridx/seed so ordering is stable
            spotify = 3_000_000_000 - (ridx * 16 + rseed) * 20_000_000
            live = None
            fallbacks.append(f"{artist} - {name}")

        entries.append({
            "name": name,
            "overall": ridx * 16 + rseed,
            "region_idx": ridx,
            "region": region_label,
            "seed": rseed,
            "spotify": spotify,
            "_live": live,
        })

    # liveRank across all 64 by songdb live desc; missing -> mid rank
    have_live = [e for e in entries if e["_live"] is not None]
    have_live.sort(key=lambda e: e["_live"], reverse=True)
    for rank, e in enumerate(have_live, start=1):
        e["liveRank"] = rank
    mid = len(have_live) + 1
    for e in entries:
        if e["_live"] is None:
            e["liveRank"] = mid

    return entries, matched, fallbacks


def main():
    cfg_path = os.path.join(ROOT, "build-configs", "newpopqueens.json")
    with open(cfg_path, encoding="utf-8") as f:
        cfg = json.load(f)

    out_slug = cfg["slug"]
    out_band = cfg["name"]
    out_regions = cfg["region_names"]

    ref_dir = os.path.join(ROOT, REF_SLUG)
    out_dir = os.path.join(ROOT, out_slug)
    os.makedirs(out_dir, exist_ok=True)

    entries, matched, fallbacks = build_song_data_explicit(cfg)

    with open(os.path.join(ref_dir, "index.html"), encoding="utf-8") as f:
        text = f.read()

    text = bb.replace_all_songs_block(text, bb.render_all_songs(entries))
    text = bb.replace_region_r1(text, entries, REF_REGIONS)
    text = bb.replace_region_headers(text, REF_REGIONS, out_regions)
    for old, new in zip(REF_REGIONS, out_regions):
        text = text.replace(f">{html.escape(old)} Winner<", f">{html.escape(new)} Winner<")

    ref = {"band": REF_BAND, "slug": REF_SLUG}
    out = {"band": out_band, "slug": out_slug}
    text = bb.swap_tokens(text, ref, out)

    text = bb.swap_album_vote(text, NEWPOPQUEENS_ALBUMS)
    text = bb.replace_celebrate(text, bb.build_celebrate_block(cfg["slogan"]))

    with open(os.path.join(out_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(text)

    with open(os.path.join(ref_dir, f"sw_{REF_SLUG}.js"), encoding="utf-8") as f:
        ref_sw = f.read()
    with open(os.path.join(out_dir, f"sw_{out_slug}.js"), "w", encoding="utf-8") as f:
        f.write(bb.make_service_worker(ref_sw, REF_SLUG, out_slug))

    with open(os.path.join(ref_dir, f"manifest_{REF_SLUG}.json"), encoding="utf-8") as f:
        ref_manifest = f.read()
    with open(os.path.join(out_dir, f"manifest_{out_slug}.json"), "w", encoding="utf-8") as f:
        f.write(bb.make_manifest(ref_manifest, REF_BAND, REF_SLUG, out_band, out_slug))

    for fname in ["crown.png", "cyc-logo.png"]:
        src = os.path.join(ref_dir, fname)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(out_dir, fname))

    print(f"[build] {out_band} -> {out_dir}")
    print(f"[build] songdb match: {matched}/64  (fallbacks: {len(fallbacks)})")
    if fallbacks:
        print("[build] fallback songs:")
        for fb in fallbacks:
            print("   -", fb)
    return 0


if __name__ == "__main__":
    sys.exit(main())
