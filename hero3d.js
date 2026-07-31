// hero3d.js — WebGL brand-icon scene for the homepage hero.
//
// Dynamically imported by initHero3D() in site.js, and only after that
// function's capability gate passes (pointer:fine, not prefers-reduced-motion,
// a real WebGL context test, no Save-Data). Nothing here runs unless all of
// that already held true, and the flat <div id="heroIcon"> SVG icon stays in
// the DOM the whole time as the default state — this module only adds a
// canvas on top of it and fades it in once a frame has actually rendered.
//
// Same bracket-person geometry as draw_icon() in instagram/generate_post.py
// and brandIconSVG() in site.js (left/right quadratic-bezier brackets, a
// circular head, a semicircular body arc), rebuilt as real 3D tube/sphere
// geometry instead of flat SVG paths — not a generic imported 3D scene.
//
// Three.js is vendored locally (vendor/three.module.min.js) rather than
// fetched from a CDN at runtime, so this doesn't add a third-party runtime
// dependency to a production page.

import * as THREE from './vendor/three.module.min.js';

/**
 * @param {HTMLElement} container - the always-present .hero-3d-stage div.
 *   A <canvas> is created and appended to it; on any failure or a sustained
 *   low frame rate, that canvas is torn down and removed, leaving the
 *   sibling flat icon exactly as it already was.
 */
export function mountHero3D(container) {
  var canvas = document.createElement('canvas');
  container.appendChild(canvas);

  var renderer;
  try {
    // preserveDrawingBuffer:true matters specifically because of the
    // IntersectionObserver-gated render loop below -- without it, a WebGL
    // canvas's drawing buffer can be cleared by the browser once rendering
    // stops (the default assumes every visible frame gets freshly redrawn),
    // so pausing the loop while the icon is out of view left the canvas
    // fully blank instead of frozen on its last frame. This showed up on
    // mobile, where the icon sits further down a taller stacked layout and
    // starts outside (or barely inside) the initial viewport, but not on
    // desktop, where the hero is already fully in view on load.
    renderer = new THREE.WebGLRenderer({ canvas: canvas, antialias: true, alpha: true, preserveDrawingBuffer: true });
  } catch (e) {
    if (canvas.parentNode) canvas.parentNode.removeChild(canvas);
    return;
  }
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));

  var scene = new THREE.Scene();
  var camera = new THREE.PerspectiveCamera(38, 1, 0.1, 100);
  camera.position.set(0, 0, 14);

  // Warm, low-key three-point setup -- no HDRI/environment map, no
  // post-processing bloom, kept deliberately simple so the object reads as
  // matte/hand-built rather than glossy-agency-3D.
  scene.add(new THREE.AmbientLight(0xf4f1e8, 0.7));
  var key = new THREE.DirectionalLight(0xffb37a, 1.15);
  key.position.set(4, 5, 6);
  scene.add(key);
  var rim = new THREE.DirectionalLight(0xff7a3d, 0.55);
  rim.position.set(-5, -3, -4);
  scene.add(rim);

  var group = new THREE.Group();
  scene.add(group);

  // Maps the same 0-150 x / 0-100 y coordinate space draw_icon() and
  // brandIconSVG() use onto centered local units, Y flipped (SVG is
  // Y-down, Three.js is Y-up).
  function svgPt(x, y) {
    return new THREE.Vector3((x - 75) / 14, -(y - 50) / 14, 0);
  }

  var creamMat = new THREE.MeshStandardMaterial({ color: 0xf4f1e8, roughness: 0.55, metalness: 0.06 });
  var orangeMat = new THREE.MeshStandardMaterial({
    color: 0xff7a3d, roughness: 0.4, metalness: 0.08, emissive: 0xff7a3d, emissiveIntensity: 0.22,
  });

  var leftCurve = new THREE.QuadraticBezierCurve3(svgPt(38, 16), svgPt(20, 50), svgPt(38, 84));
  var rightCurve = new THREE.QuadraticBezierCurve3(svgPt(112, 16), svgPt(130, 50), svgPt(112, 84));
  var leftTube = new THREE.Mesh(new THREE.TubeGeometry(leftCurve, 48, 0.22, 12, false), creamMat);
  var rightTube = new THREE.Mesh(new THREE.TubeGeometry(rightCurve, 48, 0.22, 12, false), creamMat);
  group.add(leftTube, rightTube);

  var head = new THREE.Mesh(new THREE.SphereGeometry(13 / 14, 28, 20), orangeMat);
  head.position.copy(svgPt(75, 38));
  group.add(head);

  var arcPts = [];
  for (var a = 180; a <= 360; a += 6) {
    var rad = a * Math.PI / 180;
    arcPts.push(svgPt(75 + 17 * Math.cos(rad), 78 + 17 * Math.sin(rad)));
  }
  var arcCurve = new THREE.CatmullRomCurve3(arcPts);
  var arcTube = new THREE.Mesh(new THREE.TubeGeometry(arcCurve, 40, 0.16, 10, false), orangeMat);
  group.add(arcTube);

  var clock = new THREE.Clock();
  var pointerTX = 0, pointerTY = 0, targetPX = 0, targetPY = 0;
  var scrollTilt = 0, targetScroll = 0;
  var running = true;
  var rafId = null;

  function onPointerMove(e) {
    targetPX = (e.clientY / window.innerHeight) * 2 - 1;
    targetPY = (e.clientX / window.innerWidth) * 2 - 1;
  }
  window.addEventListener('pointermove', onPointerMove, { passive: true });

  function onScroll() {
    var rect = container.getBoundingClientRect();
    var vh = window.innerHeight || 1;
    var centerFrac = (rect.top + rect.height / 2) / vh;
    targetScroll = Math.max(-1, Math.min(1, (0.5 - centerFrac) * 2));
  }
  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();

  function resize() {
    var w = container.clientWidth, h = container.clientHeight;
    if (!w || !h) return;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
  }
  window.addEventListener('resize', resize);
  resize();

  // Deliberately no IntersectionObserver-based pause when scrolled out of
  // view. That optimization -- stop calling render() while off-screen,
  // resume on re-intersect -- sounds harmless, but on a real phone (where
  // this icon commonly starts outside or barely inside the initial
  // viewport, unlike on desktop where the hero is already fully visible on
  // load) the canvas would go permanently blank instead of resuming: the
  // "resume" branch relies on the observer's re-intersect callback firing
  // and successfully kicking the render loop back on, and that handoff
  // didn't reliably happen, leaving a healthy WebGL context with real
  // rendered pixels in its buffer that the browser never painted again.
  // This is a tiny scene (a couple tubes and a sphere) -- rendering it
  // continuously regardless of scroll position isn't a meaningful cost,
  // and it removes an entire class of pause/resume timing bugs outright.
  var frameCount = 0;
  var perfStart = performance.now();
  var lowPerfChecked = false;

  function tick() {
    if (!running) { rafId = null; return; }
    rafId = requestAnimationFrame(tick);

    var elapsed = clock.getElapsedTime();
    pointerTX += (targetPX - pointerTX) * 0.04;
    pointerTY += (targetPY - pointerTY) * 0.04;
    scrollTilt += (targetScroll - scrollTilt) * 0.05;

    // Continuous idle spin + gentle float, with pointer/scroll adding a
    // lerped offset on top -- never replacing the idle motion, so it never
    // looks "stuck" waiting for input.
    group.rotation.y = elapsed * 0.18 + pointerTY * 0.35 + scrollTilt * 0.3;
    group.rotation.x = pointerTX * 0.22 + scrollTilt * 0.15;
    group.position.y = Math.sin(elapsed * 0.6) * 0.15;

    renderer.render(scene, camera);

    frameCount++;
    if (!lowPerfChecked && performance.now() - perfStart > 1500) {
      lowPerfChecked = true;
      var fps = frameCount / ((performance.now() - perfStart) / 1000);
      if (fps < 24) teardown();
    }
  }

  function teardown() {
    running = false;
    if (rafId) cancelAnimationFrame(rafId);
    rafId = null;
    window.removeEventListener('pointermove', onPointerMove);
    window.removeEventListener('scroll', onScroll);
    window.removeEventListener('resize', resize);
    [leftTube, rightTube, head, arcTube].forEach(function (m) { m.geometry.dispose(); });
    creamMat.dispose();
    orangeMat.dispose();
    renderer.dispose();
    container.classList.remove('is-ready');
    if (canvas.parentNode) canvas.parentNode.removeChild(canvas);
  }

  // A mid-session reduced-motion toggle (OS setting changed while the tab
  // is open) tears the scene down immediately, same as a failed perf check.
  var reducedQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
  if (typeof reducedQuery.addEventListener === 'function') {
    reducedQuery.addEventListener('change', function (e) { if (e.matches) teardown(); });
  }

  try {
    renderer.render(scene, camera);
    container.classList.add('is-ready');
    tick();
  } catch (e) {
    teardown();
  }
}
