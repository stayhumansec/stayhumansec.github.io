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
prompts.html          Prompt Library — pre-written prompts to copy into any AI chat, see "Prompt Library" section below
glossary.html         Full glossary, rendered from the GLOSSARY_TERMS array in site.js
404.html              Not-found page, styled as a failed `cat` command
style.css             All styles for every page (one shared stylesheet, no per-page CSS files)
site.js               All shared JS: data loading, rendering helpers, animations, nav, command palette
fonts/                Self-hosted Sora + IBM Plex Mono woff2 files (@font-face'd from style.css) plus their OFL LICENSE.txt — no Google Fonts request, keeping the "0 trackers" boot-sequence claim literally true
news.html             News page — every Cyber News/AI News post in one feed, plus the "Also today" curated headline strip below it
notes.html             on(my).mind — freeform personal writing (technical/philosophy/concerns), separate from posts/News, see "on(my).mind" section below
posts.json            All post content — the only content data file; index.html and post.html both read it
newsBriefs.json       Bare curated headlines for the "Also today" strip on news.html (headline + source + link only, no write-up) — see AUTOMATED-WORKFLOW.md's "Also today" section
notes.json             All on(my).mind content — deliberately thinner schema than posts.json, see "on(my).mind" section below
prompts.json           All Prompt Library content — see "Prompt Library" section below
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

**Identity**: "stay(human).sec" — wordmark always styled as `stay` + `(human)` in accent orange + `.sec`, reused verbatim (with parens colored) in the nav, hero, and footer. Framed persona: "Not a company. Not a bot. Just one person explaining this properly."

**Motto vs. tagline**: "For human. For privacy." is the short-form motto — shown as a pill badge above the wordmark in the hero (`.hero-motto` in `index.html`), `HUMAN`/`PRIVACY` bold orange, rest cream-dim, `IBM Plex Mono`. "Use AI. Remain human. Privacy matters." is the full canonical tagline — originally written for day_01's social captions/thread (`instagram/posts/day_01_launch/`) but not ported to the website until this line was added; now lives directly under the wordmark in the hero (`.hero-tagline`), all-caps, bold: `AI`/`HUMAN`/`PRIVACY` orange, rest cream (not cream-dim — unlike the motto pill, the tagline uses full-brightness cream), `IBM Plex Mono`. Both are canonical and both stay — the motto is the compact badge version, the tagline is the fuller line underneath it, not a replacement for one another.

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

**Typography**: `Sora` for body/headings (self-hosted, see fonts/), `IBM Plex Mono` for anything meant to read as "terminal output" — nav links, badges, filenames, code, eyebrows, stat lines. This split is consistent everywhere: if it should feel typed/technical, it's mono; if it's prose, it's Sora.

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
- `ask.html` — Search the Archive. Local keyword search over `posts.json` + glossary is the default for every visitor (no key needed). With a BYOK API key saved, an AI synthesis auto-runs on top of each search — grounded specifically in that query's matched posts/glossary terms (title, intro, a real quoted snippet, checklist), not the whole site, so it cites and quotes what it actually found rather than giving a generic take. Stays named "Search the Archive" rather than reverting to "Ask the Archive": local search is still the only guaranteed-default experience, since AI can never run without a visitor's own key on a backend-less static site.

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

## Prompt Library (`prompts.html` / `prompts.json`)

Extends the same "teach the method, don't just hand over the answer" philosophy behind Password Coach into a new format: rather than writing a guide for every possible situation, this teaches people how to get reliable help from an AI chat (ChatGPT, Claude, Gemini, etc.) for situations too specific or too numerous for the site to cover directly — e.g. "recover my Gmail account," "check what an app permission actually does," "explain this privacy policy clause to me." Each entry is a pre-written prompt someone copies and pastes into whatever AI chat they already use, then works through interactively.

**Schema** (`prompts.json`, repo root): `{ "prompts": [ { slug, title, pillar, pillarColor, promptText, checkNote }, ... ] }`.

- `pillar`/`pillarColor` reuse the exact 9-pillar slugs/colors from the table above (`prompts.html` derives the human-readable label from the slug locally; the schema itself doesn't duplicate a `pillarLabel` field the way `posts.json` does).
- `promptText` is the literal text copied to the clipboard when someone clicks "Copy prompt" — write it as a complete, self-contained prompt (it should tell the AI what role to play and to ask the person clarifying questions about their specific situation, not assume the AI already has context it doesn't).

**`checkNote` is mandatory on every single entry — never optional, never skipped.** This is where the actual safety guidance for that specific prompt lives: what never to paste into the AI chat, or what to verify through an official/authoritative source before acting on what the AI says. For an account-recovery prompt, for example, that's something like "never share an actual OTP, verification code, or password with an AI chat — no legitimate recovery process needs that, and no prompt on this page should ever ask you to paste one in." A prompt entry without a real, specific `checkNote` is not ready to ship, the same way a news-pillar post without `sourceUrl`/`sourceName`/`date` isn't ready to ship (see the Automated Post Generation Workflow's verification checklist for that precedent).

This is separate from — and doesn't replace — the page-level disclaimer at the top of `prompts.html` ("AI responses can be wrong or outdated. For anything involving passwords, payments, or account access, always verify through the platform's real official support before acting on AI advice."), which applies to every entry generally. `checkNote` is the specific risk for *that* prompt; the banner is the general rule for the whole page. Keep both — don't fold one into the other.

## Content conventions

- **Tone**: direct, calm, non-alarmist. Explicitly avoids fear-mongering ("Don't panic, but do act") and jargon (every technical term either gets a plain-language gloss inline or is picked up automatically by the glossary tooltip system).
- **Structure per post**: numbered steps grouped into sections, each step often split by platform (iPhone vs. Android) when instructions diverge — always in that order, iPhone first.
- **Closers**: nearly every post ends the same way — a warning box for "if this already happened to you," then a "60-second version" checklist, then a "next file" teaser box linking to the next post (or a placeholder if none exists yet).
- **New post checklist**: add an entry to `posts.json` following an existing post's shape exactly; pick a `pillar` from the table above (reuse its exact `pillarColor`); keep `stripeColor`/`tagColor` as `var(--...)` references, not hex; keep `next.slug` of the *previous* most-recent post pointing at the new one, and set the new post's own `next` to `null` until a following post exists.
- **Copy-as-markdown**: `post.html` includes a "Copy as .md" button; `generateMarkdown()` in `site.js` reconstructs a markdown version of a post straight from its JSON shape, so any post added to `posts.json` gets this for free with no extra work.
- **Download as PDF — removed.** This existed through four implementations (html2canvas/html2pdf.js rasterizing a DOM clone, `window.print()` + a print stylesheet, and two rounds of native jsPDF drawing chasing dark/grid/glass fidelity against the live site) before being removed entirely at the user's request. Every version, `generatePostPdf()`/`drawPdf*()` helpers, the CDN font-fetch code, and the `.download-pdf-btn` CSS are gone from `site.js`/`post.html`/`style.css`. If asked to rebuild this feature, don't assume any prior version's approach was "the answer" — html2canvas silently produced blank PDFs for real visitors, `window.print()` depended on the visitor's OS print pipeline (one real machine rasterized the whole page through a "Print to PDF" driver instead of producing real text), and native jsPDF drawing required several rounds of fixing color/font/layout fidelity bugs against the actual site CSS. Ask what's wanted (light standalone document vs. dark/grid/glass site match) before building, and verify any PDF output with PyMuPDF (`page.get_text()`, `page.get_fonts()`, `page.get_images()`) rather than assuming it looks right.
- **Escaping**: all post-derived text is passed through `escapeHTML()` before insertion, *except* `step` block `paragraphs`, which are treated as trusted raw HTML (so `<code>` tags work) — never put user-supplied or untrusted content there.
- **Platform adaptation**: one fact/fix, five packages. The underlying content — the actual fact, the actual fix — never changes between platforms; only tone and format do. Instagram gets the 4-slide carousel with a punchy hook-style caption; Facebook reuses those exact same slides with a warmer, community/family-oriented caption; LinkedIn combines those same slides into a single PDF carousel with a narrative, first-person, professionally-framed caption; X gets a numbered thread instead of any images at all; Reels gets a separately-written voiceover script turned into a captioned, hook-overlaid vertical video via `instagram/generate_reel.py`. See "Platform-specific packaging" under Automated Post Generation Workflow for the exact spec per platform.

## on(my).mind (`notes.html` / `notes.json`) — a deliberately different voice

Displayed site-wide as **"on(my).mind"** (nav link, page title, terminal path bar) — the underlying filenames stay `notes.html`/`notes.json` since renaming those is a bigger structural change than the display name warrants, the same way "You, Check." lives at `index.html#youcheck` rather than a matching filename. Talk about the *feature* as on(my).mind; talk about the *files* as `notes.html`/`notes.json`.

on(my).mind is a separate, freeform writing section — **not** part of the posts/News system, and not held to the same standard. Where every post above is built to pass "the beginner test" (plain language, every term explained, structured teaching), on(my).mind is the opposite on purpose: first-person, less polished, allowed to assume the reader already has context, allowed to sit with an unresolved thought instead of closing with a checklist.

**Do not flatten on(my).mind writing into the numbered-posts voice.** No "60-second version," no warning box, no `next` teaser, no requirement to explain every term inline — those are structural commitments of the *teaching* format, and on(my).mind is explicitly not that format. A future session editing or adding to `notes.json` should write like an actual journal entry: technical explorations, the reasoning/doubts behind why this project exists, honest concerns — including ones without a tidy resolution. If an entry reads like a post that wandered into the wrong file, that's the failure mode to catch.

**Schema** (`notes.json`, repo root): `{ "notes": [ { slug, title, date, tag, body } ] }` — deliberately thinner than `posts.json`. `tag` is one of `"technical" | "philosophy" | "concerns"`. `body` is an array of plain paragraph strings; `**bold**` and `*italic*` are the only supported emphasis (rendered via `formatNoteText()` in `site.js`, not a full markdown parser). No `sections`, `checklist`, `warn`, or `next` fields — if an entry needs those, it's probably actually a post.

**Fully siloed by design**: entries do not appear in the homepage news ticker, the command palette's search results, or `ask.html`'s archive search — only the `notes.html` *page itself* ("on(my).mind") is in the command palette's static-page list, the same way Toolkit and Glossary are. This keeps raw personal writing separate from the site's polished discovery surfaces, matching the whole point of the section existing separately in the first place.

**Rendering**: the default "All" view groups entries into three distinct chapter-like blocks — Technical, Philosophy, Concerns, each with its own colored `// LABEL` eyebrow, a one-line intro describing what that category holds, and a dashed divider separating it from the next block — rather than one flat list with tag as a small chip. Selecting a single tag tab still shows a flat list of just that category (no headers needed, since it's already one category). Every note renders inline in full (title, date, tag chip, complete body) — no "continue reading" truncation/expansion. Sorted newest-first within each group. If an entry ever gets long enough that inline rendering stops working well, the right fix is a per-note permalink page (mirroring `post.html`), not a client-side expand/collapse widget grafted onto the listing.


## Automated Post Generation Workflow

The full standard process for generating a day's post — the website
article, the Instagram carousel, and the Facebook/LinkedIn/X/Reel packages
built from it, including the exact 4-slide structure, the platform-packaging
spec, the numbered standard steps, the Cyber News/AI News sourcing
criteria, and the auto-merge verification checklist — lives in
**[`AUTOMATED-WORKFLOW.md`](./AUTOMATED-WORKFLOW.md)**, not in this file.
That document is the source of truth for the workflow itself; this section
just points to it so it isn't missed.

The short version: the website grows automatically as posts are added, as
long as automated verification passes. Social packaging (Instagram,
Facebook, LinkedIn, X, Reels) is always manual — **this workflow never
posts to any social platform under any circumstances.**
