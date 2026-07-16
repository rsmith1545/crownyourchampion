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

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "build-lib"))
import tree  # the ONE place that knows what a bracket tree looks like

VALID_SIZES = (32, 64)
REGION_PREFIXES = tree.REGION_PREFIXES
R1_ORDER = tree.R1_ORDERS[16]   # kept for any legacy caller; size-aware code uses tree.r1_order()


# Quadrant strength rank -> DOM slot. The four region cards are emitted in DOM
# order SP, WP, AL, DC, which renders as top-left, bottom-left, top-right,
# bottom-right (AL/DC carry flex-direction:row-reverse -- see tree.ROW_STYLE).
#
# The v14 workbook's "Round 1 Logic" tab is the spec and is unambiguous:
#     Region 1 = Top Left | Region 2 = Top Right | Region 3 = Bottom Left | Region 4 = Bottom Right
# with overall seed 1->R1, 2->R2, 3->R3, 4->R4. So the #1 and #2 songs sit in
# OPPOSITE halves and can only meet in the final. Every hand-built bracket
# (ATE verified 63/63 against the sheet) already does this.
#
# The bug this fixes: quadrant k used to render into DOM slot k, which put the
# #2 song bottom-left -- the same half as #1 -- so they collided in the SEMI.
# Do NOT "fix" this by reordering REGION_PREFIXES: the emitter replaces the
# ridx-th DOM block, so prefix and slot are coupled and that would render AL's
# mirrored markup in the bottom-left slot.
QUAD_TO_SLOT = (0, 2, 1, 3)   # R1->TL, R2->TR, R3->BL, R4->BR


def scurve(overall):
    line = (overall - 1) // 4
    pos = (overall - 1) % 4
    region_seed = line + 1
    quadrant = pos if line % 2 == 0 else 3 - pos
    return QUAD_TO_SLOT[quadrant], region_seed


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
    size = int(cfg.get("size", 64))
    assert size in VALID_SIZES, f"size must be one of {VALID_SIZES}, got {size}"
    assert len(songs) == size, f"config says size={size} but has {len(songs)} songs"
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



def js1(v):
    """Escape a value for insertion into a JS '...' string literal."""
    return v.replace("\\", "\\\\").replace("'", "\\'")


def replace_region_headers(text, ref_regions, new_regions):
    """Rewrite every place a region NAME appears, not just the visible header.

    Three surfaces carry it and all three must move together, or a regenerated
    bracket ends up showing its own regions on screen while the share card and
    the venue watermarks still say the reference's:
      1. <div class="region-header">NAME</div>      -- visible header
      2. 'NAME': ['SP-R2-1', ...]                   -- share-card region->slot map
      3. .venue-*::after { content:"NAME"; }        -- background watermark
    """
    for old, new in zip(ref_regions, new_regions):
        eo, en = html.escape(old), html.escape(new)
        text = text.replace(f'<div class="region-header">{eo}</div>',
                            f'<div class="region-header">{en}</div>')
        # share-card map key (single-quoted JS string followed by the slot array)
        text = re.sub(r"'" + re.escape(old) + r"'(\s*:\s*\[')",
                      lambda m, en=new: "'" + en + "'" + m.group(1), text)
        # era-filter buttons — the onclick arg is a JS '...' literal
        text = text.replace(f"selectEra('{js1(old)}')\">{eo}</button>",
                            f"selectEra('{js1(new)}')\">{en}</button>")
        # JS string compares: 'X Winner' / "X Winner" (champion detection).
        # MUST escape: a region like "Harry's House" otherwise terminates the
        # literal early and breaks the entire <script> block.
        text = text.replace(f"'{js1(old)} Winner'", f"'{js1(new)} Winner'")
        text = text.replace(f'"{old} Winner"', f'"{new} Winner"')

    # The .venue-*::after watermark carries the REFERENCE's region names. Every
    # bracket built by this generator blanks it (19 of 32 live brackets are blank;
    # the 13 non-blank ones came from the older one-off build_*.py scripts).
    # Leaving it would print the reference's region names over the new bracket.
    text = re.sub(r'(\.venue-[a-z]+::after\s*\{ content:")[^"]*(";)', r'\1\2', text)
    return text


def replace_region_trees(text, entries, size):
    """Replace each region's ENTIRE <div class="bracket-row"> block with a freshly
    emitted tree. At 64 this reproduces the reference byte-for-byte (proven by
    build-lib/verify_tree.py). At 32 the R4 tier simply is not emitted — which is
    why we replace the whole block rather than patching R2 into an inherited one."""
    for ridx, prefix in enumerate(REGION_PREFIXES):
        by_seed = {}
        for e in entries:
            if e["region_idx"] == ridx:
                by_seed[e["seed"]] = e["name"]
        expect = tree.seeds_per_region(size)
        if len(by_seed) != expect:
            raise RuntimeError(f"{prefix}: got {len(by_seed)} seeds, expected {expect}")

        # locate this region's existing bracket-row block in the reference
        m = None
        for cand in re.finditer(r'<div class="bracket-row"[^>]*>', text):
            chunk = text[cand.start():]
            pm = re.search(r"pick\(this,'([A-Z]{2})-R2-1'\)", chunk[:4000])
            if pm and pm.group(1) == prefix:
                end = chunk.find("\n            </div>")
                if end < 0:
                    raise RuntimeError(f"{prefix}: could not find end of bracket-row")
                m = (cand.start(), cand.start() + end + len("\n            </div>"))
                break
        if m is None:
            raise RuntimeError(f"could not find bracket-row for region {prefix}")
        text = text[:m[0]] + tree.render_region(prefix, size, by_seed) + text[m[1]:]
    return text


def short_band(b):
    return re.sub(r"^The\s+", "", b)



# ---- depth-aware advance logic -------------------------------------------------
# The template's auto-fill walks the region tiers with HARDCODED loop bounds
# (i<=4 for R2->R3, i<=2 for R3->R4, then an explicit R4-1/R4-2 -> WIN).
# At size 32 there is no R4 tier at all, so those loops must derive from the
# tree shape instead. We inject CYC_ROUND_IDS/CYC_ROUND_COUNTS and replace both
# copies of the walk (fillEntireBracket + fillRemainingRounds) with one generic
# loop. At 64 it produces exactly the same sequence of advancePair() calls.

ADVANCE_A = """    regionPrefixes.forEach(p => {
        // R2 -> R3 (4 matchups -> but R2 has 8 slots feeding 4 R3... actually 8 R2 slots = 4 matchups)
        // R2-1&R2-2 -> R3-1, R2-3&R2-4 -> R3-2, R2-5&R2-6 -> R3-3, R2-7&R2-8 -> R3-4
        for (let i = 1; i <= 4; i++) {
            const a = document.getElementById(`${p}-R2-${i*2-1}`);
            const b = document.getElementById(`${p}-R2-${i*2}`);
            advancePair(a, b, scoreFn, randomTiebreak);
        }
    });
    regionPrefixes.forEach(p => {
        // R3-1&R3-2 -> R4-1, R3-3&R3-4 -> R4-2
        for (let i = 1; i <= 2; i++) {
            const a = document.getElementById(`${p}-R3-${i*2-1}`);
            const b = document.getElementById(`${p}-R3-${i*2}`);
            advancePair(a, b, scoreFn, randomTiebreak);
        }
    });
    regionPrefixes.forEach(p => {
        // R4-1&R4-2 -> WIN
        const a = document.getElementById(`${p}-R4-1`);
        const b = document.getElementById(`${p}-R4-2`);
        advancePair(a, b, scoreFn, randomTiebreak);
    });"""

ADVANCE_A_NEW = """    // Walk each tier: the slots of tier k-1 pair up and feed tier k.
    // Derived from CYC_ROUND_IDS so 32 (no R4 tier) and 64 share one path.
    for (let k = 1; k < CYC_ROUND_IDS.length; k++) {
        const src = CYC_ROUND_IDS[k - 1];
        const n = CYC_ROUND_COUNTS[k];
        regionPrefixes.forEach(p => {
            for (let i = 1; i <= n; i++) {
                const a = document.getElementById(`${p}-${src}-${i*2-1}`);
                const b = document.getElementById(`${p}-${src}-${i*2}`);
                advancePair(a, b, scoreFn, randomTiebreak);
            }
        });
    }"""

ADVANCE_B = """    regionPrefixes.forEach(p => {
        for (let i = 1; i <= 4; i++) {
            advancePair(document.getElementById(`${p}-R2-${i*2-1}`), document.getElementById(`${p}-R2-${i*2}`), scoreFn, randomTiebreak);
        }
    });
    regionPrefixes.forEach(p => {
        for (let i = 1; i <= 2; i++) {
            advancePair(document.getElementById(`${p}-R3-${i*2-1}`), document.getElementById(`${p}-R3-${i*2}`), scoreFn, randomTiebreak);
        }
    });
    regionPrefixes.forEach(p => {
        advancePair(document.getElementById(`${p}-R4-1`), document.getElementById(`${p}-R4-2`), scoreFn, randomTiebreak);
    });"""

ADVANCE_B_NEW = """    for (let k = 1; k < CYC_ROUND_IDS.length; k++) {
        const src = CYC_ROUND_IDS[k - 1];
        const n = CYC_ROUND_COUNTS[k];
        regionPrefixes.forEach(p => {
            for (let i = 1; i <= n; i++) {
                advancePair(document.getElementById(`${p}-${src}-${i*2-1}`), document.getElementById(`${p}-${src}-${i*2}`), scoreFn, randomTiebreak);
            }
        });
    }"""


def make_advance_depth_aware(text, size):
    ids = tree.round_ids(size)          # ['R2','R3','R4','WIN'] | ['R2','R3','WIN']
    counts = tree.matchup_counts(size)  # [8,4,2,1]              | [4,2,1]
    decl = ("    const CYC_ROUND_IDS = %s;\n    const CYC_ROUND_COUNTS = %s;\n"
            % (json.dumps(ids), json.dumps(counts)))

    hits = 0
    for old, new in ((ADVANCE_A, ADVANCE_A_NEW), (ADVANCE_B, ADVANCE_B_NEW)):
        if old in text:
            text = text.replace(old, new, 1)
            hits += 1
    if hits != 2:
        raise RuntimeError(
            "advance-logic blocks not found (%d/2) -- the template moved; "
            "re-sync ADVANCE_A/ADVANCE_B before building." % hits)

    # declare the constants at the top of each function that uses them
    for fname in ("function fillEntireBracket(scoreFn, randomTiebreak) {",
                  "function fillRemainingRounds(scoreFn, randomTiebreak) {"):
        if fname not in text:
            raise RuntimeError("could not find %r to declare round constants" % fname)
        text = text.replace(fname, fname + "\n" + decl, 1)
    return text


def rewrite_slot_tables(text, size):
    """ALL_IDS (save/restore) and the child->parent NEXT map are pure derivations of
    the tree shape but are written out longhand. Regenerate both for `size`, or a 32
    bracket carries R4 ids that no element on the page has."""
    ids, counts = tree.round_ids(size), tree.matchup_counts(size)

    # --- ALL_IDS ---------------------------------------------------------------
    m = re.search(r'const ALL_IDS = \[.*?\];', text, re.S)
    if not m:
        raise RuntimeError("ALL_IDS block not found")
    lines = ["const ALL_IDS = ["]
    for p in REGION_PREFIXES:
        for k, tier in enumerate(ids):
            if tier == "WIN":
                lines.append(f"    '{p}-WIN',")
            else:
                row = ",".join(f"'{p}-{tier}-{i}'" for i in range(1, counts[k] + 1))
                lines.append("    " + row + ",")
    lines.append("    'f1','f2','f3','f4','c1','c2'")
    lines.append("];")
    text = text[:m.start()] + "\n".join(lines) + text[m.end():]

    # --- child -> parent map ---------------------------------------------------
    # every slot in tier k-1 points at the tier-k slot it feeds; WIN points at f1..f4
    m = re.search(r"(\{\s*\n\s*'SP-R2-1':\s*'SP-R3-1',.*?\n\})", text, re.S)
    if not m:
        raise RuntimeError("child->parent NEXT map not found")
    out = ["{"]
    for p in REGION_PREFIXES:
        for k in range(1, len(ids)):
            src, dst = ids[k - 1], ids[k]
            for i in range(1, counts[k] + 1):
                a, b = i * 2 - 1, i * 2
                tgt = f"{p}-WIN" if dst == "WIN" else f"{p}-{dst}-{i}"
                out.append(f"    '{p}-{src}-{a}': '{tgt}', '{p}-{src}-{b}': '{tgt}',")
        out.append(f"    '{p}-WIN':  '{tree.FINAL_SLOT[p]}',")
    out.append("}")
    text = text[:m.start(1)] + "\n".join(out) + text[m.end(1):]
    return text


def rewrite_share_card(text, size, regions):
    """The share card holds THREE hardcoded four-tier structures: the region->slot
    map, roundLabels, and a chunks slicing with literal offsets. All three are
    derivations of the tree shape. At 32 the untouched version renders eight
    round-1 matchups for a bracket that has four."""
    ids, counts = tree.round_ids(size), tree.matchup_counts(size)

    # region -> ordered slot ids
    rows = []
    for p, rname in zip(REGION_PREFIXES, regions):
        slots = []
        for k, tier in enumerate(ids):
            if tier == "WIN":
                slots.append(f"'{p}-WIN'")
            else:
                slots += [f"'{p}-{tier}-{i}'" for i in range(1, counts[k] + 1)]
        rows.append("        '%s': [%s]," % (rname.replace("'", "\\'"), ",".join(slots)))
    m = re.search(r"    const regions = \{\n(?:.*?\n)*?    \};", text)
    if not m:
        raise RuntimeError("share-card regions map not found")
    text = text[:m.start()] + "    const regions = {\n" + "\n".join(rows) + "\n    };" + text[m.end():]

    # roundLabels: one per tier. tier k-1 has counts[k-1]*2 slots -> counts[k] winners
    labels = []
    for k, tier in enumerate(ids):
        if tier == "WIN":
            labels.append("Elite 8")          # live convention: the region-winner chunk
        else:
            labels.append("R%d Winners (%d)" % (k + 1, counts[k]))
    m = re.search(r"    const roundLabels = \[.*?\];", text, re.S)
    if not m:
        raise RuntimeError("roundLabels not found")
    text = (text[:m.start()] + "    const roundLabels = [" +
            ",".join("'%s'" % l for l in labels) + "];" + text[m.end():])

    # chunks: literal slice offsets over the slot list
    offs, acc = [], 0
    for k, tier in enumerate(ids):
        n = 1 if tier == "WIN" else counts[k]
        offs.append((acc, acc + n)); acc += n
    chunks = ",".join("ids.slice(%d,%d)" % (a, b) for a, b in offs)
    m = re.search(r"        const chunks = \[.*?\];", text, re.S)
    if not m:
        raise RuntimeError("chunks slicing not found")
    text = text[:m.start()] + "        const chunks = [" + chunks + "];" + text[m.end():]
    return text


def rewrite_size_constants(text, size):
    """Four more places hardcode 64. All are size derivations, none were caught by
    the tree/JS work because they are copy or arithmetic, not slot ids.

      * TOTAL_PICKS = 63      -> a 32 bracket is 31 picks (size-1)
      * "0 / 63" in the HTML  -> initial progress label
      * tg-stats / wt-stats   -> "64 Songs · 4 Regions · 1 Champion" tagline copy
                                 (SEPARATE from <div class="subtitle">, which is why
                                  the earlier subtitle fix missed it)
    """
    picks = size - 1                      # every song but the champion loses once
    text = re.sub(r'const TOTAL_PICKS = \d+;', f'const TOTAL_PICKS = {picks};', text)
    text = text.replace('id="progressCount">0 / 63<', f'id="progressCount">0 / {picks}<')
    text = re.sub(r'(<span class="(?:tg|wt)-stats">(?:&mdash; )?)64 Songs',
                  lambda m: m.group(1) + f'{size} Songs', text)
    return text


def fix_round_col_spacing(text, size):
    """`.bracket-row { height: 960px }` is hardcoded for 8 matchups in column one.
    At 32 there are 4, so the tree floats in ~half a card of dead space.

    Do NOT touch `justify-content: space-around` -- it is what makes each column
    center on its feeders automatically (R3-1 lands exactly between the R2-1/R2-2
    and R2-3/R2-4 pairs). Pinning column one to flex-start breaks that alignment.
    Halving the row height keeps the same geometry at half scale.

    Slot height is deliberately NOT locked. An earlier version pinned
    height/max-height to var(--slot-h) with overflow:hidden, reading "it
    shouldn't change the height of each selection" as "never grow". That was
    wrong twice over: the ask was for the same slot height as a 64 (which
    --slot-h already gives), and the clip hid the "Download on iTunes" button,
    an inline-block ::after on .cbb-inline that lives INSIDE the slot. The 64s
    set only min-height -- a floor -- so the card grows to fit it. Match that;
    a locked box and an in-flow button cannot both win.
    """
    if size >= 64:
        return text
    rows = 960 * size // 64          # 32 -> 480
    text = re.sub(r'(\.bracket-row\s*\{[^}]*?height:\s*)960px', r'\g<1>%dpx' % rows,
                  text, count=1)
    css = """
        /* --- %d-song bracket ------------------------------------------------
           Row height scaled to the matchup count; space-around still handles
           feeder alignment. Slot sizing inherited from the 64 (min-height only)
           so the iTunes buy button can expand its card. */
        .slot > span.seed { flex: 0 0 auto; }
""" % size
    return text.replace("</style>", css + "    </style>", 1)


def style_size_note(text):
    """The size note div ships with NO css -- it renders as an unstyled block and
    strands itself under the header. Give it the subtitle's visual weight so it
    reads as a caption on the song count rather than a system message.

    NOTE: placement is layout, not markup -- it already sits above .header-tagline
    in the DOM. If it still renders below, that is a positioning rule in the header
    and needs an eye on a real browser, not a grep."""
    css = """
        .subtitle-note {
            font-size: 10.5px;
            font-style: italic;
            letter-spacing: .3px;
            color: rgba(240,165,0,.72);
            margin-top: 2px;
            margin-bottom: 1px;
        }
        @media (max-width:1080px){ .subtitle-note { font-size: 9.5px; } }
"""
    return text.replace("</style>", css + "    </style>", 1)



def drop_live_mode(text, cfg):
    """Remove the "Most Played Live" auto-fill button.

    This is an EDITORIAL call, not a data check. The Beatles bracket omits it
    because setlist.fm coverage of the 1960s is not trustworthy -- the data
    exists, we just don't believe it. So it lives in the config as a decision:

        "no_live_data": true

    Also correct (for now) for any artist absent from songdb.json, because their
    liveRank is a synthetic constant and the button would silently produce
    meaningless order. Remove the flag once they have real setlist data.
    """
    if not cfg.get("no_live_data"):
        return text
    pat = r'\s*<button class="mode-btn mode-live"[^>]*>[^<]*</button>'
    new, n = re.subn(pat, "", text, count=1)
    if not n:
        print("[build] WARNING: no_live_data set but the Most Played Live button "
              "was not found -- markup may have changed")
    return new


def move_note_into_tagline(text):
    """RETIRED -- superseded by web_header_note(). This moved the note above
    .header-tagline, which is display:none on desktop, so it fixed nothing."""
    return text


def _dead_move_note(text):
    """The size note sits in .header-left with white-space:nowrap, which widens
    that block and shoves "Settle the debate" to the right of where it sits on a
    64. Move it out of the flow above the tagline instead, so the tagline keeps
    its normal position and the note reads as a caption on it."""
    m = re.search(r'\s*<div class="subtitle-note">.*?</div>', text)
    if not m:
        return text
    note = m.group(0).strip()
    text = text.replace(m.group(0), "", 1)
    # place it immediately BEFORE the tagline, inside the same wrapper
    tag = '<div class="header-tagline">'
    i = text.find(tag)
    if i < 0:
        return text
    return text[:i] + note + "\n        " + text[i:]


def web_header_note(text):
    """Put the size note ABOVE the tagline on desktop, without moving the tagline.

    Why the first two attempts failed -- worth recording, because the markup
    lies about the layout. On desktop .header-left is:
        display:flex; align-items:flex-end; gap:20px
    a HORIZONTAL row. .subtitle-note is a direct child of it, so it was a flex
    ITEM sitting between the logo and the tagline, shoving "Settle the debate"
    right by its own width + the 20px gap. Dropping white-space:nowrap only
    narrowed the shove. And moving the note above .header-tagline did nothing,
    because .header-tagline is display:none on desktop -- the tagline you can
    actually SEE is #cycWebTag, which the web-header JS builds at runtime and
    appends to .header-left.

    So: hide .subtitle-note on desktop and render the note as a block INSIDE
    #cycWebTag. That div is a block and .header-left is align-items:flex-end,
    so the note stacks above the tagline and the tagline's baseline does not
    move. Text is read from the DOM, so a bracket with no size_note emits no
    div. Mobile (<=1080) is a separate layout and keeps .subtitle-note as-is.
    """
    ok = True
    old = "  .site-header .subtitle, .site-header .header-tagline { display:none !important; }"
    new = ("  .site-header .subtitle, .site-header .header-tagline,\n"
           "  .site-header .subtitle-note { display:none !important; }")
    if old in text:
        text = text.replace(old, new, 1)
    else:
        print("[build] WARNING: desktop tagline-hide rule not found"); ok = False

    css = ("  #cycWebTag .wt-note { display:block; font-family:'Barlow Condensed',sans-serif;"
           " font-style:italic; font-size:23px; letter-spacing:.5px; line-height:1.1;"
           " color:rgba(240,165,0,.72); margin-bottom:1px; }\n")
    anchor = "  #cycWebTag { min-width:0;"
    i = text.find(anchor)
    if i >= 0:
        text = text[:i] + css + text[i:]
    else:
        print("[build] WARNING: #cycWebTag rule not found"); ok = False

    old_js = '      tag.innerHTML=\'<span class="wt-lead">Settle the debate: </span>\'+'
    new_js = ("      var nEl=document.querySelector('.site-header .subtitle-note');\n"
              "      var nTx=nEl?(nEl.textContent||'').trim():'';\n"
              "      tag.innerHTML=(nTx?'<div class=\"wt-note\">'+nTx+'</div>':'')+\n"
              "        '<span class=\"wt-lead\">Settle the debate: </span>'+")
    if old_js in text:
        text = text.replace(old_js, new_js, 1)
    else:
        print("[build] WARNING: cycWebTag innerHTML not found -- note NOT injected"); ok = False
    if not ok:
        print("[build] WARNING: web_header_note only partially applied")
    return text


def compact_console(text):
    """Trim the center console so more of Most-Crowned Champions clears the fold.

    .center-col is sticky with max-height:calc(100vh - sticky-top-h) and scrolls
    internally; Most-Crowned is its next sibling below .finals-card. So every px
    off the finals card lifts the leaderboard by one px.

    Only chrome is touched -- padding, gaps, empty-slot minimums, and the crown
    button. Deliberately NOT the .final-slot font: those carry song titles, and
    shrinking them would sell legibility to buy vertical space.
    """
    subs = [
        (".sf-pairs { display: grid; grid-template-columns: 1fr 1fr; grid-template-rows: minmax(40px, auto) auto minmax(40px, auto); gap: 8px; }",
         ".sf-pairs { display: grid; grid-template-columns: 1fr 1fr; grid-template-rows: minmax(30px, auto) auto minmax(30px, auto); gap: 6px; }"),
        ("display: grid; grid-template-rows: subgrid; grid-row: 1 / span 3; gap: 6px;",
         "display: grid; grid-template-rows: subgrid; grid-row: 1 / span 3; gap: 4px;"),
        ("border-radius: 4px; padding: 7px;",
         "border-radius: 4px; padding: 5px;"),
        ("display: block; width: 100%; margin-top: 8px;",
         "display: block; width: 100%; margin-top: 6px;"),
        ("padding: 13px 16px; border: 1px dashed #3a4150; border-radius: 9px;",
         "padding: 9px 16px; border: 1px dashed #3a4150; border-radius: 9px;"),
        ("font-family: 'Bebas Neue', sans-serif; font-size: 23px; letter-spacing: 2.5px;",
         "font-family: 'Bebas Neue', sans-serif; font-size: 20px; letter-spacing: 2.5px;"),
    ]
    for a, b in subs:
        if a in text:
            text = text.replace(a, b, 1)
        else:
            print("[build] WARNING: compact_console miss -> " + a[:58])
    return text


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
        # buy-bar compliance block: per-bracket artist for the runtime iTunes lookup.
        # Added after this generator was written -- without it every "Download on
        # iTunes" link searches for the REFERENCE artist.
        (f"var ART_DEFAULT = '{rb}';", f"var ART_DEFAULT = '{ob}';"),
        # share header uses SHORT band, uppercased
        (f"{rbs.upper()} MADNESS — MY BRACKET", f"{obs.upper()} MADNESS — MY BRACKET"),
        (f"Play the {rbs} bracket → crownyourchampion.com/{rslug}",
         f"Play the {obs} bracket → crownyourchampion.com/{oslug}"),
        # NOTE: deliberately NOT swapping the all-brackets menu chip
        #   (f'href="/{rslug}/">{rb}</a>', ...)
        # That menu lists EVERY bracket, so the reference's own chip is legitimate
        # content -- swapping it deletes the reference from the menu and creates a
        # duplicate of this bracket. New brackets need a chip ADDED to all pages
        # (see task #140), which is a separate propagation step, not a token swap.
        # album-vote title uses SHORT band
        (f"Best {rbs} Album?", f"Best {obs} Album?"),
        # service worker registration
        (f"register('./sw_{rslug}.js')", f"register('./sw_{oslug}.js')"),
        # itunes title-match regex uses SHORT band, lowercased (/rolling stones/i)
        (f"/{rbs.lower()}/i", f"/{obs.lower()}/i"),
    ]
    # concert-mode placeholder is per-artist prose ("e.g. Hyde Park 1969, Wembley 1990").
    # There is nothing to infer it from, so it comes from the config; if absent we
    # leave the reference's text rather than invent venues for the wrong band.
    ph = out.get("concert_placeholder")
    if ph:
        subs.append((f'placeholder="e.g. {ref.get("concert_placeholder","")}"',
                     f'placeholder="e.g. {ph}"'))
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
    size = int(cfg.get("size", 64))
    out_regions = cfg["regions"]

    ref_dir = os.path.join(root, ref_slug)
    out_dir = os.path.join(root, out_slug)
    os.makedirs(out_dir, exist_ok=True)

    songdb_map = build_songdb_map(os.path.join(root, "songdb.json"), out_band)
    entries, matched, fallbacks = build_song_data(cfg, songdb_map)

    with open(os.path.join(ref_dir, "index.html"), encoding="utf-8") as f:
        text = f.read()

    text = replace_all_songs_block(text, render_all_songs(entries))
    text = replace_region_trees(text, entries, size)
    text = make_advance_depth_aware(text, size)
    text = rewrite_slot_tables(text, size)
    text = rewrite_size_constants(text, size)
    text = fix_round_col_spacing(text, size)
    text = style_size_note(text)
    text = web_header_note(text)
    text = compact_console(text)
    text = drop_live_mode(text, cfg)
    text = replace_region_headers(text, ref_regions, out_regions)
    text = rewrite_share_card(text, size, out_regions)
    for old, new in zip(ref_regions, out_regions):
        text = text.replace(f">{html.escape(old)} Winner<", f">{html.escape(new)} Winner<")

    # subtitle + (32 only) the explainer line beneath it
    if size != 64:
        sub_old = '<div class="subtitle">64 Songs &middot; 4 Regions &middot; 1 Champion</div>'
        if sub_old not in text:
            sub_old = re.search(r'<div class="subtitle">64 Songs[^<]*</div>', text)
            sub_old = sub_old.group(0) if sub_old else None
        if sub_old:
            note = cfg.get("size_note", "Not enough songs for 64\u2026 yet")
            sub_new = (sub_old.replace("64 Songs", f"{size} Songs")
                       + f'\n            <div class="subtitle-note">{html.escape(note)}</div>')
            text = text.replace(sub_old, sub_new, 1)

    ref = {"band": ref_band, "slug": ref_slug}
    out = {"band": out_band, "slug": out_slug}
    text = swap_tokens(text, ref, out)

    # Best Album vote. Source order: --albums flag > config "albums" > hardcoded
    # queen special-case. Without one of these the vote silently keeps the
    # REFERENCE band's discography (Stones albums on a Harry Styles board).
    albums = None
    if args.albums:
        albums = [(p.split("::")[0], (p.split("::")[1] if "::" in p else ""))
                  for p in args.albums.split("|") if p.strip()]
    elif cfg.get("albums"):
        albums = [(a[0], a[1]) for a in cfg["albums"]]
    elif out_slug == "queen":
        albums = QUEEN_ALBUMS
    if not albums:
        print("[build] WARNING: no albums for %s -- Best Album vote will still show "
              "the reference band's albums" % out_slug)
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
