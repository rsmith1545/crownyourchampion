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
- **Editions** = top-tab filter inside Store: **Music · Movies · TV**. Music is the only live edition;
  Movies + TV are scaffolded but **hidden behind a server-side Firebase flag** (editions.<id>.enabled)
  — flip to launch instantly, no App Store resubmit. Dev build uses GENERIC non-IP placeholders only
  ("Sample Vault A"). Never real movie/TV titles, even hidden (studio IP liability).
- **Nav:** bottom tabs = **My Vaults · Store** (state); editions = **top tabs inside Store** (content),
  never bottom. Pin a **Free/Seasonal strip** at the top of each edition.
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
  index.html load native.js and take the native path only when SFS.native is true; web behavior is unchanged behind guards.
- BUILD (needs a Mac + Xcode + Apple Developer acct $99/yr): `git checkout native-app` → `npm install` →
  `npm run ios:add` → `npm run ios:open` → in Xcode set signing Team, plug in iPhone, press Run. Own phone via cable
  (free Apple ID works but the app expires in 7 days; paid = 1yr + TestFlight). Share via **TestFlight** (up to 10k
  testers, no full review). Android later: `npm install @capacitor/android && npx cap add android` (buildable on Windows, $25 Google one-time).
- App Store gotchas: Guideline 4.2 (must feel like an app, not a bare web wrapper — our native features clear it);
  vault-unlock payments must use Apple In-App Purchase (**15% Small Business Program** / 30% otherwise) — decide the
  payments model before public launch. Add a proper app icon + splash.
- WORKFLOW: keep iterating gameplay / content / look on the WEB (fast loop: push → live ~60s, testable in any browser).
  Only go to Capacitor/Xcode to test native-only things (fullscreen, real rotation, haptics). When the game feels done,
  wrap + TestFlight. The native scaffold is fully guarded, so merging native-app → main is safe (no visible change to the
  live site) and keeps ONE codebase — offered, not yet done.
- Reference doc (local, not in repo): **SuperFanShuffle-Native-Wrapper-Guide.md** in the SFS folder.

------------------------------------------------------------
## Session log — July 5 2026 (iOS fixes + native scaffold)
------------------------------------------------------------
- Pushed to **main**: audio silent-switch unlock + safe-area centering + sw v3 (ca3ab59); screen wake lock (2d6cad6);
  #stage rotation refactor + rotated countdown screens + single motion prompt per session (c9f20ce).
- Pushed to **native-app** branch: full Capacitor scaffold (see section above).
- OPEN / needs device confirm: card centering after the #stage refactor (awaiting a fresh iPhone screenshot); iOS tilt
  direction (DOWN_IS_GOOD +1 guess).
- Reminder: repo is cloud-synced via OneDrive — the bash sandbox sometimes reads half-synced files. Work from a fresh
  /tmp clone and push (the reliable path); the Read tool sees the authoritative OneDrive copy.
