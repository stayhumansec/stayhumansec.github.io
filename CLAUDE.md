# stay(human).sec

A static site for `stayhumansec` — plain-language cybersecurity, AI, and privacy content, framed as a "terminal / file system" of posts. No build step, no framework, no backend. It's meant to run as-is on GitHub Pages, or via any local static server.

## Project structure

```
index.html      Homepage — hero, pillars, stats, activity heatmap, post listing
post.html       Article template — renders one post from posts.json based on ?slug=
quiz.html       Redirect shim to index.html#youcheck — the quiz used to live here as its own page
toolkit.html    Curated tool recommendations (password managers, VPNs, etc.), self-contained data
glossary.html   Full glossary, rendered from the GLOSSARY_TERMS array in site.js
404.html        Not-found page, styled as a failed `cat` command
style.css       All styles for every page (one shared stylesheet, no per-page CSS files)
site.js         All shared JS: data loading, rendering helpers, animations, nav, command palette
posts.json      All post content — the only content data file; index.html and post.html both read it
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

## Content conventions

- **Tone**: direct, calm, non-alarmist. Explicitly avoids fear-mongering ("Don't panic, but do act") and jargon (every technical term either gets a plain-language gloss inline or is picked up automatically by the glossary tooltip system).
- **Structure per post**: numbered steps grouped into sections, each step often split by platform (iPhone vs. Android) when instructions diverge — always in that order, iPhone first.
- **Closers**: nearly every post ends the same way — a warning box for "if this already happened to you," then a "60-second version" checklist, then a "next file" teaser box linking to the next post (or a placeholder if none exists yet).
- **New post checklist**: add an entry to `posts.json` following an existing post's shape exactly; pick a `pillar` from the table above (reuse its exact `pillarColor`); keep `stripeColor`/`tagColor` as `var(--...)` references, not hex; keep `next.slug` of the *previous* most-recent post pointing at the new one, and set the new post's own `next` to `null` until a following post exists.
- **Copy-as-markdown**: `post.html` includes a "Copy as .md" button; `generateMarkdown()` in `site.js` reconstructs a markdown version of a post straight from its JSON shape, so any post added to `posts.json` gets this for free with no extra work.
- **Escaping**: all post-derived text is passed through `escapeHTML()` before insertion, *except* `step` block `paragraphs`, which are treated as trusted raw HTML (so `<code>` tags work) — never put user-supplied or untrusted content there.
