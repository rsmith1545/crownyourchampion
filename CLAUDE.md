# Project Memory — Rose / Hutch Design (Russell Smith)

This file is auto-read by Cowork/Claude when working in this folder. It captures
context for two sister products so any new session (laptop or desktop) can pick up
without re-explaining. Keep it updated as things change.

Git identity for commits: user.name "Rose", user.email "accounting@hutch-design.com".
GitHub owner: **rsmith1545**. Deploy = `git push` to `main` (GitHub Pages auto-builds).
GitHub token (fine-grained PAT) covers BOTH repos with Contents: read/write — the user
provides it each session. **Use it transiently only** (in the clone/push URL, scrub with
`sed "s/$TOKEN/***/g"`, then `unset TOKEN`). NEVER write the token into any file or echo it.

------------------------------------------------------------
## Product 1 — Crown Your Champion (CYC)  [MATURE / LIVE]
------------------------------------------------------------
- Live: https://crownyourchampion.com  · Repo: rsmith1545/crownyourchampion (GitHub Pages)
- What it is: static PWA of 64-song music-bracket tournaments. Backend = Firebase Firestore + GA4.
- Identity: gold-on-dark, regal. (Distinct from SFS.)
- Status: 32 brackets live. Album "Best Album" vote complete = 32/32 brackets fully covered
  (incl. Beyoncé Lemonade via per-song iTunes lookup). Song previews baked from iTunes
  (permanent audio-ssl.itunes.apple.com m4a URLs; Deezer URLs expire — never use).
- Deploy: work in a clone (e.g. /tmp/cyc), git push main. Preview data lives in per-bracket
  preview-urls.json / album-tracks.json. Shared theme; generator clones a live bracket.
- Open/optional later: CYC could migrate hosting to Firebase (backend already Firestore).

------------------------------------------------------------
## Product 2 — SuperFan Shuffle (SFS)  [ACTIVE BUILD]
------------------------------------------------------------
- Live: https://superfanshuffle.com  · Repo: **rsmith1545/superfanshuffle** (GitHub Pages, own origin)
- What it is: install-to-play PWA "Heads Up"-style music party game. Phone on forehead,
  tilt DOWN = correct (green), tilt UP = pass (orange).
- Identity (locked): NEON nightlife. Deep purple base, cyan + magenta neon. Logo = two-tone
  "SUPERFAN" (cyan) / "SHUFFLE" (magenta) in a neon-tube frame. Tagline "Face the Music."
  Fonts: **Bebas Neue** (display) + **Barlow** (body) — same family as CYC for kinship.
  Western/gunslinger theme was RETIRED.

### File structure (repo root = superfanshuffle.com root)
- index.html   = neon STORE / home (vaults, featured, top-10 by genre). Domain opens here.
- play.html    = the tilt game (opens from store).
- manifest.webmanifest (display: fullscreen), sw.js (v2, network-first for docs),
  icon-192/512/512-maskable, apple-touch-icon (neon vinyl), CNAME, .nojekyll.
- Local ready-to-deploy copy also in this folder: ./SuperFanShuffle-site/

### Product model
- **Vault = an artist** (Taylor Swift, Gracie Abrams, Chappell Roan…), sold in Volumes (Vol.1…).
- Inside each vault are **4 games (modes)**:
  1. Name That Tune (human hums/describes; app never plays copyrighted audio — IP-safe)
  2. Fill-in-the-Lyric (fragmented lyric w/ blanks; fragmentation = gameplay + IP safeguard; 1 of 3 blanks scores)
  3. Party Trivia (multiplayer, forehead, party-pace)
  4. Superfan Solo (single-player, sit-down, deep/obscure — NOTE: this mode likely needs a
     DIFFERENT interaction than forehead, since there's no clue-giver to confirm; undecided)
- Free taste: 5 questions per game, then unlock with payment.
- Pricing (per vault): 1 game $1.99 · 2 games $2.99 · **all 4 $3.99** (NO 3-game tier — 3 selected = all 4).
- Charts: Featured of the Week, Top 10 Overall / Pop / Rock / Hip-Hop.

### Current state (what works today)
- Tilt mechanic PROVEN on Android. Uses accelerationIncludingGravity.z (orientation-agnostic).
  DOWN_IS_GOOD = -1 (Android sign). iOS may be reversed → add auto-detect when iOS tested.
- Flow: Ready screen waits for portrait→landscape → "TIME TO FACE THE MUSIC" (fanfare) → pulsing
  3-2-1 → whole rounded card SPRINGS in (overshoot); text static. Correct=green bell, Pass=orange buzz,
  last-10s clock pulses + tick-tock, buzzer → red "TIME'S UP" → recap. Distinct Web-Audio sounds (no files).
- Visual: colored ROUNDED card floating on BLACK (black margin all sides), thick white/neon border,
  landscape-locked during play, released at report card. Fullscreen PWA.
- Store: neon home w/ vault tiles (vinyl aesthetic), mode-picker w/ live pricing. Install button
  (beforeinstallprompt) + iOS hint. **Gracie Abrams tile = direct-launch to game; others = mode-picker.**
- All 4 "Try 5 free" currently launch the SAME generic tilt demo (placeholder songs) — modes &
  real vault content NOT built yet.

### Next steps (SFS "2B — define + build the game")
- Build the 4 modes as distinct experiences; decide Solo's sit-down interaction.
- Wire REAL per-vault content (e.g., a real Gracie Abrams deck) into a mode, end-to-end.
- Enforce the 5-question free limit + unlock.
- LATER (needs pro security/architecture review before building): accounts, payments
  (Apple/Google take 15–30% on in-app unlocks), Firestore for vaults/charts/progress → move to Firebase Hosting.

------------------------------------------------------------
## Working conventions
------------------------------------------------------------
- Deploy by pushing to the relevant repo's main (Pages auto-deploys ~30–60s). If a Pages
  "deploy" step fails ("try again later"), it's a transient GitHub hiccup — re-push or Re-run failed jobs.
- SFS SW is network-first for HTML, so page updates show on relaunch. Manifest changes need a
  PWA reinstall. Stale installed app → Site settings → Clear & reset to swap the service worker.
- Validate JS before deploy (node: run each <script> through `new Function`; ignore the Firebase
  ES-module import false-positive on CYC).
- Do NOT reproduce copyrighted lyrics/audio in the app (IP model relies on human clue-givers + fragmentation).
