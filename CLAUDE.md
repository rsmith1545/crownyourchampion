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
- Status: **49 brackets live** (32 hand-built + 17 generated). Album vote = **49/49**.
  Previews baked from iTunes (permanent audio-ssl.itunes.apple.com m4a URLs; Deezer expires — never use).
- Note: CYC hub PWA manifest_hub.json has scope "/" — it claims the whole origin, which is why
  a second PWA can't install separately under crownyourchampion.com (the reason SFS got its own domain).

### CYC data model — the traps (learned the hard way, July 17 2026)
- **roster.json is the source of truth (49)** but every bracket page embeds a COPY as
  `var CYC_ROSTER`. It feeds `cycNextData()` = the post-crown "What's Next?" pick, NOT the
  All-Brackets menu (that's 49 hardcoded `.qm-chip`s on every page — it was never broken).
  Adding a bracket = re-sync the embedded copy or new brackets never get suggested. Will drift
  again; the durable fix is fetching roster.json at runtime.
- **17 older bracket pages have NO CYC_ROSTER.** They use a hardcoded `NEXT = {picks:[...]}` with
  2 hand-picked neighbours (rhcp → Foo, Pearl Jam). Editorial, not stale. They'll never suggest a
  new bracket — decide separately.
- **`pick()` reads `innerText`** to advance a winner and writes it to the next slot AND Firebase.
  Any CSS that changes rendered text (clamp/truncate) risks writing a TRUNCATED title to real data.
  Verified: `-webkit-line-clamp` does NOT change innerText. Still — test before shipping.
- **The title CANNOT be wrapped in a span.** `pick()` does `target.innerText = text`, which replaces
  the target's children with a bare text node — any wrapper dies on the first advance, precisely in
  the R2/Final-Four boxes that overflow.
- **`.round-col` is `justify-content:space-around`** → gaps are LEFTOVER space. Oversized boxes eat
  them. "Round 2 has no gap" is a SYMPTOM of box overflow, not its own bug.
- **Region panels** are `.venue-gorge/spac/westpalm/camden` — DMB venue names on all 49, because
  everything was cloned from the DMB template. They are decoration with NO meaning (chips are all
  gold; there is no legend). Now uniform `rgba(56,96,72,.46)` ("Oyster Bay", renders #16242a) on 48.
  **DMB is deliberately excluded** — its panels are real venue PHOTOS (bg-gorge.jpg etc). Its regions
  ARE those venues. Don't flatten it.
- **Two `</head>` in bracket pages** (one inside a JS string). Inject late CSS as a
  `<style id="cyc-*">` after the last `</style>` — the file's own convention.
- **Blurbs must never mention seeding/streams.** Rose killed it ("streamed by who? not our
  audience"). A 2-line clamp was HIDING the tail on 30 of 51 homepage tiles; widening to 3 lines
  re-exposed it. All 51 cleaned July 17.

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
- manifest.webmanifest (display: fullscreen), sw.js (v3, network-first for docs + only caches OK responses so a bad deploy can't
  white-screen the app; page updates show on relaunch), icon-192/512/512-maskable + apple-touch-icon (neon vinyl), CNAME, .nojekyll.
- Local ready copy also in this folder: ./SuperFanShuffle-site/ . CLAUDE.md committed to BOTH repos.

### Product model (UPDATED per home-screen spec July 2026 — retires the old 4-games/tiered model)
- **Vault = an artist** (Taylor Swift, Gracie Abrams…). SFS is **ONE mixed game per vault** —
  songs + lyrics + lore all shuffled together (NOT 4 separate games; don't count/​reveal modes).
- Monetization: **5 free questions, then $0.99 to unlock the rest.** This is the **inherited default
  behavior of the vault template** (not a per-vault toggle) — any artist added to Firebase later
  auto-inherits it. IP-safe: never plays copyrighted audio / never shows a continuous lyric run.
- **NO counts anywhere on tiles** (no "Vol. 1", no "X / 250 shuffled", no "4 games inside", no pool
  size). A ceiling disappoints; only the free-preview FLOOR is allowed — the "5-question taste" pill.
- Keep free/seasonal tiles + the "3 days left" FOMO badge (the acquisition engine).
- **Editions** = top-tab filter: **Music · Film & TV · Sports** (TV folded into Film & TV). Music is the
  only live edition; Film&TV + Sports are **hidden behind a server-side Firebase flag** (editions.<id>.enabled),
  GENERIC non-IP placeholders only. Sports gets one LIVE free seed: **"The '85 Shuffle"**. DEV_PREVIEW=true
  renders the hidden tabs during build; set false for prod.
- **Per-edition ACCENT tint** (glows only, chrome stays dark, NEVER aqua=nav): Music=purple, Film&TV=gold/amber,
  Sports=yellow-orange. Chrome = dark header + dark bottom bar framing a **lighter-purple content zone**.
- **No "X days left" countdown** for now (no rotation calendar yet) — free tiles show just "FREE".
  Category shelf order (render only if ~3+ tiles; See All when >9): Best Of · Pop · Hip-Hop & R&B · Country ·
  Alt & Grunge · Classic Rock · Singer-Songwriter · Jam · Indie. Layout: Free This Week → Featured (whole card
  clickable, no button) → Recently Added → category shelves.
- **Nav:** bottom tabs = **Play · Explore · My Vaults** (Play=home, default; active tab glows aqua). Editions =
  top tabs inside Play. Never ship "Home/Store/My Brackets". Pin **Free This Week** at top of each edition.
- Charts (Music): Featured of the Week, Top in Pop / Rock / Hip-Hop.

### Current state (deployed + working)
- PWA installs cleanly on Android (own origin). Store: neon vault tiles (vinyl aesthetic),
  edition top-tabs (Music live; Movies/TV placeholder, flag-gated), pinned Free strip, bottom nav
  (My Vaults / Store), Install button + iOS hint. Free vaults direct-launch the 5-question taste;
  paid vaults open a sheet: "Play 5 free" + "Unlock the full vault · $0.99". No counts shown anywhere.
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

### iOS / cross-platform notes (tested on a real iPhone — updated July 5 2026)
- **Tilt:** direction sign may be reversed vs Android — DOWN_IS_GOOD set to +1 for iOS as a guess; confirm on device.
- **Fake-landscape rotation (iOS PWA):** an installed iOS PWA never physically rotates, so during play we rotate the
  content in CSS. As of the July 2026 fix the rotation lives on an OUTER `#stage` wrapper while the card's spring
  animation stays on `#app`. Previously BOTH were on `#app` and the transforms fought each other — that is what made
  the game card off-center with no margins. Countdown / "Face the Music" screens now also get `lock-ls` so the whole
  play flow is consistently landscape (not just the game). `#score`/`#hint` are position:absolute so they rotate with
  the panel. Android uses REAL rotation (the @media(orientation:portrait) rule just doesn't apply there).
- **Status bar CANNOT be hidden on iPhone** (Apple limit). iOS has no Fullscreen API — goFullscreen() no-ops on iPhone
  (works on Android). Because the iOS PWA stays physically portrait during play, the real status bar sits at the physical
  top and shows even in the rotated game (it does NOT auto-hide — the device isn't truly landscape). On the web the best
  we can do is black-translucent so the clock floats on black. TRUE fullscreen requires the native wrapper (see below).
- **Audio + iOS silent switch:** Web Audio is muted by the ring/silent switch. `unlockAudio()` (play.html) plays a
  near-silent looping media element on the Tap-to-Play / Play Again tap to shift the audio session to "playback" so the
  synth sounds come through. Best-effort — also tell users to check the physical ring switch.
- **Haptics:** iOS Safari IGNORES navigator.vibrate entirely — buzz() does nothing on the iPhone web build. Real haptics
  only come from the native wrapper.
- **Motion permission:** iOS requires the DeviceMotion/Orientation grant per fresh launch (security) — no web way to make
  it permanent. Guarded so it prompts once per session, not per round.
- **Screen sleep:** Wake Lock API (navigator.wakeLock) holds the screen on during a round (Android + iOS 16.4+),
  re-acquired on return to foreground, released at game end.

------------------------------------------------------------
## Native app path — Capacitor (cross-platform iOS + Android)  [SCAFFOLDED · branch: native-app]
------------------------------------------------------------
- WHY: the iPhone web PWA can't hide the status bar, has no real haptics, and relies on the fragile CSS fake-rotation.
  A Capacitor native shell around the SAME web game fixes all of it — true fullscreen, REAL OS landscape lock (deletes
  the #stage hack), real haptics, reliable keep-awake, remembered permissions. ONE codebase → both iOS and Android.
- Lives on branch **`native-app`** (main / live web PWA untouched). Files added there:
  package.json + capacitor.config.json (appId **com.hutchdesign.superfanshuffle**, webDir=www);
  native.js (feature-detected bridge: SFS.native + lockLandscape / hideStatusBar / keepAwake / haptic — all no-ops on
  the web); scripts/build-web.js (copies web assets into www/); README-NATIVE.md (the Mac/Xcode runbook). play.html +
  index.html load native.js and take the native path only when SFS.nati