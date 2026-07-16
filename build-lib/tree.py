"""Bracket tree emitter — the ONE place that knows what a CYC bracket looks like.

A region with N seeds collapses N -> N/2 -> ... -> 1. Round ids are R2, R3, R4 ...
with the final winner always called WIN. So:
    64 songs = 16 seeds/region -> ids R2(8) R3(4) R4(2) WIN(1)   [4 matchup cols]
    32 songs =  8 seeds/region -> ids R2(4) R3(2)       WIN(1)   [3 matchup cols]
The R4 tier simply does not exist at 32. Everything downstream (f1 = Final Four,
Championship) is size-independent.
"""
import html, math

REGION_PREFIXES = ["SP", "WP", "AL", "DC"]

# S-curve first-round pairings, by seeds-per-region
R1_ORDERS = {
    16: [(1,16),(8,9),(5,12),(4,13),(6,11),(3,14),(7,10),(2,15)],
     8: [(1,8),(4,5),(3,6),(2,7)],
}

def seeds_per_region(size):   return size // 4
def r1_order(size):           return R1_ORDERS[seeds_per_region(size)]

def round_ids(size):
    """['R2','R3','R4','WIN'] for 64;  ['R2','R3','WIN'] for 32."""
    spr = seeds_per_region(size)
    levels = int(math.log2(spr))                 # 4 for 16 seeds, 3 for 8
    return [f"R{i+2}" for i in range(levels-1)] + ["WIN"]

def matchup_counts(size):
    """[8,4,2,1] for 64;  [4,2,1] for 32 — matchups per column."""
    spr = seeds_per_region(size)
    n, out = spr // 2, []
    while n >= 1:
        out.append(n); n //= 2
    return out

# each region winner feeds its own Final Four slot
FINAL_SLOT = {"SP": "f1", "WP": "f2", "AL": "f3", "DC": "f4"}

# the two right-hand regions are mirrored so the tree reads inward (NCAA layout)
ROW_STYLE = {
    "SP": '<div class="bracket-row">',
    "WP": '<div class="bracket-row">',
    "AL": '<div class="bracket-row" style="flex-direction: row-reverse;">',
    "DC": '<div class="bracket-row" style="flex-direction: row-reverse;">',
}

def render_region(prefix, size, by_seed, esc=True):
    """Emit the <div class="bracket-row"> block for one region.
    by_seed: {seed_number: song_name}. Returns a string with exact live indentation."""
    ids   = round_ids(size)
    counts= matchup_counts(size)
    L=[]
    A=lambda n,s: L.append(" "*n + s)
    A(0, ROW_STYLE[prefix])
    for k, cnt in enumerate(counts):
        A(16, '<div class="round-col">')
        for i in range(1, cnt+1):
            tgt = f"{prefix}-{ids[k]}-{i}" if ids[k] != "WIN" else f"{prefix}-WIN"
            if k == 0:                                  # seeded songs
                hi, lo = r1_order(size)[i-1]
                hn = html.escape(by_seed[hi], quote=True) if esc else by_seed[hi]
                ln = html.escape(by_seed[lo], quote=True) if esc else by_seed[lo]
                A(20, f'<div class="matchup">'
                      f'<div class="slot" onclick="pick(this,\'{tgt}\')">'
                      f'<span class="seed">{hi}</span>{hn}</div>'
                      f'<div class="slot" onclick="pick(this,\'{tgt}\')">'
                      f'<span class="seed">{lo}</span>{ln}</div></div>')
            else:                                       # empty advance slots
                p = ids[k-1]
                a, b = f"{prefix}-{p}-{i*2-1}", f"{prefix}-{p}-{i*2}"
                A(20, f'<div class="matchup">'
                      f'<div class="slot empty" id="{a}" onclick="pick(this,\'{tgt}\')">--</div>'
                      f'<div class="slot empty" id="{b}" onclick="pick(this,\'{tgt}\')">--</div></div>')
        A(16, '</div>')
    # final display column: the region winner feeds the Final Four (f1)
    A(16, '<div class="round-col">')
    A(20, f'<div class="matchup"><div class="slot empty" id="{prefix}-WIN" '
          f'onclick="pick(this,\'{FINAL_SLOT[prefix]}\')">--</div></div>')
    A(16, '</div>')
    A(12, '</div>')
    return "\n".join(L)
