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
  }, { threshold: 0.1, rootMargin: '0px 0px -30px 0px' });

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

/** Animates every [data-countup] number from 0 to its target once it scrolls into view. */
function animateCounters() {
  var els = document.querySelectorAll('[data-countup]');
  var prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  if (prefersReduced) {
    els.forEach(function (el) { el.textContent = el.getAttribute('data-countup'); });
    return;
  }

  var observer = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (!entry.isIntersecting) return;
      var el = entry.target;
      var target = parseInt(el.getAttribute('data-countup'), 10) || 0;
      var duration = 900;
      var startTime = null;

      function step(ts) {
        if (!startTime) startTime = ts;
        var progress = Math.min((ts - startTime) / duration, 1);
        el.textContent = Math.floor(progress * target);
        if (progress < 1) requestAnimationFrame(step);
        else el.textContent = target;
      }
      requestAnimationFrame(step);
      observer.unobserve(el);
    });
  }, { threshold: 0.4 });

  els.forEach(function (el) { observer.observe(el); });
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
