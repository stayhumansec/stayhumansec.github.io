#!/usr/bin/env python3
"""Regenerate sitemap.xml and feed.xml from posts.json.

This site has no build step, so sitemap.xml/feed.xml are static snapshots.
Run this script (or let the "Regenerate feeds" GitHub Action run it for you)
whenever posts.json changes.
"""
import json
import os
from datetime import datetime, timezone
from xml.sax.saxutils import escape

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE_URL = "https://stayhumansec.github.io"
TODAY = datetime.now(timezone.utc).strftime("%Y-%m-%d")

STATIC_PAGES = [
    ("", "1.0", "daily"),
    ("posts.html", "0.9", "daily"),
    ("news.html", "0.9", "daily"),
    ("notes.html", "0.6", "weekly"),
    ("toolkit.html", "0.7", "monthly"),
    ("tools.html", "0.7", "monthly"),
    ("prompts.html", "0.6", "monthly"),
    ("glossary.html", "0.6", "monthly"),
    ("password-coach.html", "0.5", "monthly"),
    ("recovery-kit.html", "0.5", "monthly"),
    ("breach-check.html", "0.5", "monthly"),
    ("ask.html", "0.5", "monthly"),
    ("privacy.html", "0.3", "yearly"),
]


def load_posts():
    with open(os.path.join(ROOT, "posts.json"), "r", encoding="utf-8") as f:
        data = json.load(f)
    return [p for p in data["posts"] if p.get("badge") == "live"]


def build_sitemap(posts):
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for page, priority, changefreq in STATIC_PAGES:
        lines.append("  <url>")
        lines.append(f"    <loc>{SITE_URL}/{page}</loc>")
        lines.append(f"    <lastmod>{TODAY}</lastmod>")
        lines.append(f"    <changefreq>{changefreq}</changefreq>")
        lines.append(f"    <priority>{priority}</priority>")
        lines.append("  </url>")
    for post in posts:
        lastmod = post.get("date") or TODAY
        lines.append("  <url>")
        lines.append(f"    <loc>{SITE_URL}/post.html?slug={escape(post['slug'])}</loc>")
        lines.append(f"    <lastmod>{lastmod}</lastmod>")
        lines.append("    <changefreq>monthly</changefreq>")
        lines.append("    <priority>0.8</priority>")
        lines.append("  </url>")
    lines.append("</urlset>")
    return "\n".join(lines) + "\n"


def rfc822(date_str):
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return dt.strftime("%a, %d %b %Y 00:00:00 GMT")


def build_feed(posts):
    build_date = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">',
             "  <channel>",
             "    <title>stay(human).sec</title>",
             f"    <link>{SITE_URL}/</link>",
             "    <description>Cybersecurity, AI, and privacy explained properly — one fact, one fix, every day.</description>",
             "    <language>en-us</language>",
             '    <atom:link href="{}/feed.xml" rel="self" type="application/rss+xml"/>'.format(SITE_URL),
             f"    <lastBuildDate>{build_date}</lastBuildDate>"]
    for post in posts:
        link = f"{SITE_URL}/post.html?slug={escape(post['slug'])}"
        desc = post.get("listDesc") or post.get("intro") or ""
        lines.append("    <item>")
        lines.append(f"      <title>{escape(post['title'])}</title>")
        lines.append(f"      <link>{link}</link>")
        lines.append(f'      <guid isPermaLink="true">{link}</guid>')
        lines.append(f"      <description>{escape(desc)}</description>")
        if post.get("date"):
            lines.append(f"      <pubDate>{rfc822(post['date'])}</pubDate>")
        lines.append("    </item>")
    lines.append("  </channel>")
    lines.append("</rss>")
    return "\n".join(lines) + "\n"


def main():
    posts = load_posts()
    with open(os.path.join(ROOT, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write(build_sitemap(posts))
    with open(os.path.join(ROOT, "feed.xml"), "w", encoding="utf-8") as f:
        f.write(build_feed(posts))
    print(f"Regenerated sitemap.xml and feed.xml from {len(posts)} live posts.")


if __name__ == "__main__":
    main()
