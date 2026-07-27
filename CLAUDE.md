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
news.html             News page — every Cyber News/AI News post in one feed, plus the "Also today" curated headline strip below it
posts.json            All post content — the only content data file; index.html and post.html both read it
newsBriefs.json       Bare curated headlines for the "Also today" strip on news.html (headline + source + link only, no write-up) — see AUTOMATED-WORKFLOW.md's "Also today" section
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
- `sourceUrl`, `sourceName`, `date` — **required on any post whose `pillar` is `cyber-news` or `ai-news`**, unused otherwise. `sourceUrl` links directly to the specific outside story (not the outlet's homepage), `sourceName` is the outlet's name (e.g. `"BleepingComputer"`), and `date` is an ISO string (`"2026-07-26"`) used to sort the News page newest-first. See `news.html` and `AUTOMATED-WORKFLOW.md`'s sourcing sections.

### Section block types

Each entry in `sections[].blocks[]` has a `type`, rendered by `renderBlock()` in `post.html`:

- `"step"` — `{ platform?, paragraphs[] }`. `platform` is optional (e.g. `"iPhone"`, `"Android"`) and rendered as a small green label above the paragraphs. Paragraphs are raw HTML strings (can contain `<code>`), **not** escaped — only author trusted content here.
- `"compare"` — `{ bad: {label, text}, good: {label, text} }`. Renders a two-column ✕/✓ comparison box. `text` fields ARE escaped.
- `"pattern-list"` — `{ items: [{ tag, text }] }`. Renders a list of tagged pattern entries (e.g. scam-text categories). Escaped.

When adding a new post, follow an existing post in `posts.json` as a template rather than inventing new block types — `post.html`'s `renderBlock()` only knows these three.

## The 9 content pillars

Defined by convention across `index.html` (pillar-card grid) and each post's `pillar`/`pillarColor` fields — there's no separate pillar config file, so a pillar's color must be kept consistent everywhere it's referenced:

| pillar slug | label | color | cadence |
|---|---|---|---|
| `cyber-news` | Cyber News | `var(--blue)` | Alternates daily w/ AI News |
| `ai-news` | AI News | `var(--violet)` | Alternates daily w/ Cyber News |
| `stay-safe` | Stay Safe | `var(--orange)` | Daily |
| `cyber-basics` | Cyber Basics | `var(--green)` | Daily |
| `ai-watch` | AI Watch | `var(--violet)` | Weekly |
| `myth-busting` | Myth Busting | `var(--gold)` | Weekly |
| `case-file` | Case File | `var(--pink)` | Weekly |
| `deep-dive` | Deep Dive | `var(--green)` | Occasional |
| `story-time` | Story Time | `#ff8a6a` (one-off, not a CSS var) | Occasional |

`ai-news` deliberately shares `ai-watch`'s violet accent rather than getting its own color — they read as siblings (both AI-related), and it avoids introducing a new CSS custom property just to distinguish them. What *does* distinguish them is the pillar slug itself: `ai-news` is always live-sourced, never pre-planned, while `ai-watch` covers the deliberately-written AI Watch topics in `CALENDAR.md`. This is a deliberate exception to "one color per pillar" — every other pillar still gets its own distinct color. A dedicated Privacy pillar was considered and rejected for the same reason `ai-news` almost was: privacy content stays distributed across Myth Busting/Cyber Basics/Stay Safe rather than adding a 10th pillar card.

**Cyber News and AI News are a hard 50/50, not a daily-vs-occasional split.** They alternate daily — one runs each day, never both, never neither — specifically because the earlier setup (Cyber News daily, AI News twice a week) worked out to roughly 78/22 in practice, the same one-day-at-a-time drift that caused the imbalance in "Content Balance" below. See `AUTOMATED-WORKFLOW.md` for the exact alternation rule and sourcing criteria for both.

## Content Balance

An audit run in July 2026 found a real, measured imbalance despite the brand claiming three equal pillars (cybersecurity, AI, privacy): of 28 planned content pieces, 18 were cybersecurity, 5 were privacy, 4 were AI-as-attacker (deepfakes, voice cloning, AI phishing), and **exactly 1 was AI-privacy-intersection** — content about what happens to a normal person's *own* data when *they* use an AI tool (a ChatGPT conversation, an AI photo upload, a voice assistant, an app quietly adding an AI feature). Every AI Watch post up to that point treated AI purely as an attacker's tool, never as something the reader hands their own data to.

The calendar was rebalanced in response — see `CALENDAR.md`, which now runs roughly 11 cybersecurity / 9 privacy / 8 AI across all 28 days, with 6 of those 8 AI Watch slots specifically AI-and-your-own-data topics. When planning future days beyond day 28, or when Cyber News/AI News stories come up for selection, keep this same rough three-way balance in mind rather than defaulting back to cybersecurity-only or AI-as-attacker-only topics — the imbalance came from exactly that default, applied one day at a time without anyone checking the aggregate.

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
- Any "save," "export," or "download" feature (Copy-as-markdown, and anything added later in this family) generates its output entirely client-side and triggers a direct browser download or clipboard write — no server round-trip, no email capture, no data collected anywhere. This is a firm precedent for the whole site, not a case-by-case call: it's the same "nothing leaves the browser unless you explicitly ask for the BYOK AI extra" guarantee applied to exports specifically.

### Writing (Instagram captions and website articles alike)

- Plain language always beats jargon. If a beginner wouldn't understand a term on first read, either explain it inline or don't use it.
- No fear-mongering. State real risks honestly, but always pair them with a concrete, doable fix — never leave someone anxious with nothing actionable to do about it.
- Written voice is one real person, not a company or a bot — warm, direct, occasionally a little playful, never corporate.
- Never overstate certainty. If something is a heuristic, an estimate, or has real limitations, say so plainly rather than presenting it as a definitive verdict.

### The beginner test (mandatory before any content ships)

Every piece of content — carousel, article, or animated explainer script — gets checked against one question before it's considered done: **would a complete beginner follow this start to finish without needing to look anything else up?** This is a permanent standard, not a one-time cleanup pass. Concretely:

- Every technical term is either avoided or defined in plain language the moment it's first used. Cross-check it against `GLOSSARY_TERMS` in `site.js` — if the term isn't in there and isn't explained inline, that's a gap to fix before shipping, not after.
- Never assume a setting, menu, or concept is self-explanatory just because it has a specific name. "Device admin apps," "OTP," and "spyware" all shipped once without ever being explained in plain words — asking a reader to evaluate a settings screen, or warning them about a term, without first saying what it actually means or does is exactly the failure mode to catch. Say what it *does*, not just what it's *called*.
- Reread the finished piece once specifically hunting for tone that's drifted dry or instructional instead of staying "one person explaining this to a friend" — this can happen even when every individual sentence is factually fine.

This audit was first run in full against `posts.json` and the carousel/social copy in July 2026 — see "Content Balance" below for the topic-coverage half of that audit, and treat both halves (balance and writing quality) as a standard to re-check periodically, not a single fix.

## Content conventions

- **Tone**: direct, calm, non-alarmist. Explicitly avoids fear-mongering ("Don't panic, but do act") and jargon (every technical term either gets a plain-language gloss inline or is picked up automatically by the glossary tooltip system).
- **Structure per post**: numbered steps grouped into sections, each step often split by platform (iPhone vs. Android) when instructions diverge — always in that order, iPhone first.
- **Closers**: nearly every post ends the same way — a warning box for "if this already happened to you," then a "60-second version" checklist, then a "next file" teaser box linking to the next post (or a placeholder if none exists yet).
- **New post checklist**: add an entry to `posts.json` following an existing post's shape exactly; pick a `pillar` from the table above (reuse its exact `pillarColor`); keep `stripeColor`/`tagColor` as `var(--...)` references, not hex; keep `next.slug` of the *previous* most-recent post pointing at the new one, and set the new post's own `next` to `null` until a following post exists.
- **Copy-as-markdown**: `post.html` includes a "Copy as .md" button; `generateMarkdown()` in `site.js` reconstructs a markdown version of a post straight from its JSON shape, so any post added to `posts.json` gets this for free with no extra work.
- **Download as PDF — removed.** This existed through four implementations (html2canvas/html2pdf.js rasterizing a DOM clone, `window.print()` + a print stylesheet, and two rounds of native jsPDF drawing chasing dark/grid/glass fidelity against the live site) before being removed entirely at the user's request. Every version, `generatePostPdf()`/`drawPdf*()` helpers, the CDN font-fetch code, and the `.download-pdf-btn` CSS are gone from `site.js`/`post.html`/`style.css`. If asked to rebuild this feature, don't assume any prior version's approach was "the answer" — html2canvas silently produced blank PDFs for real visitors, `window.print()` depended on the visitor's OS print pipeline (one real machine rasterized the whole page through a "Print to PDF" driver instead of producing real text), and native jsPDF drawing required several rounds of fixing color/font/layout fidelity bugs against the actual site CSS. Ask what's wanted (light standalone document vs. dark/grid/glass site match) before building, and verify any PDF output with PyMuPDF (`page.get_text()`, `page.get_fonts()`, `page.get_images()`) rather than assuming it looks right.
- **Escaping**: all post-derived text is passed through `escapeHTML()` before insertion, *except* `step` block `paragraphs`, which are treated as trusted raw HTML (so `<code>` tags work) — never put user-supplied or untrusted content there.
- **Platform adaptation**: one fact/fix, four packages. The underlying content — the actual fact, the actual fix — never changes between platforms; only tone and format do. Instagram gets the 4-slide carousel with a punchy hook-style caption; Facebook reuses those exact same slides with a warmer, community/family-oriented caption; LinkedIn combines those same slides into a single PDF carousel with a narrative, first-person, professionally-framed caption; X gets a numbered thread instead of any images at all. See "Platform-specific packaging" under Automated Post Generation Workflow for the exact spec per platform.


## Automated Post Generation Workflow

The full standard process for generating a day's post — the website
article, the Instagram carousel, and the Facebook/LinkedIn/X packages built
from it, including the exact 4-slide structure, the platform-packaging
spec, the numbered standard steps, the Cyber News/AI News sourcing
criteria, and the auto-merge verification checklist — lives in
**[`AUTOMATED-WORKFLOW.md`](./AUTOMATED-WORKFLOW.md)**, not in this file.
That document is the source of truth for the workflow itself; this section
just points to it so it isn't missed.

The short version: the website grows automatically as posts are added, as
long as automated verification passes. Social packaging (Instagram,
Facebook, LinkedIn, X) is always manual — **this workflow never posts to
any social platform under any circumstances.**
