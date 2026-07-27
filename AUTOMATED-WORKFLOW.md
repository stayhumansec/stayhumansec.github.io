# Automated Post Generation Workflow

This document is the standard process for generating a day's post — the
website article, the Instagram carousel, and the Facebook, LinkedIn, and X
packages built from that same carousel — so this workflow is consistent
every time it's triggered, whether by the project owner or a future session
picking this up cold. `CLAUDE.md` links here rather than duplicating this
content; this file is the source of truth for the workflow itself.

## How this gets triggered

The website grows automatically as posts are added — no manual review gate,
**as long as automated verification passes** (see step 7). Social packaging
(Instagram, Facebook, LinkedIn, X) is a separate, always-manual step:
**this workflow never posts to any social platform under any circumstances.**
The owner reviews every generated slide, PDF, caption, and thread and posts
them manually, on their own schedule, per platform.

**Cyber News and AI News are a genuine 50/50, not a daily-vs-occasional
split.** They alternate daily — exactly one of the two runs on any given
day, never both, never neither. Concretely: odd calendar days get Cyber
News, even calendar days get AI News, and that assignment flips at the
start of each new month so neither pillar permanently sits on the
short end of a 7-day week. This is a hard rule, not a target to
approximate — the previous setup (Cyber News daily, AI News twice a
week) worked out to roughly 78/22 in practice, which is exactly the kind
of one-day-at-a-time drift that caused the imbalance documented in
`CLAUDE.md`'s "Content Balance" section in the first place. If a future
session is ever unsure which one today is, check yesterday's post: today
is whichever pillar *didn't* run yesterday.

## Standard workflow for "make today's post"

The Instagram carousel is always exactly 4 slides, each rendered with
`instagram/generate_post.py`, following this fixed structure:

- **Slide 1 — Hook.** A `tag_pill()` labeling the content type (e.g. "QUICK
  QUESTION", "MYTH BUSTED", "TRUE STORY", "STAY SAFE") plus one short,
  attention-grabbing line — a question, a surprising fact, or a stat — that
  states the topic without giving away the fix. Ends with `draw_swipe_hook()`
  to pull the reader into slide 2. No body copy beyond the hook line itself.

- **Slide 2 — Why this matters.** Grounds the hook in a real stake or
  consequence: what actually happens if this goes unaddressed, in plain,
  non-alarmist language (per "Writing" in `CLAUDE.md`'s Utility & Content
  Philosophy — real risk, not fear-mongering). Ends with another
  `draw_swipe_hook()`.

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
as website articles — see `CLAUDE.md`'s "Writing" and "Sounding like a
person, not a model" sections for the shared voice, and its pillar table for
which tag color (`tag_pill(bg=...)`) matches which pillar.

## Platform-specific packaging

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

## Standard steps

1. **Check `CALENDAR.md`** for the next day marked "Pending," then check
   which of Cyber News or AI News today's turn belongs to — they alternate
   daily (see "How this gets triggered" above for the exact 50/50 rule).
   Follow "Sourcing a Cyber News story" or "Sourcing an AI News story"
   below, whichever applies to today, before writing anything else (a day
   can carry its live-sourced story *and* its planned pillar topic at once
   if the calendar lines up that way — they're independent).

2. **Write the carousel copy** for all 4 slides, following the established
   structure (see "Standard workflow for 'make today's post'" earlier in this
   file, and the tone/voice rules in `CLAUDE.md`). Write for how much a slide
   can actually hold, not the bare minimum needed to state the fact —
   FILE_001's slide 1 (`instagram/posts/day_01_launch/slide1.png`) is the
   reference bar for "how much copy is enough." Then write the four
   platform captions/thread (Instagram, Facebook, LinkedIn, X) per the
   "Platform-specific packaging" spec above — same fact/fix, different tone
   per platform.

3. **Generate the 4 slides** using `instagram/generate_post.py` (a rendering
   library, not a script — `from generate_post import *`, see its module
   docstring for the exact usage pattern and the shared helpers it provides.
   **This is the standard, non-optional way every carousel gets generated
   from here forward** — every existing carousel from Day 2 onward
   (`day_02a_password_manager` through `day_07_deepfakes`, plus
   `cybernews_20260727_chickfila`) was retrofitted onto it. `day_01_launch`
   was intentionally left as-is (out of scope, and a bespoke 5-slide
   structure unlike every other day's 4) — its slide 1 stays the
   copy-substantiality reference bar regardless. There is no "skip the
   auto-fit step" path for a new post:
   `base_card`, `linux_chrome`, `tag_pill`, `wrap_text`, `draw_swipe_hook`,
   `clean_smiley`, `footer`, `verify_slide`, `save_pdf_carousel`,
   `verify_pdf_carousel`, `compute_fill_ratio`, `auto_fit_body`,
   `terminal_callout`). For any slide with body copy of variable length
   (i.e. slides 2 and 3 — the hook and close slides are short by design and
   don't need this), render it through `auto_fit_body()` instead of a
   single fixed font size/line spacing. It closes empty vertical space in
   two stages: first by growing the text itself (font size, then line
   spacing, within bounded limits — capped at 48px so slides don't read as
   oversized), and if that still leaves real empty space, by passing
   `callout_lines` — a real stat or status line relevant to the slide's
   topic (e.g. `["risk_level: HIGH", "3 in 4 reused passwords get tried
   elsewhere within 24h"]`) — so a small bordered box styled as terminal
   output (matching `linux_chrome()`'s existing `$ ` prompt look) finishes
   the gap with real information instead of a large dead zone below the
   copy. Save the output to
   `instagram/posts/day_NN_<topic-slug>/slide1.png` through `slide4.png`
   (paths relative to the repo root). In that same folder, write
   `caption.txt` (Instagram), `facebook_caption.txt`, build `linkedin.pdf`
   from the same 4 slides via `save_pdf_carousel()`, write
   `linkedin_caption.txt`, and write `x_thread.txt`.

4. **Verify every slide** with `verify_slide()` before considering the post
   done — checks correct size (1080×1080) and confirms the image isn't
   blank. This step is non-negotiable; this project has hit blank/broken
   image bugs before. **Also check the `report["ok"]` returned by
   `auto_fit_body()` for every slide it was used on.** If `False`, the copy
   itself is too thin to fill the slide within `auto_fit_body()`'s bounded
   growth range — go back and write more substantial copy for that slide
   (per step 2 above) rather than shipping it sparse or forcing an
   artificially large font. Note any such flag in the PR description. Also
   run `verify_pdf_carousel(path, 4)` on `linkedin.pdf` to confirm it has
   exactly 4 pages, each 1080×1080, and confirm `facebook_caption.txt`,
   `linkedin_caption.txt`, and `x_thread.txt` all exist and are non-empty.

5. **Write the matching website article** as a new entry in `posts.json`
   (repo root — this is a flat static site, there's no `website/`
   subdirectory), following the exact schema and block types (`step`,
   `compare`, `pattern-list`, `warn`, `checklist`, `next`) of existing
   entries. Include the `pillar`, `pillarLabel`, `pillarColor`, and
   `readMinutes` fields already established in the current schema. **If the
   post's pillar is `cyber-news` or `ai-news`, also include `sourceUrl`,
   `sourceName`, and `date`** (see "Sourcing a Cyber News story" /
   "Sourcing an AI News story" below) — these three fields are what power
   the site's News page and are required, not optional, on any news-pillar
   post.

6. **Update `CALENDAR.md`**, marking that day's row as "Done."

7. **Run automated verification, then merge only if everything passes:**
   - `posts.json` is valid JSON (parses without error)
   - The new post entry has every field the schema requires (`slug`,
     `filename`, `badge`, `freq`, `pillar`, `pillarLabel`, `pillarColor`,
     `readMinutes`, `stripeColor`, `tagColor`, `tag`, `title`, `titleAccent`,
     `listDesc`, `intro`, `statLine`, `sections`, `warn`, `checklist`, `next`)
   - **If the pillar is `cyber-news` or `ai-news`: `sourceUrl`, `sourceName`,
     and `date` are all present and non-empty.** Missing any of the three on
     a news-pillar post is a hard verification failure — do not merge.
   - All 4 carousel slide images pass `verify_slide()` (correct size, not
     blank)
   - Any slide rendered via `auto_fit_body()` (slides 2/3, per step 3 above)
     has `report["ok"] == True`, or the PR description explicitly notes why
     it doesn't (i.e. the copy was judged too short and needs a rewrite, not
     a silently-shipped sparse slide)
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

## Sourcing a Cyber News story (alternating days, 50/50 with AI News)

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
   - **The Hacker News (thehackernews.com)** — primary outlet to check first;
     broad, frequently-updated breach/vulnerability coverage, but skews
     technical, so still filter through criteria #1 and #2 above rather than
     using a story just because it's there
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
   - **Cross-check across at least two of the above outlets when possible**
     before writing the post — this project has previously corroborated a
     story (e.g. the Chick-fil-A credential stuffing post) across multiple
     sources rather than relying on a single outlet, and that's the standard
     to keep, not a one-off.

3. **Do not fabricate or guess at details.** If a search doesn't turn up a
   story that clearly meets the "affects normal people, explainable, recent"
   bar, say so explicitly in your response rather than stretching a marginal
   or overly technical story to fit. It's fine for a Cyber News slot to stay
   pending an extra day rather than force a weak story.

4. **Always cite the source, and capture it structurally, not just in
   prose.** Set `sourceName` (the outlet's name, e.g. `"BleepingComputer"`)
   and `sourceUrl` (a direct link to the specific story, not the outlet's
   homepage) on the `posts.json` entry, in addition to mentioning the outlet
   naturally in the article text and the PR description. Both fields are
   required for this pillar — see the verification checklist above.

5. **Follow the same "no fear-mongering, always pair with an action" rule**
   from `CLAUDE.md`'s Content Philosophy section — a Cyber News post should
   end with something concrete the reader can actually do, not just "this is
   scary."

## Sourcing an AI News story (alternating days, 50/50 with Cyber News)

AI News exists specifically to close the gap documented in `CLAUDE.md`'s
"Content Balance" section: **what happens to a normal person's own data
when they use an AI tool.** Two categories of story explicitly do NOT
qualify for this slot, even though both are AI-related and both are
tempting to reach for:

- **General AI industry news** — model releases, benchmarks, funding
  rounds, capability demos. Not about a person's own data at all.
- **AI-as-attack-tool stories** — deepfakes, voice cloning, AI-written
  phishing. These are real and worth covering, but that's what `ai-watch`
  (the planned, evergreen pillar) already does — routing them into AI News
  instead would quietly recreate the exact 100%-AI-as-attacker imbalance
  the "Content Balance" audit found and this pillar was created to fix.

AI News alternates daily with Cyber News (see "How this gets triggered"
above), is never pre-written in `CALENDAR.md`, and pairs alongside whatever
else is scheduled that day rather than taking its own dedicated slot — same
mechanism as Cyber News. **Uses its own `ai-news` pillar** (see `CLAUDE.md`'s
pillar table) — distinct from `ai-watch`, so the News page can cleanly tell
"this is breaking news" apart from "this is a planned AI Watch explainer,"
even though both currently share the violet accent color.

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
   - **The Hacker News (thehackernews.com)** — occasionally covers an AI
     data-handling story (e.g. a chatbot provider's policy change), but it's
     primarily a Cyber News outlet — only pull from it here if a story
     genuinely meets criterion #1 (a person's own data), not general AI
     security coverage

3. **Do not fabricate or guess at details.** If a search doesn't turn up a
   story that clearly meets the "your own data, explainable, recent" bar,
   say so explicitly and skip that slot rather than stretching a general
   AI-industry story to fit — a generic "new model released" story does not
   qualify, even if it's popular that week.

4. **Always cite the source, and capture it structurally, not just in
   prose.** Set `sourceName` and `sourceUrl` on the `posts.json` entry (same
   requirement as Cyber News above), in addition to mentioning the outlet in
   the article text and the PR description.

5. **Follow the same "no fear-mongering, always pair with an action" rule** —
   an AI News post should end with something concrete the reader can
   actually check or change, not just "here's what AI knows about you now."

## Also today (curated headline briefs — `newsBriefs.json`)

Separate from the one authored Cyber News/AI News post per day above, the
News page also shows an "Also today" strip of **3-5 bare headlines** —
headline text, source name, and an outbound link only, no write-up, no our
own commentary. This is deliberately not another authored `posts.json`
entry: it's raw curation, clearly labeled on `news.html` as headlines we
found and linked, not stories we wrote about. Data lives in
`newsBriefs.json` at the repo root, shape:

```json
{ "briefs": [
  { "id": "brief-YYYY-MM-DD-slug", "category": "cyber"|"ai", "headline": "...",
    "sourceName": "...", "sourceUrl": "...", "date": "YYYY-MM-DD" }
] }
```

Pull these **during the same session that generates the day's authored
post** — this is a static site with no backend, so there is no live
client-side fetching; a future session (human or automated) searches the
sources below and writes the results straight into `newsBriefs.json`, the
same static-data pattern `posts.json` already uses.

**Same hard 50/50 rule as Cyber News/AI News applies here**, applied to the
3-5 headlines as a set: aim for roughly half cyber, half AI-privacy. If a
given day genuinely doesn't have enough AI-privacy headlines that clear the
bar, **show fewer total headlines that day instead of padding the gap**
with an off-topic AI story or an extra cybersecurity one — same principle
as "don't stretch a marginal story to fit" above, just applied to a list
instead of a single post.

**Sources — cybersecurity half:**
- **Hacker News (news.ycombinator.com)** — public Algolia API, no key
  needed: `hn.algolia.com/api/v1/search_by_date?tags=story&query=security`.
  This is the actual news.ycombinator.com link aggregator — distinct from
  the outlet below despite the near-identical name.
- **The Hacker News (thehackernews.com)** — RSS feed:
  `thehackernews.com/feeds/posts/default`
- **BleepingComputer** — RSS feed: `bleepingcomputer.com/feed/`
- **Krebs on Security** — RSS feed: `krebsonsecurity.com/feed/`

Filter all four through the same "affects normal people, explainable"
criteria as the full Cyber News post above — a headline strip is not an
excuse to relax that bar.

**Sources — AI-privacy half (genuinely the harder side to fill):**
- **EFF Deeplinks** (`eff.org/rss/updates.xml`) — gets priority when
  multiple qualifying stories exist on the same day. Of the four core
  outlets, it's the only one where privacy/data-rights is the outlet's
  core beat rather than one topic among general tech coverage — WIRED and
  The Verge cover AI broadly with privacy as one angle among many, The
  Markup is investigative but low-volume. EFF being privacy-first
  end-to-end makes it the safest tie-breaker for staying on-topic.
- **The Markup** (`themarkup.org`) — no reliable RSS cadence, check
  `themarkup.org/series/artificial-intelligence` directly
- **WIRED** (Privacy/AI tags) and **The Verge** (AI tag) — higher volume,
  filter hard against criterion #1 from the AI News sourcing rules (a
  person's own data through an AI feature, not general AI industry news)
- **Fallback**: when none of the above four have a qualifying story on a
  given day — which will happen — a reputable dedicated tech-news outlet
  (e.g. Tech Times, eWeek) covering a genuinely on-topic story (a chatbot
  privacy fine, an AI feature's data-handling change) is an acceptable
  fifth-tier source. This is a real, structural scarcity on the AI-privacy
  side, not a one-off gap — expect the AI-privacy half of this list to run
  short, or dip to this fallback tier, more often than the cyber half does.

**Verification before merging:** confirm `newsBriefs.json` is valid JSON,
every `sourceUrl` is a direct link to the specific story (not an outlet
homepage), and the cyber/AI split (or the honest shortfall) is reflected
accurately — don't force the count.

The homepage's typed-headline ticker (`initNewsTicker` in `site.js`) reads
from both the day's authored post and `newsBriefs.json`, so it has more
than one headline per day to cycle through.

## Trigger prompt (for reference)

The owner will typically trigger this with something like:

> "Generate today's post — check CALENDAR.md for the next pending day, check
> whether today is a Cyber News day or an AI News day (they alternate
> daily), and search for a real current story following the matching
> sourcing criteria in AUTOMATED-WORKFLOW.md, write the carousel copy plus all four platform
> captions/thread, generate all 4 slides, build the LinkedIn PDF, verify
> none of the slides are blank and the PDF/captions/thread all check out,
> write the matching posts.json entry (with sourceUrl/sourceName/date if
> it's a news post), update CALENDAR.md, run all verification checks, and
> merge to main automatically if everything passes. If anything fails, open
> a PR instead and tell me exactly what failed. Don't touch Instagram,
> Facebook, LinkedIn, or X — I'll post those myself whenever I'm ready."
