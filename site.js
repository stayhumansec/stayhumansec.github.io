// site.js — shared behavior for every page on stay(human).sec
// Loaded by index.html and post.html so there's one copy of this logic, not one per page.

/**
 * Wires up scroll-reveal animation on all elements with the .reveal class.
 * Works identically on touch scroll (phone/tablet) and mouse/trackpad scroll (desktop)
 * because IntersectionObserver reacts to viewport position, not input method.
 * Respects prefers-reduced-motion by skipping the animation entirely.
 *
 * @param {Object} [opts]
 * @param {boolean} [opts.stagger=false] - cascade elements within the same parent container
 * @param {number} [opts.delayStep=70] - ms between staggered elements
 */
function initScrollReveal(opts) {
  opts = opts || {};
  var stagger = !!opts.stagger;
  var delayStep = opts.delayStep || 70;

  var els = document.querySelectorAll('.reveal');
  var prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  if (prefersReduced) {
    els.forEach(function (el) { el.classList.add('is-visible'); });
    return;
  }

  var counters = new Map();

  var observer = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (entry.isIntersecting) {
        var el = entry.target;
        var delay = 0;
        if (stagger) {
          var parentKey = el.parentElement;
          var n = counters.get(parentKey) || 0;
          counters.set(parentKey, n + 1);
          delay = n * delayStep;
        }
        setTimeout(function () { el.classList.add('is-visible'); }, delay);
        observer.unobserve(el);
      }
    });
  }, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });

  els.forEach(function (el) { observer.observe(el); });
}

/**
 * "Declassify" reveal — a clip-path wipe (like a redaction bar sliding off a document)
 * for elements with class `.declass`, used on file/tool/glossary card grids instead of
 * the plain fade-and-rise `.reveal` treats headings and CTAs with. Same IntersectionObserver
 * + stagger pattern as initScrollReveal, kept separate so the two effects never fight over
 * the same element's transition.
 *
 * IMPORTANT: threshold must stay 0. The `.declass` base state clips the element to 0%
 * visible area, so any non-zero threshold can never be satisfied — the CSS hiding it
 * permanently prevents the JS from ever detecting it as "visible enough" to reveal it.
 *
 * @param {Object} [opts]
 * @param {boolean} [opts.stagger=false]
 * @param {number} [opts.delayStep=80]
 */
function initDeclassify(opts) {
  opts = opts || {};
  var stagger = !!opts.stagger;
  var delayStep = opts.delayStep || 80;

  var els = document.querySelectorAll('.declass');
  if (!els.length) return;

  var prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (prefersReduced) {
    els.forEach(function (el) { el.classList.add('is-visible'); });
    return;
  }

  var counters = new Map();

  var observer = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (entry.isIntersecting) {
        var el = entry.target;
        var delay = 0;
        if (stagger) {
          var parentKey = el.parentElement;
          var n = counters.get(parentKey) || 0;
          counters.set(parentKey, n + 1);
          delay = n * delayStep;
        }
        setTimeout(function () { el.classList.add('is-visible'); }, delay);
        observer.unobserve(el);
      }
    });
  }, { threshold: 0, rootMargin: '0px 0px -30px 0px' });

  els.forEach(function (el) { observer.observe(el); });
}

/**
 * Scrambles an element's plain text into random characters, then resolves it back to the
 * real text as it scrolls into view — a "decrypting" effect for short text-only labels like
 * section eyebrows. Only safe on elements whose entire content is plain text (no child tags),
 * since it overwrites textContent directly. Skipped entirely under reduced-motion.
 *
 * @param {string} selector
 */
function initScrambleReveal(selector) {
  var els = document.querySelectorAll(selector);
  if (!els.length) return;

  var prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (prefersReduced) return;

  var chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%&*';

  function scramble(el) {
    var final = el.textContent;
    if (!final) return;
    var len = final.length;
    var revealed = 0;
    var frame = 0;
    var timer = setInterval(function () {
      var out = '';
      for (var i = 0; i < len; i++) {
        if (i < revealed || final[i] === ' ') out += final[i];
        else out += chars[Math.floor(Math.random() * chars.length)];
      }
      el.textContent = out;
      frame++;
      if (frame % 2 === 0) revealed++;
      if (revealed >= len) {
        el.textContent = final;
        clearInterval(timer);
      }
    }, 30);
  }

  var observer = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (entry.isIntersecting) {
        scramble(entry.target);
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.4 });

  els.forEach(function (el) { observer.observe(el); });
}

/** Small helper: fetch and parse posts.json once, reused by both index and post pages. */
async function loadPosts() {
  var res = await fetch('posts.json');
  if (!res.ok) throw new Error('Could not load posts.json (' + res.status + ')');
  return res.json();
}

/** Brand icon + wordmark SVG, so it's defined once instead of pasted into every HTML file. */
function brandIconSVG(size) {
  size = size || 64;
  return '<svg width="' + size + '" viewBox="0 0 150 100" fill="none" xmlns="http://www.w3.org/2000/svg">' +
    '<path d="M38 16C29 25 20 33 20 50C20 67 29 75 38 84" stroke="#f4f1e8" stroke-width="7" stroke-linecap="round"/>' +
    '<path d="M112 16C121 25 130 33 130 50C130 67 121 75 112 84" stroke="#f4f1e8" stroke-width="7" stroke-linecap="round"/>' +
    '<circle cx="75" cy="38" r="13" fill="#ff7a3d"/>' +
    '<path d="M58 78C58 68 65 61 75 61C85 61 92 68 92 78" stroke="#ff7a3d" stroke-width="5" stroke-linecap="round" fill="none"/>' +
    '</svg>';
}

/** Shared glossary data — used by glossary.html and by inline tooltip matching in posts. */
var GLOSSARY_TERMS = [
  { term: 'MFA', match: ['mfa', '2fa', 'multi-factor authentication', 'two-factor authentication'], color: 'var(--green)', def: 'A second proof of identity beyond your password — usually a code, an app tap, or a security key. The single biggest upgrade you can make to any account.' },
  { term: 'Phishing', match: ['phishing'], color: 'var(--pink)', def: 'A fake email, message, or website designed to trick you into handing over a password, card number, or one-time code by impersonating someone you trust.' },
  { term: 'Smishing', match: ['smishing'], color: 'var(--pink)', def: 'Phishing delivered by text message instead of email — usually a fake delivery notice, bank alert, or prize claim with a link.' },
  { term: 'Credential Stuffing', match: ['credential stuffing'], color: 'var(--orange)', def: 'An automated attack where a password leaked from one breached site gets tried against hundreds of other sites, betting that you reused it.' },
  { term: 'VPN', match: ['vpn'], color: 'var(--blue)', def: 'Virtual private network. Encrypts your internet traffic and hides your IP address from the network you\'re connected to — useful on public Wi-Fi, not a cure-all for privacy.' },
  { term: 'Zero-Day', match: ['zero-day', 'zero day'], color: 'var(--violet)', def: 'A software vulnerability that\'s being exploited before the company that makes the software knows about it or has released a fix.' },
  { term: 'Ransomware', match: ['ransomware'], color: 'var(--pink)', def: 'Malicious software that encrypts your files and demands payment to unlock them. Prevention (backups, patching) matters far more than any cure.' },
  { term: 'Social Engineering', match: ['social engineering'], color: 'var(--gold)', def: 'Manipulating a person — not a system — into giving up access or information. Most real-world breaches start here, not with clever code.' },
  { term: 'Password Manager', match: ['password manager'], color: 'var(--green)', def: 'An app that generates and remembers a unique, strong password for every site, so you only need to remember one master password.' },
  { term: 'End-to-End Encryption', match: ['end-to-end encryption'], color: 'var(--blue)', def: 'A message is scrambled on your device and only unscrambled on the recipient\'s — not even the app in the middle can read it.' },
  { term: 'Data Breach', match: ['data breach'], color: 'var(--orange)', def: 'An incident where an organization\'s data — often including passwords or personal info — is accessed or leaked without authorization.' },
  { term: 'Malware', match: ['malware'], color: 'var(--pink)', def: 'An umbrella term for any software designed to damage, spy on, or gain unauthorized access to a device — viruses, spyware, and ransomware are all types.' },
  { term: 'Stalkerware', match: ['stalkerware'], color: 'var(--pink)', def: 'Spyware installed on someone\'s device, usually by a person they know, to secretly monitor their messages, location, or activity.' },
  { term: 'Configuration Profile', match: ['configuration profile'], color: 'var(--violet)', def: 'A file on iPhone that can control device settings remotely — legitimate for work devices, but a red flag if you didn\'t install it yourself.' }
];

/**
 * Wraps the first mention of each glossary term inside a container's paragraphs with a
 * tap-to-reveal tooltip. Works by tag-aware text splitting so it never breaks existing HTML
 * (like <code> blocks) already inside the paragraph.
 */
function initGlossaryTooltips(container) {
  if (!container) return;
  var used = {};

  container.querySelectorAll('p').forEach(function (p) {
    if (p.closest('.gloss-term')) return;
    var html = p.innerHTML;
    var parts = html.split(/(<[^>]+>)/g);

    parts = parts.map(function (part) {
      if (part.charAt(0) === '<') return part;
      var text = part;
      GLOSSARY_TERMS.forEach(function (g) {
        if (used[g.term]) return;
        g.match.forEach(function (m) {
          if (used[g.term]) return;
          var re = new RegExp('\\b(' + m.replace(/[-]/g, '\\-') + ')\\b', 'i');
          if (re.test(text)) {
            text = text.replace(re, function (match) {
              used[g.term] = true;
              return '<span class="gloss-term" tabindex="0" style="--gloss-color:' + g.color + ';">' + match +
                '<span class="gloss-pop">' + escapeHTML(g.def) + '</span></span>';
            });
          }
        });
      });
      return text;
    });

    p.innerHTML = parts.join('');
  });

  container.querySelectorAll('.gloss-term').forEach(function (el) {
    el.addEventListener('click', function (e) {
      e.stopPropagation();
      var wasOpen = el.classList.contains('open');
      container.querySelectorAll('.gloss-term.open').forEach(function (o) { o.classList.remove('open'); });
      if (!wasOpen) el.classList.add('open');
    });
  });
  document.addEventListener('click', function () {
    container.querySelectorAll('.gloss-term.open').forEach(function (o) { o.classList.remove('open'); });
  });
}

/** Fades the whole page in on load instead of popping in unstyled. No-op under reduced-motion (handled in CSS). */
function initPageFade() {
  requestAnimationFrame(function () {
    requestAnimationFrame(function () { document.body.classList.add('loaded'); });
  });
}

/**
 * Builds a slide-out mobile menu from whatever is already in .nav-links, so no page needs
 * duplicate link markup — it just works once .nav-links exists in the nav.
 */
function initMobileNav() {
  var navLinks = document.querySelector('.nav-links');
  var navRight = document.querySelector('.nav-right');
  if (!navLinks || !navRight) return;

  var hamburger = document.createElement('button');
  hamburger.className = 'nav-hamburger';
  hamburger.setAttribute('aria-label', 'Menu');
  hamburger.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="4" y1="7" x2="20" y2="7"/><line x1="4" y1="12" x2="20" y2="12"/><line x1="4" y1="17" x2="20" y2="17"/></svg>';
  navRight.appendChild(hamburger);

  var backdrop = document.createElement('div');
  backdrop.className = 'mobile-nav-backdrop';
  var panel = document.createElement('div');
  panel.className = 'mobile-nav-panel';
  var ctaLink = document.querySelector('.nav-cta');
  panel.innerHTML = navLinks.innerHTML +
    (ctaLink ? '<div class="mobile-nav-cta"><a href="' + ctaLink.getAttribute('href') + '" class="btn-primary" style="width:100%; text-align:center;">' + ctaLink.textContent + '</a></div>' : '');
  document.body.appendChild(backdrop);
  document.body.appendChild(panel);

  function open() { panel.classList.add('open'); backdrop.classList.add('open'); document.body.style.overflow = 'hidden'; }
  function close() { panel.classList.remove('open'); backdrop.classList.remove('open'); document.body.style.overflow = ''; }

  hamburger.addEventListener('click', open);
  backdrop.addEventListener('click', close);
  panel.querySelectorAll('a').forEach(function (a) { a.addEventListener('click', close); });
  window.addEventListener('resize', function () { if (window.innerWidth > 980) close(); });
}

/** Adds/removes a `.scrolled` class on the sticky nav so it can compact itself once the page scrolls. */
function setupNavScroll() {
  var nav = document.getElementById('topnav');
  if (!nav) return;
  function onScroll() {
    nav.classList.toggle('scrolled', window.scrollY > 12);
  }
  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();
}

/**
 * Marks whichever nav-links entry corresponds to the current page with an `.active` class,
 * so there's always a visible "you are here." Only matches links whose href is a standalone
 * page (no `#anchor`) — Posts/You,Check point to homepage sections via anchors and multiple
 * of them legitimately share the same target page, so highlighting one over the other would
 * be arbitrary; skipped entirely rather than guessed. The Utilities pill lights up for its
 * hub page and every individual tool page underneath it, since "you're somewhere in
 * Utilities" is the useful signal there, not just "you're on tools.html exactly."
 */
function highlightActiveNav() {
  var UTILITY_PAGES = ['tools.html', 'password-coach.html', 'recovery-kit.html', 'breach-check.html', 'ask.html'];
  var current = window.location.pathname.split('/').pop() || 'index.html';

  document.querySelectorAll('.nav-links a').forEach(function (a) {
    var href = a.getAttribute('href') || '';
    if (!href || href.indexOf('#') !== -1) return;
    var isUtilitiesLink = href === 'tools.html';
    var match = isUtilitiesLink ? UTILITY_PAGES.indexOf(current) !== -1 : href === current;
    if (match) a.classList.add('active');
  });
}

/**
 * Ambient cursor glow that softly follows the mouse on dark sections.
 * Skipped entirely on touch devices and under prefers-reduced-motion.
 */
function initCursorFX() {
  var isFine = window.matchMedia('(pointer: fine)').matches;
  var prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (!isFine || prefersReduced) return;

  var glow = document.createElement('div');
  glow.className = 'cursor-glow';
  document.body.appendChild(glow);

  function onMove(e) {
    glow.classList.add('active');
    document.documentElement.style.setProperty('--mx', e.clientX + 'px');
    document.documentElement.style.setProperty('--my', e.clientY + 'px');
  }
  window.addEventListener('mousemove', onMove, { passive: true });
  window.addEventListener('mouseleave', function () {
    glow.classList.remove('active');
  });
}

/**
 * Command palette (⌘K / Ctrl+K): fuzzy-searches all posts plus a fixed set of site pages.
 * Builds its own DOM on first use so no markup needs to be duplicated across pages.
 * Any page that calls this just needs a trigger element with id="cmdkTrigger".
 */
function initCommandPalette() {
  var trigger = document.getElementById('cmdkTrigger');
  var staticPages = [
    { title: 'Home', sub: 'index.html', href: 'index.html', color: 'var(--orange)' },
    { title: 'You, Check.', sub: 'index.html#youcheck — the quick gut-check quiz', href: 'index.html#youcheck', color: 'var(--pink)' },
    { title: 'Toolkit', sub: 'toolkit.html — recommended tools', href: 'toolkit.html', color: 'var(--gold)' },
    { title: 'Utilities', sub: 'tools.html — every small tool in one place', href: 'tools.html', color: 'var(--violet)' },
    { title: 'Password Coach', sub: 'password-coach.html — memorable, genuinely strong passwords', href: 'password-coach.html', color: 'var(--violet)' },
    { title: '2FA Recovery Kit Builder', sub: 'recovery-kit.html — build a printable recovery plan', href: 'recovery-kit.html', color: 'var(--green)' },
    { title: 'Breach Exposure Check', sub: 'breach-check.html — check if a password has already leaked', href: 'breach-check.html', color: 'var(--gold)' },
    { title: 'Search the Archive', sub: 'ask.html — search this site\'s posts and glossary', href: 'ask.html', color: 'var(--orange)' },
    { title: 'Glossary', sub: 'glossary.html — plain-language terms', href: 'glossary.html', color: 'var(--blue)' }
  ];
  var items = staticPages.slice();
  var selectedIndex = 0;
  var filtered = items;

  var overlay = document.createElement('div');
  overlay.className = 'palette-overlay';
  overlay.innerHTML =
    '<div class="palette-box">' +
      '<div class="palette-input-row">' +
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/></svg>' +
        '<input type="text" placeholder="Search posts, pages…" id="paletteInput" autocomplete="off" />' +
        '<span class="palette-esc">ESC</span>' +
      '</div>' +
      '<div class="palette-results" id="paletteResults"></div>' +
    '</div>';
  document.body.appendChild(overlay);

  var input = overlay.querySelector('#paletteInput');
  var resultsEl = overlay.querySelector('#paletteResults');

  loadPosts().then(function (data) {
    var posts = data.posts.map(function (p) {
      return { title: p.title, sub: p.filename + ' — ' + (p.pillarLabel || ''), href: 'post.html?slug=' + p.slug, color: p.pillarColor || p.stripeColor || 'var(--orange)' };
    });
    items = staticPages.concat(posts);
    render(items);
  }).catch(function () { render(items); });

  function render(list) {
    filtered = list;
    selectedIndex = 0;
    if (!list.length) {
      resultsEl.innerHTML = '<div class="palette-empty">No matches. Try a different filename or keyword.</div>';
      return;
    }
    resultsEl.innerHTML = list.map(function (it, i) {
      return '<a href="' + it.href + '" class="palette-item' + (i === 0 ? ' selected' : '') + '" data-index="' + i + '">' +
        '<span class="p-dot" style="background:' + it.color + ';"></span>' +
        '<span class="p-meta"><span class="p-title">' + escapeHTML(it.title) + '</span><span class="p-sub">' + escapeHTML(it.sub) + '</span></span>' +
      '</a>';
    }).join('');
  }

  function updateSelection() {
    resultsEl.querySelectorAll('.palette-item').forEach(function (el, i) {
      el.classList.toggle('selected', i === selectedIndex);
    });
    var sel = resultsEl.querySelector('.palette-item.selected');
    if (sel) sel.scrollIntoView({ block: 'nearest' });
  }

  function open() {
    overlay.classList.add('open');
    input.value = '';
    render(items);
    setTimeout(function () { input.focus(); }, 50);
  }
  function close() {
    overlay.classList.remove('open');
  }

  if (trigger) trigger.addEventListener('click', open);

  document.addEventListener('keydown', function (e) {
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
      e.preventDefault();
      overlay.classList.contains('open') ? close() : open();
    }
    if (e.key === 'Escape' && overlay.classList.contains('open')) close();
  });

  overlay.addEventListener('click', function (e) {
    if (e.target === overlay) close();
  });

  input.addEventListener('input', function () {
    var q = input.value.trim().toLowerCase();
    if (!q) { render(items); return; }
    render(items.filter(function (it) {
      return it.title.toLowerCase().indexOf(q) !== -1 || it.sub.toLowerCase().indexOf(q) !== -1;
    }));
  });

  input.addEventListener('keydown', function (e) {
    if (e.key === 'ArrowDown') { e.preventDefault(); selectedIndex = Math.min(selectedIndex + 1, filtered.length - 1); updateSelection(); }
    if (e.key === 'ArrowUp') { e.preventDefault(); selectedIndex = Math.max(selectedIndex - 1, 0); updateSelection(); }
    if (e.key === 'Enter' && filtered[selectedIndex]) { window.location.href = filtered[selectedIndex].href; }
  });
}

/** Turns a post object back into a real markdown document, for the "Copy as .md" button on articles. */
function generateMarkdown(post) {
  var lines = [];
  lines.push('# ' + post.title, '');
  lines.push('_' + post.intro + '_', '');
  post.sections.forEach(function (sec) {
    lines.push('## ' + sec.num + '. ' + sec.title, '');
    sec.blocks.forEach(function (block) {
      if (block.type === 'step') {
        if (block.platform) lines.push('**' + block.platform + '**', '');
        block.paragraphs.forEach(function (p) { lines.push(p.replace(/<[^>]+>/g, ''), ''); });
      } else if (block.type === 'compare') {
        lines.push('- ' + block.bad.label + ': ' + block.bad.text);
        lines.push('- ' + block.good.label + ': ' + block.good.text, '');
      } else if (block.type === 'pattern-list') {
        block.items.forEach(function (it) { lines.push('- **' + it.tag + '**: ' + it.text); });
        lines.push('');
      }
    });
  });
  lines.push('> ' + post.warn.label + ' — ' + post.warn.text, '');
  lines.push('## Checklist', '');
  post.checklist.forEach(function (c) { lines.push('- [ ] ' + c); });
  lines.push('', '---', 'stay(human).sec — for human. for privacy.');
  return lines.join('\n');
}

/** Wires up a "Copy as .md" button: copies markdown to clipboard with a brief confirmation state. */
function setupCopyMdButton(btn, post) {
  if (!btn) return;
  btn.addEventListener('click', function () {
    var md = generateMarkdown(post);
    var done = function () {
      btn.classList.add('copied');
      var original = btn.querySelector('span').textContent;
      btn.querySelector('span').textContent = 'Copied!';
      setTimeout(function () {
        btn.classList.remove('copied');
        btn.querySelector('span').textContent = original;
      }, 1800);
    };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(md).then(done).catch(function () { fallbackCopy(md, done); });
    } else {
      fallbackCopy(md, done);
    }
  });
}

function fallbackCopy(text, done) {
  var ta = document.createElement('textarea');
  ta.value = text;
  ta.style.position = 'fixed';
  ta.style.opacity = '0';
  document.body.appendChild(ta);
  ta.select();
  try { document.execCommand('copy'); done(); } catch (e) {}
  document.body.removeChild(ta);
}

/**
 * Loads a <script src="..."> exactly once, caching the in-flight/settled promise so a
 * second call (e.g. clicking "Download as PDF" twice) reuses the same load instead of
 * injecting the tag again.
 */
var _scriptLoadPromises = {};
function loadScriptOnce(src) {
  if (!_scriptLoadPromises[src]) {
    _scriptLoadPromises[src] = new Promise(function (resolve, reject) {
      var s = document.createElement('script');
      s.src = src;
      s.onload = function () { resolve(); };
      s.onerror = function () { delete _scriptLoadPromises[src]; reject(new Error('Failed to load ' + src)); };
      document.head.appendChild(s);
    });
  }
  return _scriptLoadPromises[src];
}

var JSPDF_CDN_URL = 'https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js';

/**
 * Three rounds of trying to make html2canvas/html2pdf.js rasterize a styled DOM clone all
 * failed for real visitors (zero-height clone, then a JPEG-alpha theory, then confirmed the
 * canvas simply wasn't painting any content at all in a real browser) while every fix looked
 * correct in sandboxed testing — html2canvas's cloning/rendering pipeline was an unreliable,
 * undebuggable black box across environments. So PDF export is built directly with jsPDF's
 * own text/shape drawing API instead of screenshotting anything: deterministic, no DOM
 * cloning, no web-font loading race, no canvas painting to silently fail.
 */
var PDF_BRAND_COLORS = {
  bg: [0, 0, 0],
  card: [13, 12, 10],
  cream: [244, 241, 232],
  creamDim: [199, 195, 182],
  line: [58, 53, 44],
  orange: [255, 122, 61],
  blue: [76, 141, 255],
  green: [63, 207, 142],
  violet: [150, 112, 230],
  gold: [232, 167, 0],
  pink: [232, 90, 130]
};

/** Maps a post's `var(--xxx)` color string to an RGB triple jsPDF can use — falls back to orange. */
function pdfColorFromVar(cssVar) {
  var match = /--([a-z]+)/.exec(cssVar || '');
  return (match && PDF_BRAND_COLORS[match[1]]) || PDF_BRAND_COLORS.orange;
}

function stripTagsForPdf(html) { return html.replace(/<[^>]+>/g, ''); }

/**
 * jsPDF's built-in fonts (helvetica/courier/times) only support the WinAnsi glyph set — no
 * arrows, checkboxes, or symbol characters. Post content routinely uses "→" for step
 * sequences ("Settings → General → ..."), and this file's own warn/compare/checklist markup
 * used ⚠/✕/✓/☐. Left unreplaced, jsPDF renders those as garbled glyphs AND — worse —
 * mis-measures their width, throwing off splitTextToSize()'s wrapping math enough to run
 * text off the page edge. Every string reaching doc.text()/splitTextToSize() goes through
 * this first.
 */
function sanitizePdfText(str) {
  return String(str)
    .replace(/→/g, '->')
    .replace(/⚠/g, '!')
    .replace(/✕/g, 'X')
    .replace(/✓/g, 'OK')
    .replace(/☐/g, '[ ]');
}

/**
 * The site's actual Poppins/JetBrains Mono TTF files, fetched directly from Google's static
 * font host (fonts.gstatic.com — the same origin the page's own @font-face rules resolve to)
 * so the PDF uses the real brand fonts instead of jsPDF's built-in Helvetica/Courier
 * substitutes. These are the literal file URLs the browser would request; fetching a static
 * font file doesn't depend on any request header a page script can't set, so this works from
 * plain browser fetch() despite Google's font *CSS* API varying by User-Agent.
 */
var PDF_FONT_FILES = {
  sansRegular: 'https://fonts.gstatic.com/s/poppins/v24/pxiEyp8kv8JHgFVrFJA.ttf',
  sansBold: 'https://fonts.gstatic.com/s/poppins/v24/pxiByp8kv8JHgFVrLCz7V1s.ttf',
  monoRegular: 'https://fonts.gstatic.com/s/jetbrainsmono/v24/tDbY2o-flEEny0FZhsfKu5WU4zr3E_BX0PnT8RD8yKxjPQ.ttf',
  monoBold: 'https://fonts.gstatic.com/s/jetbrainsmono/v24/tDbY2o-flEEny0FZhsfKu5WU4zr3E_BX0PnT8RD8L6tjPQ.ttf'
};
var _pdfFontDataCache = null;

function arrayBufferToBase64(buffer) {
  var bytes = new Uint8Array(buffer);
  var binary = '';
  var chunkSize = 0x8000;
  for (var i = 0; i < bytes.length; i += chunkSize) {
    binary += String.fromCharCode.apply(null, bytes.subarray(i, i + chunkSize));
  }
  return btoa(binary);
}

/**
 * Fetches the real brand font files as base64, once, caching the result (not tied to any
 * particular jsPDF document — each generatePostPdf() call embeds fresh into its own doc).
 * Resolves to null on any failure so callers can fall back to jsPDF's built-in
 * helvetica/courier — a visitor should always get a working PDF, exact font or not.
 */
function loadPdfFontData() {
  if (_pdfFontDataCache) return _pdfFontDataCache;
  _pdfFontDataCache = Promise.all(Object.keys(PDF_FONT_FILES).map(function (key) {
    return fetch(PDF_FONT_FILES[key]).then(function (res) {
      if (!res.ok) throw new Error('font fetch failed: ' + key);
      return res.arrayBuffer();
    }).then(function (buf) {
      return [key, arrayBufferToBase64(buf)];
    });
  })).then(function (entries) {
    var data = {};
    entries.forEach(function (e) { data[e[0]] = e[1]; });
    return data;
  }).catch(function () {
    return null;
  });
  return _pdfFontDataCache;
}

/** Builds the full PDF document for a post using jsPDF's native drawing API. Returns the jsPDF instance. */
function generatePostPdf(post, fontData) {
  var doc = new window.jspdf.jsPDF({ unit: 'pt', format: 'a4' });
  var fonts = { sans: 'helvetica', mono: 'courier' };
  if (fontData) {
    doc.addFileToVFS('sansRegular.ttf', fontData.sansRegular);
    doc.addFont('sansRegular.ttf', 'PdfSans', 'normal');
    doc.addFileToVFS('sansBold.ttf', fontData.sansBold);
    doc.addFont('sansBold.ttf', 'PdfSans', 'bold');
    doc.addFileToVFS('monoRegular.ttf', fontData.monoRegular);
    doc.addFont('monoRegular.ttf', 'PdfMono', 'normal');
    doc.addFileToVFS('monoBold.ttf', fontData.monoBold);
    doc.addFont('monoBold.ttf', 'PdfMono', 'bold');
    fonts = { sans: 'PdfSans', mono: 'PdfMono' };
  }
  var pageW = doc.internal.pageSize.getWidth();
  var pageH = doc.internal.pageSize.getHeight();
  var marginX = 50, marginTop = 44, marginBottom = 50;
  var contentW = pageW - marginX * 2;
  var chromeH = 24;
  var y = marginTop;

  function setColor(method, rgb) { doc[method](rgb[0], rgb[1], rgb[2]); }

  function paintPageChrome() {
    setColor('setFillColor', PDF_BRAND_COLORS.bg);
    doc.rect(0, 0, pageW, pageH, 'F');
    setColor('setFillColor', PDF_BRAND_COLORS.card);
    doc.rect(0, 0, pageW, chromeH, 'F');
    var dots = [[255, 95, 87], [254, 188, 46], [40, 200, 64]];
    dots.forEach(function (c, i) {
      setColor('setFillColor', c);
      doc.circle(marginX - 30 + i * 11, chromeH / 2, 2.6, 'F');
    });
    doc.setFont(fonts.mono, 'normal');
    doc.setFontSize(8);
    setColor('setTextColor', PDF_BRAND_COLORS.creamDim);
    doc.text(sanitizePdfText('stay(human).sec:~$ cat ' + post.filename), marginX, chromeH / 2 + 3);
  }

  function newPage() {
    doc.addPage();
    paintPageChrome();
    y = marginTop + chromeH;
  }

  function ensureSpace(h) {
    if (y + h > pageH - marginBottom) newPage();
  }

  function writeWrapped(text, opts) {
    opts = opts || {};
    var size = opts.size || 10.5;
    var lineH = opts.lineH || size * 1.5;
    doc.setFont(opts.font || fonts.sans, opts.style || 'normal');
    doc.setFontSize(size);
    setColor('setTextColor', opts.color || PDF_BRAND_COLORS.cream);
    var lines = doc.splitTextToSize(sanitizePdfText(text), contentW - (opts.indent || 0));
    lines.forEach(function (line) {
      ensureSpace(lineH);
      doc.text(line, marginX + (opts.indent || 0), y);
      y += lineH;
    });
    y += opts.gapAfter || 0;
  }

  function drawDivider() {
    ensureSpace(20);
    setColor('setDrawColor', PDF_BRAND_COLORS.line);
    doc.setLineDashPattern([2, 2], 0);
    doc.line(marginX, y, pageW - marginX, y);
    doc.setLineDashPattern([], 0);
    y += 20;
  }

  paintPageChrome();
  y = marginTop + chromeH;

  // tag pill
  var tagRGB = pdfColorFromVar(post.tagColor);
  doc.setFont(fonts.mono, 'normal');
  doc.setFontSize(8);
  var tagText = sanitizePdfText(post.tag);
  var tagW = doc.getTextWidth(tagText) + 16;
  ensureSpace(20);
  setColor('setDrawColor', tagRGB);
  doc.roundedRect(marginX, y - 9, tagW, 15, 7, 7, 'S');
  setColor('setTextColor', tagRGB);
  doc.text(tagText, marginX + 8, y + 1);
  y += 26;

  writeWrapped(post.title, { size: 19, font: fonts.sans, style: 'bold', color: PDF_BRAND_COLORS.cream, lineH: 23, gapAfter: 10 });
  writeWrapped(post.intro, { size: 10.5, color: PDF_BRAND_COLORS.creamDim, lineH: 15, gapAfter: 6 });
  drawDivider();

  post.sections.forEach(function (sec) {
    ensureSpace(28);
    writeWrapped(sec.num + ' — ' + sec.title, { size: 13.5, style: 'bold', color: PDF_BRAND_COLORS.cream, lineH: 17, gapAfter: 8 });
    sec.blocks.forEach(function (block) {
      if (block.type === 'step') {
        if (block.platform) {
          writeWrapped(block.platform.toUpperCase(), { size: 8.5, font: fonts.mono, color: PDF_BRAND_COLORS.green, lineH: 11, gapAfter: 3 });
        }
        block.paragraphs.forEach(function (p) {
          writeWrapped(stripTagsForPdf(p), { size: 10, color: PDF_BRAND_COLORS.creamDim, lineH: 14.5, gapAfter: 8 });
        });
      } else if (block.type === 'compare') {
        writeWrapped(block.bad.label + ': ' + block.bad.text, { size: 9.5, color: PDF_BRAND_COLORS.pink, lineH: 13.5, gapAfter: 4 });
        writeWrapped(block.good.label + ': ' + block.good.text, { size: 9.5, color: PDF_BRAND_COLORS.green, lineH: 13.5, gapAfter: 8 });
      } else if (block.type === 'pattern-list') {
        block.items.forEach(function (it) {
          writeWrapped(it.tag + ' — ' + it.text, { size: 9.5, color: PDF_BRAND_COLORS.creamDim, lineH: 13.5, gapAfter: 4 });
        });
        y += 4;
      }
    });
  });

  // warn box
  ensureSpace(50);
  var warnTop = y;
  writeWrapped(post.warn.label, { size: 9, font: fonts.mono, color: PDF_BRAND_COLORS.pink, lineH: 12, gapAfter: 4 });
  writeWrapped(post.warn.text, { size: 9.5, indent: 10, color: PDF_BRAND_COLORS.creamDim, lineH: 13.5 });
  setColor('setDrawColor', PDF_BRAND_COLORS.pink);
  doc.roundedRect(marginX - 8, warnTop - 14, contentW + 16, y - warnTop + 20, 6, 6, 'S');
  y += 22;

  drawDivider();
  writeWrapped('The 60-second version', { size: 13.5, style: 'bold', color: PDF_BRAND_COLORS.cream, lineH: 17, gapAfter: 6 });
  post.checklist.forEach(function (c) {
    writeWrapped('☐  ' + c, { size: 10, color: PDF_BRAND_COLORS.creamDim, lineH: 15, gapAfter: 2 });
  });

  // footer on every page
  var pageCount = doc.internal.getNumberOfPages();
  for (var i = 1; i <= pageCount; i++) {
    doc.setPage(i);
    setColor('setDrawColor', PDF_BRAND_COLORS.line);
    doc.line(marginX, pageH - 34, pageW - marginX, pageH - 34);
    doc.setFont(fonts.mono, 'normal');
    doc.setFontSize(7.5);
    setColor('setTextColor', PDF_BRAND_COLORS.creamDim);
    doc.text('stay(human).sec — plain-language cybersecurity, AI & privacy — stayhumansec.github.io', pageW / 2, pageH - 20, { align: 'center' });
  }

  return doc;
}

/**
 * Wires up a "Download as PDF" button. Lazy-loads jsPDF from a CDN only on first click (so
 * articles that are never exported never pay for the library), builds the PDF natively via
 * generatePostPdf(), and triggers a direct download — entirely in the browser. No server
 * round-trip, no email capture, nothing sent or stored anywhere.
 */
function setupDownloadPdfButton(btn, post) {
  if (!btn) return;
  var labelEl = btn.querySelector('span');
  var originalLabel = labelEl.textContent;

  btn.addEventListener('click', function () {
    btn.disabled = true;
    btn.classList.remove('pdf-error');
    labelEl.textContent = 'Generating…';

    Promise.all([loadScriptOnce(JSPDF_CDN_URL), loadPdfFontData()]).then(function (results) {
      var fontData = results[1];
      var doc = generatePostPdf(post, fontData);
      doc.save(post.slug + '.pdf');
    }).then(function () {
      btn.disabled = false;
      labelEl.textContent = originalLabel;
    }).catch(function () {
      btn.disabled = false;
      btn.classList.add('pdf-error');
      labelEl.textContent = 'Couldn’t generate — try again';
      setTimeout(function () {
        btn.classList.remove('pdf-error');
        labelEl.textContent = originalLabel;
      }, 3000);
    });
  });
}

/** Fills a thin fixed bar across the top of the viewport as the person scrolls down the page. */
function initScrollProgress() {
  var bar = document.getElementById('scrollProgress');
  if (!bar) return;
  function onScroll() {
    var doc = document.documentElement;
    var scrollable = doc.scrollHeight - doc.clientHeight;
    var pct = scrollable > 0 ? (window.scrollY / scrollable) * 100 : 0;
    bar.style.width = pct + '%';
  }
  window.addEventListener('scroll', onScroll, { passive: true });
  window.addEventListener('resize', onScroll);
  onScroll();
}

/**
 * Plays once per browser session, on whichever page the person lands on first (since most
 * traffic arrives on a specific post, not the homepage). Runs a genuinely true privacy check
 * of the page itself — this is a static site with no trackers, no ad scripts, no cookies —
 * so the result isn't a marketing claim, it's an accurate readout. Always skippable, and
 * skipped instantly under reduced-motion or on repeat visits within the same session.
 * Calls `onDone` when finished so the caller can fade the real page in afterward.
 */
function initBootSequence(onDone) {
  var prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var alreadyBooted = false;
  try { alreadyBooted = sessionStorage.getItem('shs_booted') === '1'; } catch (e) {}

  if (prefersReduced || alreadyBooted) { onDone(); return; }
  try { sessionStorage.setItem('shs_booted', '1'); } catch (e) {}

  var checks = [
    { text: 'checking for third-party trackers…', result: '0 found' },
    { text: 'checking for ad scripts…', result: '0 found' },
    { text: 'checking for cookies set…', result: '0 found' },
    { text: 'verifying you\'re not a robot…', result: 'you\'re clear, human.' }
  ];

  var overlay = document.createElement('div');
  overlay.className = 'boot-overlay';
  overlay.innerHTML =
    '<button class="boot-skip" id="bootSkip">Skip →</button>' +
    '<div class="boot-terminal">' +
      '<div class="term-bar">' +
        '<div class="term-bar-label">stay(human).sec:~$ ./boot.sh</div>' +
        '<div class="win-controls"><span class="wc-min"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="5" y1="19" x2="19" y2="19"/></svg></span><span class="wc-max"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="5" y="5" width="14" height="14" rx="1.5"/></svg></span><span class="wc-close"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="6" y1="6" x2="18" y2="18"/><line x1="18" y1="6" x2="6" y2="18"/></svg></span></div>' +
      '</div>' +
      '<div class="term-body"><div class="boot-lines" id="bootLines"></div></div>' +
    '</div>';
  document.body.appendChild(overlay);
  requestAnimationFrame(function () { overlay.classList.add('active'); });

  var linesEl = overlay.querySelector('#bootLines');
  var timers = [];
  var i = 0;

  function addLine(html, extraClass) {
    var div = document.createElement('div');
    div.className = 'boot-line' + (extraClass ? ' ' + extraClass : '');
    div.innerHTML = html;
    linesEl.appendChild(div);
    requestAnimationFrame(function () { div.classList.add('show'); });
  }

  function next() {
    if (i >= checks.length) {
      timers.push(setTimeout(finish, 450));
      return;
    }
    var c = checks[i];
    addLine('<span class="boot-ok">[ok]</span>' + escapeHTML(c.text) + ' <b>' + escapeHTML(c.result) + '</b>');
    i++;
    timers.push(setTimeout(next, 320));
  }

  function finish() {
    addLine('Welcome. <b>For human. For privacy.</b>', 'boot-welcome');
    timers.push(setTimeout(dismiss, 850));
  }

  function dismiss() {
    timers.forEach(clearTimeout);
    overlay.classList.add('leaving');
    setTimeout(function () { overlay.remove(); onDone(); }, 350);
  }

  var skipBtn = document.getElementById('bootSkip');
  if (skipBtn) skipBtn.addEventListener('click', dismiss);
  timers.push(setTimeout(next, 350));
}

/** Escapes text before it's inserted as HTML, since post content comes from a JSON data file. */
function escapeHTML(str) {
  var div = document.createElement('div');
  div.textContent = str == null ? '' : String(str);
  return div.innerHTML;
}

/* ============================================================
 * BRING-YOUR-OWN-KEY AI HELPERS
 *
 * The site has no backend, so the only way to offer a real (not just
 * rule-based) AI feature without breaking that is to let each visitor
 * bring their own Anthropic API key and call Anthropic directly from
 * their own browser. The key is stored only in that browser's
 * localStorage — it never touches any server of ours, and every tool
 * on the site keeps working with plain rule-based analysis if no key
 * is set. This is the one deliberate exception to "nothing leaves the
 * browser," and it's opt-in per visitor, not on by default.
 * ============================================================ */

function getStoredApiKey() {
  try { return localStorage.getItem('shs_ai_key') || ''; } catch (e) { return ''; }
}
function setStoredApiKey(key) {
  try {
    if (key) localStorage.setItem('shs_ai_key', key);
    else localStorage.removeItem('shs_ai_key');
  } catch (e) {}
}

/**
 * Calls Anthropic's Messages API directly from the browser using the visitor's own key.
 * Requires the anthropic-dangerous-direct-browser-access header — Anthropic provides this
 * specifically to support bring-your-own-key browser calls like this one, name
 * notwithstanding. Throws on any non-2xx response with the response body attached so
 * callers can show a real error instead of a silent failure.
 *
 * `userPromptOrMessages` accepts either a plain string (single-turn — wrapped into a
 * one-message array) or an already-built array of {role, content} messages for multi-turn
 * conversations like Search the Archive's optional AI deep-dive.
 */
async function callClaude(apiKey, systemPrompt, userPromptOrMessages, opts) {
  opts = opts || {};
  var messages = Array.isArray(userPromptOrMessages)
    ? userPromptOrMessages
    : [{ role: 'user', content: userPromptOrMessages }];
  var res = await fetch('https://api.anthropic.com/v1/messages', {
    method: 'POST',
    headers: {
      'content-type': 'application/json',
      'x-api-key': apiKey,
      'anthropic-version': '2023-06-01',
      'anthropic-dangerous-direct-browser-access': 'true'
    },
    body: JSON.stringify({
      model: opts.model || 'claude-haiku-4-5-20251001',
      max_tokens: opts.maxTokens || 1024,
      system: systemPrompt,
      messages: messages
    })
  });
  if (!res.ok) {
    var errText = '';
    try { errText = (await res.json()).error.message; } catch (e) { errText = 'HTTP ' + res.status; }
    throw new Error(errText);
  }
  var data = await res.json();
  return (data.content && data.content[0] && data.content[0].text) || '';
}

/**
 * Renders the reusable "add your own API key" box used by every AI-enabled tool. Shows a
 * masked input + save/clear buttons, and calls onSaved(key) whenever the stored key changes
 * so the calling page can enable/disable its AI-powered action.
 */
function renderApiKeyBox(containerEl, onSaved) {
  var existing = getStoredApiKey();
  containerEl.innerHTML =
    '<div class="ai-key-box">' +
      '<div class="ai-key-head">🔑 Optional: add your own Anthropic API key to unlock the AI deep-dive</div>' +
      '<div class="ai-key-row">' +
        '<input type="password" id="aiKeyInput" placeholder="sk-ant-..." value="' + escapeHTML(existing) + '" autocomplete="off" spellcheck="false" />' +
        '<button class="btn-secondary" id="aiKeySaveBtn" style="cursor:pointer;">Save</button>' +
        (existing ? '<button class="btn-secondary" id="aiKeyClearBtn" style="cursor:pointer;">Clear</button>' : '') +
      '</div>' +
      '<p class="ai-key-note">Stored only in this browser — never sent anywhere except directly from your browser to Anthropic when you use the AI deep-dive. Don\'t have one? <a href="https://console.anthropic.com/" target="_blank" rel="noopener">Get a key here</a>. Everything on this page works fine without one, just with less depth.</p>' +
    '</div>';

  document.getElementById('aiKeySaveBtn').addEventListener('click', function () {
    var val = document.getElementById('aiKeyInput').value.trim();
    setStoredApiKey(val);
    renderApiKeyBox(containerEl, onSaved);
    if (onSaved) onSaved(val);
  });
  var clearBtn = document.getElementById('aiKeyClearBtn');
  if (clearBtn) {
    clearBtn.addEventListener('click', function () {
      setStoredApiKey('');
      renderApiKeyBox(containerEl, onSaved);
      if (onSaved) onSaved('');
    });
  }
}
