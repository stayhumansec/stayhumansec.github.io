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

/** Escapes text before it's inserted as HTML, since post content comes from a JSON data file. */
function escapeHTML(str) {
  var div = document.createElement('div');
  div.textContent = str == null ? '' : String(str);
  return div.innerHTML;
}

/** Fades the whole page in on load instead of popping in unstyled. No-op under reduced-motion (handled in CSS). */
function initPageFade() {
  requestAnimationFrame(function () {
    requestAnimationFrame(function () { document.body.classList.add('loaded'); });
  });
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
