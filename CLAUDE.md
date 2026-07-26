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

AI News posts (see "Content Balance" below) use the existing `ai-watch` pillar/color rather than a new pillar slug — same reasoning as not adding a dedicated Privacy pillar: it delivers the content without a new color, new pillar-grid card, or other site-structure change to maintain.

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

This section documents the standard process for generating a day's post —
the website article, the Instagram carousel, and the Facebook, LinkedIn, and
X packages built from that same carousel — so this workflow is consistent
every time it's triggered, whether by the project owner or a future session
picking this up cold.

### How this gets triggered

The website grows automatically as posts are added — no manual review gate,
**as long as automated verification passes** (see step 7). Social packaging
(Instagram, Facebook, LinkedIn, X) is a separate, always-manual step:
**this workflow never posts to any social platform under any circumstances.**
The owner reviews every generated slide, PDF, caption, and thread and posts
them manually, on their own schedule, per platform.

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

### Platform-specific packaging

Every day's post produces **four** platform variants from the same
underlying fact/fix — the content itself never changes, only tone and
format do. All four land in the same `instagram/posts/day_NN_<topic-slug>/`
folder alongside the slides, regardless of which platform they're for —
there's no per-platform subdirectory.

- **Instagram** — the 4 slides (`slide1.png`–`slide4.png`) described above,
  plus `caption.txt`: punchy, hook-first, matches the carousel's own pacing.

- **Facebook** — reuses the exact same 4 slide PNGs, no new images. Only
  `facebook_caption.txt` is new: same core fact/fix as the Instagram
  caption, but warmer and more community-oriented — a "share this with
  someone in your family" framing, since Facebook's audience skews older
  and more relationship-driven than Instagram's.

- **LinkedIn** — combines the same 4 slide PNGs into a single `linkedin.pdf`
  (LinkedIn's carousel format is a PDF document upload, not separate
  images), built with `save_pdf_carousel()` in `instagram/generate_post.py`
  and checked with `verify_pdf_carousel()` (confirms page count and that
  every page is 1080×1080 — both use Pillow's own multi-page PDF save, no
  extra dependency). `linkedin_caption.txt` is more narrative and
  first-person than Instagram's punchier hook style, with professional
  framing where it genuinely fits ("why this matters for your work life")
  — don't force the work-life angle onto a post where it doesn't apply.

- **X (Twitter)** — no new images at all. `x_thread.txt` is a numbered
  thread: tweet 1 is the hook (mirrors slide 1's punch), each following
  tweet covers one core point from the post (mirrors the swipe-hook pacing
  already established across the carousel), and the final tweet points to
  the website article for the full write-up. `slide1.png` can optionally be
  suggested as the hook tweet's attached image, but nothing new is rendered
  for it.

### Standard steps

1. **Check `CALENDAR.md`** for the next day marked "Pending." If the day's
   pillar is Cyber News, or if today's slot includes Cyber News alongside
   another pillar, follow the "Sourcing a Cyber News story" process below
   before writing anything. Separately, AI News runs twice a week regardless
   of what else is scheduled that day — check whether one of this week's two
   AI News slots is still open, and if so, follow "Sourcing an AI News
   story" below as well (a day can carry Cyber News, AI News, and its
   planned pillar topic all at once if the calendar lines up that way).

2. **Write the carousel copy** for all 4 slides, following the established
   structure (see "Standard workflow for 'make today's post'" earlier in this
   file, and the tone/voice rules in "Utility & Content Philosophy"). Then
   write the four platform captions/thread (Instagram, Facebook, LinkedIn,
   X) per the "Platform-specific packaging" spec above — same fact/fix,
   different tone per platform.

3. **Generate the 4 slides** using `instagram/generate_post.py` (a rendering
   library, not a script — `from generate_post import *`, see its module
   docstring for the exact usage pattern and the shared helpers it provides:
   `base_card`, `linux_chrome`, `tag_pill`, `wrap_text`, `draw_swipe_hook`,
   `clean_smiley`, `footer`, `verify_slide`, `save_pdf_carousel`,
   `verify_pdf_carousel`). Save the output to
   `instagram/posts/day_NN_<topic-slug>/slide1.png` through `slide4.png`
   (paths relative to the repo root). In that same folder, write
   `caption.txt` (Instagram), `facebook_caption.txt`, build `linkedin.pdf`
   from the same 4 slides via `save_pdf_carousel()`, write
   `linkedin_caption.txt`, and write `x_thread.txt`.

4. **Verify every slide** with `verify_slide()` before considering the post
   done — checks correct size (1080×1080) and confirms the image isn't
   blank. This step is non-negotiable; this project has hit blank/broken
   image bugs before. Also run `verify_pdf_carousel(path, 4)` on
   `linkedin.pdf` to confirm it has exactly 4 pages, each 1080×1080, and
   confirm `facebook_caption.txt`, `linkedin_caption.txt`, and
   `x_thread.txt` all exist and are non-empty.

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
   - `linkedin.pdf` passes `verify_pdf_carousel()` (4 pages, each 1080×1080)
   - `facebook_caption.txt`, `linkedin_caption.txt`, and `x_thread.txt` all
     exist in the day's folder and are non-empty
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

### Sourcing an AI News story (2x/week, when scheduled)

AI News exists specifically to close the gap documented in "Content
Balance" above: **what happens to a normal person's own data when they use
an AI tool** — not general AI industry news (model releases, benchmarks,
funding rounds, capability demos). It runs twice a week, is never
pre-written in `CALENDAR.md`, and pairs alongside whatever else is
scheduled that day rather than taking its own dedicated slot — same
mechanism as Cyber News. Uses the existing `ai-watch` pillar/color.

1. **Search for a current story** (published within roughly the last 3-5
   days) using these criteria, in priority order:
   - Involves what happens to a person's *own* data through an AI feature
     they use — a chatbot conversation, an AI photo/video tool, a voice
     assistant, an app that added an AI feature and changed its data
     handling, a policy or legal change around AI training data
   - Has a clear, explainable "what should I actually do about this" angle
     (a setting to check, an opt-out to find, a habit to change)
   - Doesn't require prior AI or security knowledge to understand the
     headline

2. **Preferred sources**, roughly in order of how consumer-relevant their
   coverage tends to be:
   - **The Markup, WIRED (privacy/AI coverage), The Verge** — strong on
     consumer-facing AI/privacy stories with practical detail
   - **Electronic Frontier Foundation (eff.org)** — deep, credible coverage
     of data rights and AI policy, written to be broadly understandable
   - **Official statements, privacy policy changes, or terms-of-service
     updates from the company involved** — for verifying facts and for
     stories where the "news" is the company's own policy change
   - **Hacker News (news.ycombinator.com)** — useful for surfacing what's
     trending, but only use a story from here if it clearly meets criteria
     #1 and #2 above, same caveat as Cyber News

3. **Do not fabricate or guess at details.** If a search doesn't turn up a
   story that clearly meets the "your own data, explainable, recent" bar,
   say so explicitly and skip that slot rather than stretching a general
   AI-industry story to fit — a generic "new model released" story does not
   qualify, even if it's popular that week.

4. **Always cite the source** — include the outlet name and a link in the
   website article (and note it in the PR description).

5. **Follow the same "no fear-mongering, always pair with an action" rule** —
   an AI News post should end with something concrete the reader can
   actually check or change, not just "here's what AI knows about you now."

### Trigger prompt (for reference)

The owner will typically trigger this with something like:

> "Generate today's post — check CALENDAR.md for the next pending day, [if
> Cyber News: search for a real current story following the sourcing
> criteria in CLAUDE.md], [if an AI News slot is open this week: search for
> a real AI-and-your-own-data story following the same kind of criteria],
> write the carousel copy plus all four platform
> captions/thread, generate all 4 slides, build the LinkedIn PDF, verify
> none of the slides are blank and the PDF/captions/thread all check out,
> write the matching posts.json entry, update CALENDAR.md, run all
> verification checks, and merge to main automatically if everything
> passes. If anything fails, open a PR instead and tell me exactly what
> failed. Don't touch Instagram, Facebook, LinkedIn, or X — I'll post those
> myself whenever I'm ready."
