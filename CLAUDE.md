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
- Any "save," "export," or "download" feature (Copy-as-markdown, and anything added later in this family) generates its output entirely client-side and triggers a direct browser download or clipboard write — no server round-trip, no email capture, no data collected anywhere. This is a firm precedent for the whole site, not a case-by-case call: it's the same "nothing leaves the browser unless you explicitly ask for the BYOK AI extra" guarantee applied to exports specifically.

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
- **Download as PDF — removed.** This existed through four implementations (html2canvas/html2pdf.js rasterizing a DOM clone, `window.print()` + a print stylesheet, and two rounds of native jsPDF drawing chasing dark/grid/glass fidelity against the live site) before being removed entirely at the user's request. Every version, `generatePostPdf()`/`drawPdf*()` helpers, the CDN font-fetch code, and the `.download-pdf-btn` CSS are gone from `site.js`/`post.html`/`style.css`. If asked to rebuild this feature, don't assume any prior version's approach was "the answer" — html2canvas silently produced blank PDFs for real visitors, `window.print()` depended on the visitor's OS print pipeline (one real machine rasterized the whole page through a "Print to PDF" driver instead of producing real text), and native jsPDF drawing required several rounds of fixing color/font/layout fidelity bugs against the actual site CSS. Ask what's wanted (light standalone document vs. dark/grid/glass site match) before building, and verify any PDF output with PyMuPDF (`page.get_text()`, `page.get_fonts()`, `page.get_images()`) rather than assuming it looks right.
- **Escaping**: all post-derived text is passed through `escapeHTML()` before insertion, *except* `step` block `paragraphs`, which are treated as trusted raw HTML (so `<code>` tags work) — never put user-supplied or untrusted content there.

## Automated Post Generation Workflow

This section documents the standard process for generating a day's post — both
the Instagram carousel and the matching website article — so this workflow is
consistent every time it's triggered, whether by the project owner or a future
session picking this up cold.

### How this gets triggered

The website grows automatically as posts are added — no manual review gate,
**as long as automated verification passes** (see step 7). Instagram is a
separate, always-manual step: **this workflow never posts to Instagram under
any circumstances.** The owner reviews the generated slides and posts them
manually, on their own schedule.

### Standard workflow for "make today's post"

The Instagram carousel is always exactly 4 slides, each rendered with
`instagram/generate_post.py`, following this fixed structure:

- **Slide 1 — Hook.** A `tag_pill()` labeling the content type (e.g. "QUICK
  QUESTION", "MYTH BUSTED", "TRUE STORY", "STAY SAFE") plus one short,
  attention-grabbing line — a question, a surprising fact, or a stat — that
  states the topic without giving away the fix. Ends with `draw_swipe_hook()`
  to pull the reader into slide 2. No body copy beyond the hook line itself.

- **Slide 2 — Why this matters.** Grounds the hook in a real stake or
  consequence: what actually happens if this goes unaddressed, in plain,
  non-alarmist language (per "Writing" in Utility & Content Philosophy — real
  risk, not fear-mongering). Ends with another `draw_swipe_hook()`.

- **Slide 3 — Main content.** The actual fact or fix — the one concrete,
  doable thing this post is teaching. This is the slide that has to stand
  alone if someone only reads one of the four. Ends with another
  `draw_swipe_hook()`.

- **Slide 4 — Close.** Wraps up with a one-line takeaway, a curiosity tease
  for tomorrow's post (mirrors the website's `next` box), and a plain
  Like / Comment / Follow prompt. This is the only slide with no
  `draw_swipe_hook()` call, since there's nothing after it to swipe to.

Every slide uses `base_card()` + `linux_chrome()` for the terminal-window
frame and `footer()` for the brand mark + slide counter (`"1/4"`–`"4/4"`),
matching every other slide already produced. Copy for all 4 slides is
written before any image is rendered, and follows the same tone/voice rules
as website articles — see "Writing" under Utility & Content Philosophy and
"Content conventions" for the shared voice, and the pillar table for which
tag color (`tag_pill(bg=...)`) matches which pillar.

### Standard steps

1. **Check `CALENDAR.md`** for the next day marked "Pending." If the day's
   pillar is Cyber News, or if today's slot includes Cyber News alongside
   another pillar, follow the "Sourcing a Cyber News story" process below
   before writing anything.

2. **Write the carousel copy** for all 4 slides, following the established
   structure (see "Standard workflow for 'make today's post'" earlier in this
   file, and the tone/voice rules in "Utility & Content Philosophy").

3. **Generate the 4 slides** using `instagram/generate_post.py` (a rendering
   library, not a script — `from generate_post import *`, see its module
   docstring for the exact usage pattern and the shared helpers it provides:
   `base_card`, `linux_chrome`, `tag_pill`, `wrap_text`, `draw_swipe_hook`,
   `clean_smiley`, `footer`, `verify_slide`). Save the output to
   `instagram/posts/day_NN_<topic-slug>/slide1.png` through `slide4.png`
   (paths relative to the repo root), plus a `caption.txt` in the same folder
   with the finished Instagram caption.

4. **Verify every slide** with `verify_slide()` before considering the post
   done — checks correct size (1080×1080) and confirms the image isn't
   blank. This step is non-negotiable; this project has hit blank/broken
   image bugs before.

5. **Write the matching website article** as a new entry in `posts.json`
   (repo root — this is a flat static site, there's no `website/`
   subdirectory), following the exact schema and block types (`step`,
   `compare`, `pattern-list`, `warn`, `checklist`, `next`) of existing
   entries. Include the `pillar`, `pillarLabel`, `pillarColor`, and
   `readMinutes` fields already established in the current schema.

6. **Update `CALENDAR.md`**, marking that day's row as "Done."

7. **Run automated verification, then merge only if everything passes:**
   - `posts.json` is valid JSON (parses without error)
   - The new post entry has every field the schema requires (`slug`,
     `filename`, `badge`, `freq`, `pillar`, `pillarLabel`, `pillarColor`,
     `readMinutes`, `stripeColor`, `tagColor`, `tag`, `title`, `titleAccent`,
     `listDesc`, `intro`, `statLine`, `sections`, `warn`, `checklist`, `next`)
   - All 4 carousel slide images pass `verify_slide()` (correct size, not
     blank)
   - `post.html?slug=<new-slug>` actually loads and renders without a
     JavaScript console error (serve locally and check — this is the exact
     class of bug that's bitten this project before, e.g. a missing schema
     field silently breaking the template)
   - **If every check passes:** commit, push directly, and merge into `main`
     without waiting for approval. The website update goes live automatically.
   - **If any check fails:** do NOT merge. Push the branch and open a PR
     anyway (so no work is lost), clearly report which check failed and why,
     and stop for the owner to review manually. Never merge on a partial
     pass.

8. **Report back** with a summary — either "verified and merged, live now" or
   "verification failed on [X], PR opened for review instead" — then stop.

### Sourcing a Cyber News story (when the day's pillar requires it)

Cyber News exists to cover **real, current stories that affect normal
people** — not deep technical CVE writeups aimed at security professionals.
When this pillar comes up:

1. **Search for a current cybersecurity story** (published within roughly the
   last 3-5 days) using these criteria, in priority order:
   - Affects a product, service, or company that ordinary people actually
     use (a bank, an airline, a major app, a retailer) — not enterprise-only
     infrastructure
   - Has a clear, explainable "what should I actually do about this" angle
   - Doesn't require prior security knowledge to understand the headline

2. **Preferred sources**, roughly in order of how consumer-relevant their
   coverage tends to be:
   - **BleepingComputer** — strong on breach news with practical detail
   - **Krebs on Security** — deep, credible, well-explained incident coverage
   - **The Verge / TechCrunch (security coverage)** — good at consumer framing
   - **Malwarebytes Labs blog** — written for a general audience already
   - **Hacker News (news.ycombinator.com)** — useful for surfacing what's
     trending, but many stories there are technical/developer-focused; only
     use a Hacker News story if it clearly meets criteria #1 and #2 above,
     don't use it just because it's popular there
   - Official statements from the affected company, if available, for
     verifying facts before writing about them

3. **Do not fabricate or guess at details.** If a search doesn't turn up a
   story that clearly meets the "affects normal people, explainable, recent"
   bar, say so explicitly in your response rather than stretching a marginal
   or overly technical story to fit. It's fine for a Cyber News slot to stay
   pending an extra day rather than force a weak story.

4. **Always cite the source** — include the outlet name and a link in the
   website article (and note it in the PR description), so the claim is
   verifiable and not just asserted.

5. **Follow the same "no fear-mongering, always pair with an action" rule**
   from the Content Philosophy section — a Cyber News post should end with
   something concrete the reader can actually do, not just "this is scary."

### Trigger prompt (for reference)

The owner will typically trigger this with something like:

> "Generate today's post — check CALENDAR.md for the next pending day, [if
> Cyber News: search for a real current story following the sourcing
> criteria in CLAUDE.md], write the carousel copy, generate all 4 slides,
> verify none are blank, write the matching posts.json entry, update
> CALENDAR.md, run all verification checks, and merge to main automatically
> if everything passes. If anything fails, open a PR instead and tell me
> exactly what failed. Don't touch Instagram — I'll post those myself
> whenever I'm ready."
