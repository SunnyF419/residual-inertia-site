# Residual Inertia homepage opening

The opening follows three ideas: **Observe → Research → Decide**. It uses the existing Paper / Ink palette, IBM Plex / Noto typography, and the exact geometry of `assets/brand/RI-symbol-reverse.svg`. Bars and the rising arc assemble beside restrained orbit lines, then the existing homepage headline appears and dissolves into the real homepage.

Visual reference: [LBEILC/RhineLabUI](https://github.com/LBEILC/RhineLabUI), specifically its typographic access sequence, geometric logo assembly, and welcome transition. This implementation is original DOM/CSS/JavaScript; it does not copy its source, footage, logos, fonts, audio, or game identity. It has no WebGL, animation package, or audio dependency.

## Visitor behavior

- Only `/` and `/en/` include the opening assets and dialog.
- 9.5 seconds of animation, followed by a 0.6-second dissolve. Enter / Escape and the visible **Enter website** button skip immediately into that dissolve.
- The opening line types at 42 ms per character and stays legible until its 2.4-second fade completes. Logo assembly follows; research text types from 3.5 seconds at 48 ms per character, with approximately two seconds of fully revealed English status text. The headline remains from 6.5 to 9.5 seconds, including its gentle entrance.
- Automatically plays only on a fresh navigation once per tab session. Chinese and English share the session marker. Refresh, back/forward, anchors, restored scroll, hidden tabs, reduced motion, and blocked session storage go directly to the homepage.
- The homepage footer offers **Replay introduction**. It preserves the current scroll position and restores focus to the replay button afterwards.
- Reduced motion skips the opening entirely and hides replay. A change to that preference, tab suspension, or page departure releases an active opening immediately.
- Native modal dialog provides the focus boundary. Body scroll and original padding are restored on every exit, including unexpected close. Initial entry lands focus on the main landmark with a temporary class suppressing only that landmark's outline; it is removed on blur. Buttons and other keyboard controls retain their normal focus indicators. A watchdog releases the dialog if the normal timeline does not finish.
- The dialog is closed by default. With JavaScript disabled or unavailable, the real homepage is usable. Homepage headings, metadata, structured data, sitemap, research, account, and Global Pulse stay intact.

## Editing and checking

- Layout, timings and responsive rules: `assets/home-intro.css`.
- Session, keyboard, focus, cleanup and phase timing: `assets/home-intro.js`.
- Localized markup and the original inline logo: `home_intro()` in `scripts/build.py`.
- Runtime regression checks: `node tests/home-intro.cjs`.
- Visually verify the opening at desktop, mobile portrait and short landscape sizes in both languages. Verify first entry, automatic completion, skip, replay, reduced motion, tab suspension, blocked storage and no-JavaScript access.

The displayed stages are brand storytelling, not a claim that a market-data refresh, identity check, or live verification has occurred.
