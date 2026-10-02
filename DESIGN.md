---
name: Kuku arhiiv
description: Personal archive of Raadio Kuku shows, presented in streaming-app grammar.
colors:
  bg: "#0f0f10"
  surface: "#1b1b1d"
  surface-2: "#26262a"
  surface-3: "#323237"
  line: "#34343a"
  text: "#f4f3ef"
  text-2: "#b9b7b0"
  text-3: "#8e8c86"
  accent: "#f5b73b"
  accent-hover: "#ffc552"
  accent-press: "#e0a225"
  on-accent: "#1a1406"
  amber-dusk: "#2a2318"
  danger: "#ff7a6b"
  danger-surface: "#3a1612"
typography:
  display:
    fontFamily: "Figtree, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "clamp(1.75rem, 6vw, 2.75rem)"
    fontWeight: 800
    lineHeight: 1.05
    letterSpacing: "-0.03em"
  headline:
    fontFamily: "Figtree, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "1.75rem"
    fontWeight: 800
    lineHeight: 1.45
    letterSpacing: "-0.02em"
  title:
    fontFamily: "Figtree, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "1.375rem"
    fontWeight: 800
    lineHeight: 1.2
    letterSpacing: "-0.02em"
  body:
    fontFamily: "Figtree, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.45
  body-strong:
    fontFamily: "Figtree, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "1rem"
    fontWeight: 700
    lineHeight: 1.3
  label:
    fontFamily: "Figtree, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "0.8125rem"
    fontWeight: 400
    lineHeight: 1.45
rounded:
  cover-sm: "4px"
  cover: "6px"
  md: "10px"
  lg: "16px"
  pill: "999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "14px"
  lg: "18px"
  xl: "28px"
  section: "36px"
components:
  button-play:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.on-accent}"
    rounded: "{rounded.pill}"
    size: "48px"
  button-play-hover:
    backgroundColor: "{colors.accent-hover}"
  button-play-active:
    backgroundColor: "{colors.accent-press}"
  button-play-row:
    backgroundColor: "{colors.surface-2}"
    textColor: "{colors.text}"
    rounded: "{rounded.pill}"
    size: "44px"
  button-pill:
    textColor: "{colors.text}"
    rounded: "{rounded.pill}"
    padding: "0 18px"
    height: "40px"
  button-pill-primary:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.on-accent}"
    rounded: "{rounded.pill}"
    padding: "0 18px"
    height: "40px"
  button-pill-primary-hover:
    backgroundColor: "{colors.accent-hover}"
  button-icon:
    textColor: "{colors.text-2}"
    rounded: "{rounded.pill}"
    size: "44px"
  button-icon-hover:
    backgroundColor: "{colors.surface-2}"
    textColor: "{colors.text}"
  input-field:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text}"
    rounded: "{rounded.md}"
    padding: "0 14px"
    height: "50px"
  input-search:
    backgroundColor: "{colors.text}"
    textColor: "{colors.surface}"
    rounded: "{rounded.md}"
    padding: "0 14px"
    height: "48px"
  card-resume:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.lg}"
    padding: "14px"
  mini-player:
    backgroundColor: "{colors.amber-dusk}"
    textColor: "{colors.text}"
    rounded: "{rounded.md}"
    height: "64px"
  nav-tabs:
    backgroundColor: "{colors.bg}"
    textColor: "{colors.text-3}"
    height: "64px"
---

# Design System: Kuku arhiiv

## Overview

**Creative North Star: "The Radio Dial Lamp in a Dark Room"**

A personal archive dressed in the grammar of a streaming app the user already knows (user-chosen canon: "Spotify-like", quality bar the Spotify mobile app). Near-black ground, surfaces one lightness step above it, square cover art doing the visual work, and a persistent player that never leaves the bottom of the screen. Management (adding, removing shows) is secondary and lives in plain pills and lists, never admin tables or settings pages.

One warm amber, the glow of an old radio dial lamp, is the only color with a voice. At full strength it marks playback and the active state: the play button, progress fills, the current episode, focus. At low strength it tints the dark surfaces that belong to listening (the mini player, the resume card, the now-playing sheet), so "something is playing" reads as warmth rather than as a new hue. Phone first (390px), single column, generous 44px+ touch targets; it widens gracefully to a 760px column on desktop.

Type is Figtree throughout: heavy 800-weight headings with tight tracking against quiet 400 body text. Icons are drawn inline SVG on one stroke grammar (2 to 2.4 stroke, round caps), with play and pause as the only filled glyphs.

**Key Characteristics:**
- Near-black ground with tonal surface steps; no light theme.
- One amber accent reserved for playback and active state.
- Cover art is the primary visual; generated hue fallbacks when art is missing.
- Fully round buttons (circles and pills); softly rounded containers.
- Persistent mini player + bottom tabs; one-axis bottom-up sheet for now playing.
- Estonian UI copy, plain non-technical language.

## Colors

A dark, warm-neutral palette with a single amber signal color.

### Primary
- **Dial Lamp Amber** (accent): play buttons, progress fills, current-episode title, active speed, focus ring, selection, the "Salvesta" primary pill. Hover lifts to **Lamp Glow** (accent-hover); press settles to **Lamp Ember** (accent-press). Text on amber is **Burnt Filament** (on-accent), a near-black brown.

### Secondary
- **Amber Dusk** (amber-dusk): the mini player's background, a dark surface pre-tinted with the accent. The same tint family appears in the resume card gradient (`#2b2416` fading to surface) and the now-playing sheet gradient (`#4a3815` through `#20190d` into bg). These tints mean "listening context" and are not used on management surfaces.

### Neutral
- **Studio Black** (bg): page ground, sticky search backing, tab bar base.
- **Booth Grey** (surface): resume card, inputs, quiet banner.
- **Console Grey** (surface-2): cover placeholder, row play buttons, icon-button hover.
- **Fader Grey** (surface-3): progress-bar tracks, row play hover, scrollbar.
- **Hairline** (line): episode row dividers, input borders, danger-zone divider.
- **Paper White** (text): primary text, scrub track fill and thumb, the inverted search field.
- **Warm Ash** (text-2): secondary text (show names, descriptions, inactive icons).
- **Dim Ash** (text-3): metadata (dates, durations, expiry, times), inactive tabs, pill outlines.

### Status
- **Signal Coral** (danger) on **Oxide Red** (danger-surface): error text, the destructive pill, and the "Kuku changed" alert banner (with `#ffd9d3` body text and a `#5c231c` bottom rule).

### Named Rules
**The Lamp Rule.** Full-strength amber means "playing / active / act here to listen". It never decorates headings, tiles, or management chrome; a screen without playback in view carries almost none.

**The Warm Shadow Rule.** Listening surfaces (mini player, resume card, now-playing sheet) may carry a dark amber tint; management surfaces (search, auth, show actions, danger zone) stay neutral grey.

**The No-Green Rule.** Spotify's grammar, never Spotify's brand: no Spotify green, logo, or name, and no Kuku logo or brand imitation.

## Typography

**Display Font:** Figtree (with system-ui, -apple-system, Segoe UI, sans-serif)
**Body Font:** Figtree
Loaded from Google Fonts at weights 400, 500, 600, 700, 800.

**Character:** One geometric-humanist family carrying everything; hierarchy comes from weight jumps (400 to 700/800) and tight negative tracking on headings, not from a second face.

### Hierarchy
- **Display** (800, clamp(1.75rem, 6vw, 2.75rem), 1.05, -0.03em): show page title next to its cover. Auth page title uses 2rem at the same weight and tracking.
- **Headline** (800, 1.75rem, rising to 2.25rem at 720px+, -0.02em): the time-of-day greeting at the top of Home.
- **Title** (800, 1.375rem, -0.02em): section headings ("Uusim osa" / resume label, "Sinu saated"), empty-state heading, now-playing episode title (line-height 1.2).
- **Body** (400, 1rem, 1.45): descriptions and prose; capped at 46 to 65ch.
- **Body strong** (700, 0.9375 to 1.0625rem, 1.25 to 1.3): episode titles, tile names, result names, resume title, pill labels.
- **Label** (400 to 700, 0.75 to 0.8125rem): metadata lines, tab labels (600, 0.75rem), sheet header label (700), scrub times (tabular numerals).

### Named Rules
**The Weight-Not-Case Rule.** Hierarchy comes from weight and size. No uppercase tracked labels, no eyebrow text above headings; section labels are real h2 headings.

**The Tabular Time Rule.** Every running time and speed value uses tabular numerals so it does not jitter while playing.

## Layout

Single column, max 760px, centered; 16px side padding on phone, 20px top padding rising to 40px at 720px+. The bottom padding reserves room for the tab bar (64px), mini player (64px), safe-area inset and 32px breathing room, so content never hides under the fixed chrome.

Sections are separated by 36px (28px for the first section under the greeting); section titles sit 14px above their content. The show grid is auto-fill with 148px minimum columns (168px at 720px+), 18px row gap and 14px column gap, giving two columns on a 390px phone. Episode lists are full-width rows: title and metadata on the left, a 44px play button on the right, hairline divider above each row. The search bar is sticky to the top over a bg backing.

The now-playing sheet is a full-screen column capped at 480px: header row (close, label, speed), a flexible stage that centers the cover, and controls anchored at the bottom (title, scrubber, transport with 28px gaps).

Breakpoint: one, at 720px (more top padding, bigger greeting, roomier resume card, wider grid columns).

## Elevation & Depth

Depth is mostly tonal: surfaces step up in lightness from bg. Shadows are reserved for two kinds of objects: cover art (so square artwork lifts off the dark ground) and the floating mini player.

### Shadow Vocabulary
- **Cover lift** (`box-shadow: 0 6px 18px rgba(0,0,0,.35)`): medium covers and grid tiles. Small 44px covers and search-result covers carry no shadow.
- **Hero cover lift** (`box-shadow: 0 18px 50px rgba(0,0,0,.55)`): the large cover on the now-playing sheet.
- **Floating player** (`box-shadow: 0 10px 30px rgba(0,0,0,.5)`): the mini player, which floats above the tab bar.

### Named Rules
**The Soft Black Shadow Rule.** Shadows are soft, black, and vertical-only, used under artwork and the floating player. Cards, pills, and inputs are flat.

## Shapes

Every button is fully round: circular play and icon buttons, 999px pills. Containers are softly rounded: 10px for inputs, the search bar, tiles and the mini player; 16px for the resume card. Cover art is square (aspect-ratio 1) with tight corners (6px, 4px for the 44px thumb, 10px for the sheet hero). Progress bars are 4px tall with 2px rounding; the mini player's progress is a 2px hairline along its bottom edge.

## Components

### Buttons
Tactile and round; the press is felt through a slight scale-down.
- **Play (primary action):** amber circle, 48px (72px on the sheet), filled play/pause glyph in on-accent. Hover lifts to accent-hover; active scales to .94 and settles to accent-press (150ms, ease-out `cubic-bezier(0.16, 1, 0.3, 1)`).
- **Row play:** 44px circle in surface-2 with text-colored glyph; hover surface-3. Turns amber when the row is the current episode.
- **Pill:** 40px min-height, 18px horizontal padding, 700 weight, 1px text-3 outline; hover outline goes to text; active scales to .97. Variants: primary (amber fill), done (amber outline and text, "Salvestatud"), danger (coral text on dark red outline, faint coral hover wash). Compact pills in search results are 36px; form submit pills are 50px.
- **Icon button:** 44px circle, text-2 glyph at 22px; hover gives text color on surface-2. Transport skip buttons are 56px with 30px glyphs.
- **Speed toggle:** pill-shaped text button in the sheet header, tabular numerals, amber when above 1×.

### Cards / Containers
- **Resume card:** 16px radius, 14px padding (18px on desktop), diagonal gradient from dark amber (`#2b2416`) into surface. Holds a 72px cover, two-line clamped title, show and date line, progress bar, and the play button on the right.
- **Show tile:** cover at full width with lift shadow, 700-weight name 10px below, text-3 status line. Hover underlines the name. Pending shows (no episodes yet) render the cover at 55% opacity.
- **Cover fallback:** when art is missing, a generated hue background (`hsl(<hash> 32% 30%)`) with the show's initials at 800 weight.

### Inputs / Fields
- **Form field:** 50px tall, surface fill, 1px line border, 10px radius, 500 weight. Hover border text-3; focus border amber plus 1px amber ring. Label is 700 at 0.875rem; hint text is text-3 at 0.8125rem; errors are coral at 0.875rem.
- **Search field:** inverted (light text-colored field, near-black text and caret), 48px, 10px radius, leading search icon; focus-within draws a 3px amber ring.

### Navigation
- **Bottom tabs:** fixed, 64px plus safe area, a bg gradient that fades slightly at the top. Each tab is a 26px icon over a 0.75rem 600 label; inactive text-3, current page text. Two tabs: Kodu, Otsi.
- **Back link:** chevron plus text-2 label, 600 weight, 44px tall, hover text.

### Mini Player (signature)
Floats 6px above the tabs, 8px from the screen edges, max 744px. Amber Dusk background, 10px radius, floating shadow. The left area (44px cover, one-line title and show) opens the sheet; the right toggle is a 26px play/pause. A 2px amber progress hairline runs along the bottom.

### Now-Playing Sheet (signature)
Opens on one axis, bottom-up (420ms ease-out), closes downward (280ms ease-in). Full-screen gradient from dark amber at the top into bg. Header: chevron-down close, "Praegu mängib" label, speed toggle. Large cover centered in the flexible stage; controls anchored at the bottom: title, show link, scrubber (4px track, text-colored fill and 14px thumb on a 22% white track, tabular times), transport (-15 s, 72px play, +30 s).

### Status lines
Episode metadata is a wrapping row of text-3 facts (date, duration, expiry). "Kuulatud" carries a check icon in text-2. Imminent expiry ("Kustub varsti") is promoted to text color at 700 weight with a clock icon: urgency through weight and an icon, not through the accent.

### Banner
Full-width alert at the top of the page: Oxide Red background with a strong white first line, for the "Kuku changed" warning. A quiet variant uses surface and text-2 for neutral notices.

## Do's and Don'ts

### Do:
- **Do** keep full-strength amber (accent) for play buttons, progress, the current episode, the active speed, focus and the primary save action.
- **Do** make every button a circle or a 999px pill, with a 44px minimum touch target.
- **Do** let cover art lead; give medium and large covers the soft black lift shadow and use the generated-hue initials fallback when art is missing.
- **Do** build hierarchy from Figtree weight (800 headings with -0.02 to -0.03em tracking, 700 item titles, 400 body).
- **Do** draw new icons as inline SVG on a 24px box with 2 to 2.4 stroke and round caps; only play and pause are filled.
- **Do** reserve the bottom of the viewport for the mini player and tabs, and pad content so nothing hides beneath them.
- **Do** express urgency (expiry) with weight and an icon, keeping amber for playback.
- **Do** honor prefers-reduced-motion; motion is short and uses the ease-out curve.

### Don't:
- **Don't** use Spotify green, the Spotify logo or name, or the Kuku logo and brand look.
- **Don't** introduce a light theme, a second accent hue, or saturated colors on management surfaces.
- **Don't** lay out management as admin tables or settings pages; use lists, pills and the search view.
- **Don't** add uppercase tracked eyebrow labels above headings; section labels are h2 titles.
- **Don't** put shadows on cards, pills or inputs; depth there is tonal.
- **Don't** use icon fonts, emoji or text glyphs as icons.
