# Project Memory — Rose / Hutch Design (Russell Smith)

Auto-read by Cowork/Claude when working in a folder containing this file. Captures context
for two sister products so any new session (laptop or desktop) picks up without re-explaining.
Keep it updated + re-commit to both repos as things change.

Git identity for commits: user.name "Rose", user.email "accounting@hutch-design.com".
GitHub owner (personal, not an org): **rsmith1545**.
Deploy = `git push` to `main` (GitHub Pages auto-builds ~30–60s).
**GitHub token:** fine-grained PAT (REGENERATED July 2026) with access to BOTH repos,
Repository permission Contents: Read and write. The user provides it each session (grab from
their password manager). **Use it transiently only** — in the clone/push URL, scrub output with
`sed "s/$TOKEN/***/g"`, then `unset TOKEN`. NEVER write the token into any file or echo it.
If a Pages "deploy" step fails ("try again later") it's a transient GitHub hiccup — re-push or
Re-run failed jobs (an empty commit re-triggers).

------------------------------------------------------------
## Product 1 — Crown Your Champion (CYC)  [MATURE / LIVE]
------------------------------------------------------------
- Live: https://crownyourchampion.com · Repo: rsmith1545/crownyourchampion (GitHub Pages)
- Static PWA of 64-song music-bracket tournaments. Backend = Firebase Firestore + GA4.
- Identity: gold-on-dark, regal (distinct from SFS's neon).
- Status: 32 brackets live. Album "Best Album" vote = 32/32 fully covered (incl. Beyoncé
  Lemonade via per-song iTunes lookup). Previews baked from iTunes (permanent
  audio-ssl.itunes.apple.com m4a URLs; Deezer expires — never use).
- Note: CYC hub PWA manifest_hub.json has scope "/" — it claims the whole origin, which is why
  a second PWA can't install separately under crownyourchampion.com (the reason SFS got its own domain).

------------------------------------------------------------
## Product 2 — SuperFan Shuffle (SFS)  [ACTIVE BUILD]
------------------------------------------------------------
- Live: https://superfanshuffle.com · Repo: **rsmith1545/superfanshuffle** (GitHub Pages, OWN origin)
  · Domain via Namecheap DNS (apex A-records to GitHub Pages 185.199.108-111.153, www CNAME→rsmith1545.github.io).
- Install-to-play PWA "Heads Up"-style music party game. Phone on forehead: tilt DOWN = correct
  (green), tilt UP = pass (orange).
- Identity (LOCKED): NEON nightlife. Deep purple base, cyan + magenta neon. Logo two-tone
  "SUPERFAN"(cyan)/"SHUFFLE"(magenta) in a neon-tube frame. Tagline "Face the Music."
  Fonts: **Bebas Neue** (display) + **Barlow** (body). Western/gunslinger theme RETIRED.

### File structure (repo root = superfanshuffle.com root)
- index.html = neon STORE / home (domain opens here). play.html = the tilt game.
- manifest.webmanifest (display: fullscreen), sw.js (v2, network-first for docs so page updates
  show on relaunch), icon-192/512/512-maskable + apple-touch-icon (neon vinyl), CNAME, .nojekyll.
- Local ready copy also in this folder: ./SuperFanShuffle-site/ . CLAUDE.md committed to BOTH repos.

### Product model
- **Vault = an artist** (Taylor Swift, Gracie Abrams, Chappell Roan…), sold in Volumes (Vol.1…).
- Inside each vault = **4 games**: (1) Name That Tune, (2) Fill-in-the-Lyric, (3) Party Trivia
  (multiplayer/forehead), (4) Superfan Solo (single-player sit-down; likely needs a DIFFERENT
  interaction than forehead — no clue-giver to confirm; undecided). IP-safe by design: app never
  plays copyrighted audio / never shows a continuous copyrighted lyric run.
- Free taste: 5 questions per game, then unlock with payment.
- Pricing per vault: 1 game $1.99 · 2 games $2.99 · **all 4 $3.99** (NO 3-game tier: selecting 3 → all 4).
- Charts: Featured of the Week, Top 10 Overall / Pop / Rock / Hip-Hop.

### Current state (deployed + working)
- PWA installs cleanly on Android (own origin). Store: neon vault tiles (vinyl aesthetic),
  mode-picker w/ live tiered pricing, Install button (beforeinstallprompt) + iOS Add-to-Home hint.
  **Gracie Abrams tile = direct-launch into the game; all other vaults = mode-picker.**
- Tilt mechanic PROVEN on Android (accelerationIncludingGravity.z, orientation-agnostic).
  Direction is platform-aware: `DOWN_IS_GOOD = IS_IOS ? 1 : -1` (Android confirmed -1; iOS is a
  best-guess +1, flip that one value if reversed on a real iPhone).
- Game flow: Ready waits for portrait→landscape → pulsing "TIME TO FACE THE MUSIC" (fanfare) →
  pulsing 3-2-1 → the WHOLE rounded card SPRINGS in (translateX overshoot / spring); text is STATIC.
  Correct = bright-green card + glow (hero) + bell; Pass = orange + buzz; last-10s clock pulses +
  tick-tocks; buzzer → red "TIME'S UP" card → recap. Distinct Web-Audio sounds (no files):
  bell/pass-womp/countdown-beep/fanfare/clock-tick/buzzer.
- Visual: colored ROUNDED card floating on BLACK (black margin all sides), thick white/neon border.
- Fullscreen: manifest display:fullscreen PLUS `goFullscreen()` requestFullscreen on first tap
  (store) and Play tap (game) → hides Android status + nav bars. Landscape locked during play via
  screen.orientation.lock (installed PWA) with a CSS fallback (force-render landscape when portrait);
  released at the report card.
- Haptics: `buzz()` helper with beefed-up patterns (correct double-buzz, pass solid, time's-up alarm).
- ALL 4 "Try 5 free" currently launch the SAME generic tilt demo (placeholder songs). The 4 modes
  and real per-vault content are NOT built yet.

### iOS / cross-platform notes (test on a real iPhone)
- Tilt: direction sign may be reversed vs Android — DOWN_IS_GOOD set to +1 for iOS as a guess; confirm.
- Fullscreen: iOS has NO Fullscreen API — goFullscreen() safely no-ops. iOS status bar CANNOT be hidden
  in portrait (Apple limit; we use apple-mobile-web-app-status-bar-style=black-translucent so the neon
  flows under it). iPhone auto-hides the status bar in LANDSCAPE, so the game itself should be clean.
  No bottom n