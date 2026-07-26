# stay(human).sec

A static site for `stayhumansec` — plain-language cybersecurity, AI, and privacy content, framed as a "terminal / file system" of posts. No build step, no framework, no backend. It's meant to run as-is on GitHub Pages, or via any local static server.

## Project structure

```
index.html            Homepage — hero, pillars, stats, activity heatmap, post listing
post.html             Article template — renders one post from posts.json based on ?slug=
quiz.html             Redirect shim to index.html#youcheck — the quiz used to live here as its own page
toolkit.html          Curated tool recommendations (password managers, VPNs, etc.), self-contained data
tools.html            Utilities hub — links to every small in-browser tool below
password-coach.html   Password Coach — teaches the passphrase method, generates real random examples
recovery-kit.html     2FA Recovery Kit Builder — printable "if I lose my phone" plan, localStorage only
breach-check.html     Breach Exposure Check — k-anonymity password breach lookup via HaveIBeenPwned
ask.html              Search the Archive — local keyword search over posts.json + glossary, optional AI answer
glossary.html         Full glossary, rendered from the GLOSSARY_TERMS array in site.js
404.html              Not-found page, styled as a failed `cat` command
style.css             All styles for every page (one shared stylesheet, no per-page CSS files)
site.js               All shared JS: data loading, rendering helpers, animations, nav, command palette
posts.json            All post content — the only content data file; index.html and post.html both read it
```

There is no templating engine or bundler. Every HTML file is hand-written, loads `style.css` and `site.js` directly via `<link>`/`<script>` tags, and does its own DOM rendering inline in a `<script>` block at the bottom of the file. `index.html` and `post.html` both fail loudly (visible error message) if `site.js` didn't load or `posts.json` didn't fetch — this is deliberate, since `fetch()` against a local `file://` path is blocked by browsers, and that's the #1 way people break this site testing it locally. Use a local static server (e.g. `python3 -m http.server`) when developing.

## Content model: posts.json

`posts.json` is the single source of truth for every post. Shape:

```
{ "posts": [ { ...post }, { ...post }, ... ] }
```

Each post object drives both the homepage listing card (via `index.html`) and the full article render (via `post.html`, matched by `?slug=`). Key fields:

- `slug`, `filename` — `filename` is the cosmetic "FILE_NNN.md" identity shown in the UI; `slug` is the real routing key.
- `badge` — `"live"` or `"soon"`. Non-live posts render dimmed and unclickable on the homepage.
- `freq` — `"daily" | "weekly" | "occasional"`, drives the homepage tab filter.
- `pillar`, `pillarLabel`, `pillarColor` — which of the 8 content pillars this post belongs to (see below); drives pillar-card filtering and the colored tag chip.
- `stripeColor`, `tagColor` — accent colors for the listing-card dot and the article's rotated tag pill. Always one of the CSS custom properties (`var(--orange)`, `var(--blue)`, etc.), never a raw hex.
- `title`, `titleAccent` — `titleAccent` is a substring of `title` that gets wrapped in `<span class="accent">` (orange highlight) when the article title renders.
- `listDesc` — short description shown on the homepage card.
- `intro`, `statLine` — article intro paragraph and the "$ context — ..." stat line under the title.
- `sections[]` — the article body. Each section has `num` (e.g. `"01"`), `title`, and `blocks[]`.
- `checklist[]` — plain strings rendered as the "60-second version" checklist at the end of the article.
- `warn` — `{ label, text }`, rendered as the pink warning box.
- `next` — `{ slug, eyebrow, title, desc }`. If `slug` is `null`, the "next" box renders as a non-link div instead of an `<a>` (used for the last/most-recent post).
- `readMinutes` — shown as "N min read" on both the card and the article.

### Section block types

Each entry in `sections[].blocks[]` has a `type`, rendered by `renderBlock()` in `post.html`:

- `"step"` — `{ platform?, paragraphs[] }`. `platform` is optional (e.g. `"iPhone"`, `"Android"`) and rendered as a small green label above the paragraphs. Paragraphs are raw HTML strings (can contain `<code>`), **not** escaped — only author trusted content here.
- `"compare"` — `{ bad: {label, text}, good: {label, text} }`. Renders a two-column ✕/✓ comparison box. `text` fields ARE escaped.
- `"pattern-list"` — `{ items: [{ tag, text }] }`. Renders a list of tagged pattern entries (e.g. scam-text categories). Escaped.

When adding a new post, follow an existing post in `posts.json` as a template rather than inventing new block types — `post.html`'s `renderBlock()` only knows these three.

## The 8 content pillars

Defined by convention across `index.html` (pillar-card grid) and each post's `pillar`/`pillarColor` fields — there's no separate pillar config file, so a pillar's color must be kept consistent everywhere it's referenced:

| pillar slug | label | color | cadence |
|---|---|---|---|
| `cyber-news` | Cyber News | `var(--blue)` | Daily |
| `stay-safe` | Stay Safe | `var(--orange)` | Daily |
| `cyber-basics` | Cyber Basics | `var(--green)` | Daily |
| `ai-watch` | AI Watch | `var(--violet)` | Weekly |
| `myth-busting` | Myth Busting | `var(--gold)` | Weekly |
| `case-file` | Case File | `var(--pink)` | Weekly |
| `deep-dive` | Deep Dive | `var(--green)` | Occasional |
| `story-time` | Story Time | `#ff8a6a` (one-off, not a CSS var) | Occasional |

## Brand system

**Identity**: "stay(human).sec" — wordmark always styled as `stay` + `(human)` in accent orange + `.sec`, reused verbatim (with parens colored) in the nav, hero, and footer. Tagline: "For human. For privacy." Framed persona: "Not a company. Not a bot. Just one person explaining this properly."

**Visual language**: dark terminal/hacker aesthetic softened with warm color and rounded corners — the site imitates a file system / CLI (`ls ./posts`, `cat FILE_001.md`, boot sequences, `$` prompts) without being cold or intimidating. Cards are labeled like files (`FILE_001.md`), sections are numbered like a manual (`01`, `02`), and copy leans "explain it like a helpful friend," not corporate or fear-based.

**Colors** (CSS custom properties in `style.css :root`):
```
--bg:      #000000   page background
--card:    #0d0c0a   card/panel background
--cream:   #f4f1e8   primary text
--cream-dim: #c7c3b6 secondary/muted text
--orange:  #ff7a3d   primary brand accent (CTAs, links, highlights)
--blue:    #4c8dff
--green:   #3fcf8e   also used for "live"/success/positive states
--violet:  #9670e6
--gold:    #e8a700
--pink:    #e85a82   also used for warnings/danger states
--line:    #3a352c   borders/dividers (usually dashed)
```
Orange is the single primary accent (CTAs, active states, hover borders). Green = positive/live/good. Pink = warning/danger/bad. The other four (blue, violet, gold, and the one-off `#ff8a6a`) are used purely as pillar-identity colors, not semantic ones.

**Typography**: `Poppins` for body/headings (loaded from Google Fonts), `JetBrains Mono` for anything meant to read as "terminal output" — nav links, badges, filenames, code, eyebrows, stat lines. This split is consistent everywhere: if it should feel typed/technical, it's mono; if it's prose, it's Poppins.

**Texture**: a faint fixed grid background (`--grid`), an SVG noise/grain overlay via `body::after`, and an ambient cursor-glow effect on desktop (skipped on touch and under `prefers-reduced-motion`). Sections alternate plain vs. `.section-alt` (a translucent card-tinted background with dashed top/bottom borders) to break up long vertical scroll.

**Motion conventions**: elements needing scroll-in animation get class `.reveal`, activated by `initScrollReveal()` (IntersectionObserver-based) which adds `.is-visible`. Pass `{ stagger: true }` when reveals live inside a shared parent (grids, listings) to cascade them. Everything respects `prefers-reduced-motion` by skipping straight to the final state — this is handled at both the CSS (`@media (prefers-reduced-motion: reduce)`) and JS level, and any new animated feature should follow the same pattern.

**Signature interactions** (all defined in `site.js`, reused across pages by calling the same init functions):
- Boot sequence overlay (`initBootSequence`) — plays once per browser session on first page load, doing a fake "security checkup" of the page itself (0 trackers, 0 ad scripts, 0 cookies found) as a genuine, non-marketing trust signal, since the site really has none of those.
- Command palette (`initCommandPalette`) — ⌘K/Ctrl+K fuzzy search across all posts + static pages, triggered by any element with `id="cmdkTrigger"`.
- Mobile nav (`initMobileNav`) — auto-builds a slide-out panel from whatever's already in `.nav-links`, so link lists never need to be duplicated per page.
- Inline glossary tooltips (`initGlossaryTooltips`) — auto-wraps the first mention of any `GLOSSARY_TERMS` entry inside article `<p>` tags with a tap-to-reveal definition popover.
- Scroll progress bar, scroll-position-based nav compaction, animated counters (`data-countup`), and a GitHub-style activity heatmap of publish dates — all self-contained, opt-in per page by calling the relevant `init*`/`render*` function.

## Utility & Content Philosophy

### Current utilities (in `tools.html`)

- `password-coach.html` — Password Coach. Teaches the passphrase method rather than handing over a copy-paste password.
- `recovery-kit.html` — 2FA Recovery Kit Builder. Pure offline form + localStorage, no AI, no network calls.
- `breach-check.html` — Breach Exposure Check. Real k-anonymity math against HaveIBeenPwned; the password itself never leaves the browser, only a SHA-1 hash prefix does.
- `ask.html` — Search the Archive. Local keyword search over `posts.json` + glossary, with an optional BYOK AI deep-dive on top. Renamed from "Ask the Archive" since the default experience is search, not Q&A — kept for now but not fully proven out; a genuinely synthesizing version may replace it later as its own task.

**Removed**: Scam & Phishing Inspector and Privacy Policy Reader (both deleted, along with every link/reference to them). Both worked by regex pattern-matching over arbitrary user-pasted text — a scam message or a policy document — and presenting the result as a verdict. That's an approximate judgment call dressed up as a finding, not a real check, and a security education brand can't afford a tool that's confidently wrong. Do not rebuild either of these, or anything with the same shape (open-ended text in, "risk" verdict out from string matching), even if asked to make it "smarter" — the fix for a heuristic-only tool giving false confidence is not adding more heuristics, it's not shipping it as a verdict-giving tool at all.

### Ship a tool only if it's backed by something real

- Real data (an actual breach database, actual math), real computation (client-side crypto, real randomness), or the user's own structured input (a form, a checklist) — never an approximate judgment call on open-ended or ambiguous text. A confidently-wrong security tool is worse than no tool at all.
- Prefer tools that teach the underlying method or skill over tools that just generate a finished answer to copy-paste. The goal is someone leaves having learned something they can do themselves forever, not a one-time output they'll forget the origin of.
- Never name a tool "AI [X]" unless AI is doing genuine, load-bearing work in the *default* experience. If AI is an optional bring-your-own-key extra layered on top of a working non-AI tool, it must never be required for the tool to be useful, and the name shouldn't imply AI is core to it.
- Any "save," "export," or "download" feature (Copy-as-markdown, Download as PDF, and anything added later in this family) generates its output entirely client-side and triggers a direct browser download or clipboard write — no server round-trip, no email capture, no data collected anywhere. This is a firm precedent for the whole site, not a case-by-case call: it's the same "nothing leaves the browser unless you explicitly ask for the BYOK AI extra" guarantee applied to exports specifically.

### Writing (Instagram captions and website articles alike)

- Plain language always beats jargon. If a beginner wouldn't understand a term on first read, either explain it inline or don't use it.
- No fear-mongering. State real risks honestly, but always pair them with a concrete, doable fix — never leave someone anxious with nothing actionable to do about it.
- Written voice is one real person, not a company or a bot — warm, direct, occasionally a little playful, never corporate.
- Never overstate certainty. If something is a heuristic, an estimate, or has real limitations, say so plainly rather than presenting it as a definitive verdict.

## Content conventions

- **Tone**: direct, calm, non-alarmist. Explicitly avoids fear-mongering ("Don't panic, but do act") and jargon (every technical term either gets a plain-language gloss inline or is picked up automatically by the glossary tooltip system).
- **Structure per post**: numbered steps grouped into sections, each step often split by platform (iPhone vs. Android) when instructions diverge — always in that order, iPhone first.
- **Closers**: nearly every post ends the same way — a warning box for "if this already happened to you," then a "60-second version" checklist, then a "next file" teaser box linking to the next post (or a placeholder if none exists yet).
- **New post checklist**: add an entry to `posts.json` following an existing post's shape exactly; pick a `pillar` from the table above (reuse its exact `pillarColor`); keep `stripeColor`/`tagColor` as `var(--...)` references, not hex; keep `next.slug` of the *previous* most-recent post pointing at the new one, and set the new post's own `next` to `null` until a following post exists.
- **Copy-as-markdown**: `post.html` includes a "Copy as .md" button; `generateMarkdown()` in `site.js` reconstructs a markdown version of a post straight from its JSON shape, so any post added to `posts.json` gets this for free with no extra work.
- **Download as PDF**: `post.html` includes a "Download as PDF" button below the next-post box. `generatePostPdf()` in `site.js` draws the PDF directly with jsPDF's native text/shape API. This is the *fourth* implementation of this feature, and the history matters: v1 (html2canvas/html2pdf.js rasterizing a styled DOM clone) and v2 (`window.print()` + a print stylesheet) both went through multiple rounds of real-world blank/broken PDFs that never reproduced in testing — v1's canvas silently painted nothing in some browsers, v2 depended entirely on the visitor's OS/browser print pipeline, and on at least one real machine that pipeline rasterized the whole page through a "Print to PDF" driver instead of producing real text (confirmed by inspecting the file: every page was a `DCTDecode` JPEG image with zero embedded fonts, despite looking visually correct). Both failure modes trace to the same root cause — handing the actual rendering off to something else (a canvas library, a print driver) and hoping it behaves consistently across every visitor's setup. Native jsPDF drawing has no such handoff: this site's own code controls every glyph and shape, so there's nothing external left to behave unpredictably. **This is now the standing approach — don't reintroduce html2canvas or `window.print()` for this feature without a very specific reason.** v3 tried a deliberately different light/cream "standalone document" look instead of matching the site, on the reasoning that a downloadable resource didn't need to look identical to the webpage — that was explicitly reversed in v4 back to matching the site's actual dark/grid/glass identity, so don't reintroduce the light theme either without being asked.
  - Matches the site's dark identity: black background (`PDF_DARK_COLORS.bg`), a faint 44pt line grid on every page (`drawPdfGrid()`) reproducing the site's `--grid` overlay, and "glass" cards (`drawPdfGlassBox()` — a low-opacity fill via jsPDF's `GState`/`saveGraphicsState`/`restoreGraphicsState` opacity API, plus a solid border) standing in for `backdrop-filter` blur, which has no flat-vector equivalent. **Glass is only correct for what's actually glass on the real site** — the header's terminal-chrome bar (`.path-bar`/`.hero-terminal`, translucent), the warning box (`.warn-box`, `background:rgba(232,90,130,0.08)` — pink-tinted, not cream-tinted), and the TL;DR box (`.tldr-box`, `background:rgba(76,141,255,0.08)` — blue-tinted). Step blocks and pattern-list items are **solid** cards on the real site (`.step`/`.pattern-list li`, `background:var(--card)`), not glass — `drawPdfSolidCard()` handles those; an earlier draft of this file wrongly gave step blocks the glass treatment, so check the actual CSS for a given element before assuming it's glass. The chrome bar's window controls are minimize/maximize/close icon glyphs (a line, a square outline, an X — the X in pink), matching `.win-controls` exactly — not colored macOS-style traffic-light dots, which was another wrong assumption caught by comparing a generated PDF directly against a screenshot of the real site.
  - Header content order matches `.article-meta-row`'s real order: tag pill (bordered, `post.tagColor` via `pdfColorFromVar()`) + pillar chip (bordered, dotted, `post.pillarColor`/`post.pillarLabel`) + read time, *then* the title, *then* the intro, *then* the TL;DR box (`post.tldr`, when present), *then* the stat line (`post.statLine`, when present) — all of this was missing or reordered in an earlier draft (the tag rendered as bare mono text with no pill, no pillar chip at all, no TL;DR box, no stat line) until caught by comparing a generated PDF side-by-side against a screenshot of the real page. Section dividers (`drawDivider()`) are dashed, matching `.divider{border-top:1px dashed}` — an earlier draft drew them solid.
  - `pdfColorFromVar()` maps a post's `var(--xxx)` string to `PDF_DARK_COLORS`, so the color's key in that object **must exactly match the CSS variable's name** (`var(--pink)` → `PDF_DARK_COLORS.pink`) or the lookup silently falls through to the orange default with no error — this exact bug shipped once (the palette used `pinkBorder` as the key), and it's an easy one to miss visually since the muted-orange fallback and true pink aren't wildly different at PDF-preview thumbnail size. Verify actual pixel colors (e.g. `page.get_pixmap().pixel(x, y)` or a zoomed-in render crop) when checking a specific element's color, not just a glance at the full page.
  - Both Poppins (headings) and JetBrains Mono (terminal-style text — the chrome bar, tag pill, section numbers, platform labels, footer) are embedded from `fonts.gstatic.com` (the same host the site's own `@font-face` rules use), matching the site's actual typography split, with `helvetica`/`courier` fallbacks if that fetch fails. The header brand icon is redrawn in vector using the exact bezier curve data from `brandIconSVG()`, cream-stroked to match the dark background.
  - Pink (not orange) for the warning box, matching the site's own semantic color split where pink means warning/danger and orange means primary accent — don't blur the two just because this is a new surface.
  - `sanitizePdfText()` strips `→`/`⚠`/`☐` and any *leading* `✕`/`✓` before text reaches jsPDF's fonts. Watch out if you add new copy that prepends its own label before a string that already carries one of these symbols (e.g. `'AVOID — ' + block.bad.label`) — the anchored leading-symbol regex won't catch it if the symbol ends up mid-string, and an unstripped symbol here doesn't just render wrong, it corrupts `splitTextToSize()`'s width math and runs text off the page edge. Strip the source field's own symbol before concatenating, don't rely on the sanitizer to catch it after the fact — this exact bug happened once already while building the compare-block rendering.
  - Verify any change here with PyMuPDF, not just "the button worked": `page.get_text()` should return real content, `page.get_fonts()` should show `Type0`/embedded fonts, and `page.get_images()` should be empty — a rasterized fallback looks identical to a human eye but fails all three.
- **Escaping**: all post-derived text is passed through `escapeHTML()` before insertion, *except* `step` block `paragraphs`, which are treated as trusted raw HTML (so `<code>` tags work) — never put user-supplied or untrusted content there.
