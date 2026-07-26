# Content Calendar — 4 Weeks (Days 1-28)

Single source of truth for "what's today's topic." Update the Status column as
days are completed. Cyber News and AI News are intentionally never pre-written
here — see the notes at the bottom.

## Week 1

| Day | Pillar | Topic | Status |
|---|---|---|---|
| 1 | Launch | Introduction post | ✅ Done |
| 2 | Stay Safe | Use a password manager | ✅ Done |
| 2 | Cyber Basics | What is smishing? | ✅ Done |
| 3 | Myth Busting | "Incognito mode makes you anonymous" — busted | ✅ Done |
| 4 | AI Watch | AI voice cloning & the "emergency call" scam | ✅ Done |
| 5 | Stay Safe | Turn on 2FA — what it actually protects | ✅ Done |
| 6 | Case File | Anatomy of a real phishing email, line by line | ✅ Done |
| 7 | AI Watch | Deepfakes: how to spot one in 2026 | ✅ Done |

## Week 2

| Day | Pillar | Topic | Status |
|---|---|---|---|
| 8 | Deep Dive | Ransomware: how it spreads, one infographic | Pending |
| 9 | AI Watch | What actually happens to what you type into an AI chatbot | Pending |
| 10 | Cyber Basics | 2FA vs MFA — what's the actual difference | Pending |
| 11 | Myth Busting | "Free VPNs are safe because they're free" — busted | Pending |
| 12 | Stay Safe | Review your app permissions (the 5-minute check) | Pending |
| 13 | Story Time | A real (lighthearted) social engineering near-miss | Pending |
| 14 | AI Watch | "Anonymized" data in the AI era — is it really anonymous? | Pending |

## Week 3

| Day | Pillar | Topic | Status |
|---|---|---|---|
| 15 | Cyber Basics | What is a VPN actually protecting you from? | Pending |
| 16 | AI Watch | What AI photo/video tools actually keep from what you upload | Pending |
| 17 | Stay Safe | Passkeys — the password killer, explained simply | Pending |
| 18 | Myth Busting | "My data isn't valuable, why would anyone target me?" — busted | Pending |
| 19 | Case File | Anatomy of a SIM-swap attack | Pending |
| 20 | AI Watch | The AI features quietly added to apps you already use | Pending |
| 21 | Cyber Basics | What is encryption? (the lock-and-key analogy) | Pending |

## Week 4

| Day | Pillar | Topic | Status |
|---|---|---|---|
| 22 | Stay Safe | Lock your phone with more than a 4-digit PIN | Pending |
| 23 | AI Watch | Voice assistants: what's actually recorded vs. processed on your device | Pending |
| 24 | Myth Busting | "Private browsing stops AI chatbots from remembering what I told them" — busted | Pending |
| 25 | Cyber Basics | What is malware? (virus vs. spyware vs. ransomware) | Pending |
| 26 | Case File | A privacy incident, broken down — what actually happens when an app's data ends up somewhere you didn't expect | Pending |
| 27 | Stay Safe | Turn on automatic software updates — why it matters | Pending |
| 28 | Story Time | A real (lighthearted) near-miss in the family group chat | Pending |

## Pillar coverage check (all 9 represented across 28 days)

| Pillar | Cadence | Days used |
|---|---|---|
| 🗞️ Cyber News | Daily | Not pre-planned — see note below |
| 🤖 AI News | 2x/week | Not pre-planned — see note below |
| 🛡️ Stay Safe | Daily | 2, 5, 12, 17, 22, 27 |
| 📘 Cyber Basics | Daily | 2, 10, 15, 21, 25 |
| 🤖 AI Watch | Weekly (elevated) | 4, 7, 9, 14, 16, 20, 23 |
| ❌ Myth Busting | Weekly | 3, 11, 18, 24 |
| 🕵️ Case File | Weekly | 6, 19, 26 |
| 🔬 Deep Dive | Occasional | 8 |
| 😄 Story Time | Occasional | 13, 28 |

## Content-balance check (cybersecurity / privacy / AI-privacy-intersection)

This calendar was deliberately rebalanced — see CLAUDE.md's "Content Balance"
section for the full reasoning. Rough split across all 28 days: **11
cybersecurity, 9 privacy, 8 AI** (6 of those 8 AI Watch slots are specifically
AI-and-your-own-data topics — what happens to a chatbot conversation, an
AI photo upload, a voice assistant recording, an app's quietly-added AI
feature — not AI-as-attacker). This is a real shift from the original
calendar, which had AI Watch at 100% AI-as-attacker topics and zero
AI-privacy-intersection coverage.

## A note on Cyber News

Cyber News is deliberately **not** pre-written here — it's always today's real,
current story, found the morning it's posted. See `AUTOMATED-WORKFLOW.md` for
exactly how Claude Code should find and select that story when this pillar
comes up (including which days can pair Cyber News alongside a day's other
planned pillar, since it doesn't need its own dedicated day the way the
others do). Every Cyber News post requires `sourceUrl`, `sourceName`, and
`date` in its `posts.json` entry — see `AUTOMATED-WORKFLOW.md`'s
verification checklist.

## A note on AI News

AI News works the same way as Cyber News, but twice a week instead of daily,
uses its own `ai-news` pillar (violet, shared with `ai-watch`), and is
scoped specifically to **AI-and-your-own-data** stories — not general AI
industry news (model releases, benchmarks, funding). It's always today's
real, current story, found the day it's posted, and pairs alongside whatever
else is scheduled that day rather than taking its own dedicated slot. Same
`sourceUrl`/`sourceName`/`date` requirement as Cyber News. See
`AUTOMATED-WORKFLOW.md`'s "Sourcing an AI News story" section for the exact
criteria.
