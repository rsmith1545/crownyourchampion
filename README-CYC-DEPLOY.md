# CYC deploy — what this is and what it still needs

CYC has never had a push path. Every bracket so far went up through the GitHub
**web UI**, which only *adds* files, so replacing a bracket meant deleting the old
one by hand first. `memory.md` still lists git publishing as "planned", and the
Part B plan in `DEPLOY-billyjoel.md` (a fine-grained PAT) was never executed.

This closes that gap without a token.

## The two pieces

**`CYC-DEPLOY.bat`** — the SFS engine, retargeted. Same skeleton that shipped v353
twice today: find git, hard-sync a clone that lives outside Google Drive, copy the
staged files in, commit, push, park what shipped in `_sent\`.

One structural change, and it is the reason this is a separate file from
`SFS-DEPLOY.bat`: **CYC files live in subfolders.** SFS is flat at the repo root,
CYC is `/billyjoel/index.html`, `/dmb/index.html` and so on. A flat copy loop would
drop every bracket's `index.html` on top of the hub page. So the copy step is
`robocopy /E` over the whole tree, and **the outbox mirrors the repo layout** —
stage `billyjoel\index.html`, not `index.html`.

**`build-lib/configs/*.json`** — 66 build configs, one per bracket, in the
`harrystyles.json` schema that `build_bracket.py` already reads.

## Auth: no token, by design

`SFS-DEPLOY.bat` authenticates through Git Credential Manager — a browser sign-in
you did once. **GCM caches per host, not per repo.** Both repos live under
`rsmith1545`, so the `github.com` credential already on the machine should cover
`crownyourchampion` with no new prompt. If the push does fail, run the .bat by hand
once and the browser sign-in repairs it; the commit is already saved locally, so
nothing is lost.

A PAT is not needed and should not be pasted into a chat or written to a file.

## First run

1. Double-click `CYC-DEPLOY.bat`. On the first run it clones
   `rsmith1545/crownyourchampion` to `%USERPROFILE%\cyc-repo` — deliberately
   **outside** Google Drive, because a Drive-synced `.git` is what broke the old
   `SuperFanShuffle-github` folder.
2. It refuses to run with an empty outbox, so nothing happens by accident.
3. Every later run does `fetch` + `reset --hard origin/main` + `clean -fd` before
   copying anything in. The clone is re-mirrored from live every single time, so it
   **cannot** push stale content.

For hands-off deploys, register the watcher exactly as SFS does, with `/silent` and
a `_GO.txt` marker written last.

**Do not run watchers for both repos on the same machine's Drive folder unless the
outboxes are separate** — they are (`_sfs-outbox` and `_cyc-outbox`), so this is
safe, but `_running.lock` is per-outbox, not global.

## What the configs are, and are not

`songs[]` is the **only** field these files are authoritative for: ranks 1–64
(or 1–32) straight off the Cards tab of
`0. CYC Brackets Grid & SFS Cards 9.15.26.xlsx`, placed by the seeding rule read
off the shipped Billy Joel page —

    region = ((rank-1) mod 4) + 1        seed = floor((rank-1)/4) + 1

R1 top-left, R2 top-right, R3 bottom-left, R4 bottom-right. Sixteen seeds per
region at 64, eight at 32.

Everything marked `FROM_LIVE_PAGE` must be read out of that bracket's own
`index.html` in the clone at build time:

| field | why |
|---|---|
| `regions` | region names stay live by your instruction. Only 9 are known, from the pages in `build-kit`. ArtistList disagrees with the page on 6 of those 9 — do not use it as a source. |
| `slogan` | 28 exist in ArtistList, but ArtistList is demonstrably stale on region names, so verify against the page. |
| `albums` | `*-album-tracks.json` gives album *names* only. The config wants `[name, year]` pairs. |

**`slug_confirmed: false` on 51 of 66.** Only 15 slugs are proven by files in
`build-kit` (`billyjoel`, `ate`, `beatles`, `bonjovi`, `greenday`, `metallica`,
`rhcp`, `stones`, `foo`, `fthc`, `dmb`, `pearljam`, `springsteen`, `ccr`, `stp`).
The rest are guesses from the SFS vault ids. **Confirm every slug against the
clone's actual folder names before building** — a wrong slug writes a new folder
instead of updating a bracket.

Note the asset suffix can differ from the folder: Billy Joel is `/billyjoel/` but
ships `sw_bj.js` and `manifest_bj.json`.

## Building a bracket update

`build_bracket.py` takes `--config`, `--root` (the clone), and a `--reference`
bracket it copies structure from. For **updating an existing** bracket, point
`--reference` at that bracket's own slug and pass its own region names — then the
song list changes and nothing else does. That is what keeps the live region names,
slogan and albums intact.

It needs `songdb.json` at the clone root (audio previews). There is no copy in
`Crown Your Champion`, so expect it to come from the clone; missing entries fall
back rather than failing.

Then prove it: `python3 verify_tree.py %USERPROFILE%\cyc-repo`. Baseline is
**118/128 regions byte-identical**, with 10 known pre-existing drifts
(`ate`/`ledzeppelin`/`tompetty` mirror different regions; two escape apostrophes
differently). Do not "fix" those.

## After any bracket page changes

Three idempotent patches must re-run, per `memory.md`:

1. Open Graph / Twitter meta tags
2. the Cloudflare Web Analytics beacon
3. the share-card snippet

**All three inject before the LAST `</body>`, never the first.** A bracket page
contains a literal `</body></html>` inside a JS string; injecting at the first one
lands inside the main script, the literal `</script>` ends the script tag early,
and the bracket engine dies silently. Verify after injecting by extracting the
largest inline script and running `node --check` on it.

## Not done here

- No bracket page has been rebuilt. Nothing has been pushed to CYC.
- The song swaps are real: 8 of the 9 readable pages differ from the Cards page,
  **66 genuinely new songs**. The other 40 live brackets are unmeasured because no
  clone exists yet.
- 14 titles need censoring before any of this ships — see the Censoring tab of
  `CYC seeding - brackets 1 to 64 from the Cards page.xlsx`. The live pages do not
  censor at all; the Stones page still reads the uncensored title.
