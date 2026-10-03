/* Demos: a chapter's clip starts once it is mostly on screen (--clip-in-view) and scrolling, the page's or a row's, has
   been still for --t-clip-settle, so nothing starts moving under a scrolling thumb. Once playing it plays on until it
   leaves the screen. Its pause button holds it still until pressed again. Reduced motion keeps the poster still and
   the button hidden. */
(() => {
  const vids = [...document.querySelectorAll(".chapter__demo")];
  if (!vids.length || matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  const tok = (n) => parseFloat(getComputedStyle(document.documentElement).getPropertyValue(n));
  const inView = tok("--clip-in-view"), settle = tok("--t-clip-settle");
  const seen = new WeakMap(); // how much of each clip is on screen, 0 to 1
  const play = (v) => { v.preload = "auto"; v.play().catch(() => {}); };
  const startSettled = () => {
    for (const v of vids) if (v.paused && !v.dataset.held && (seen.get(v) || 0) >= inView) play(v);
  };
  let still = 0;
  const wait = () => { clearTimeout(still); still = setTimeout(startSettled, settle); };
  const io = new IntersectionObserver((entries) => {
    for (const e of entries) {
      seen.set(e.target, e.isIntersecting ? e.intersectionRatio : 0);
      if (!e.isIntersecting) e.target.pause();
    }
    wait();
  }, { threshold: [0, inView] });
  // capture: a swipeable row of phones scrolls on its own, and its scroll events do not reach window otherwise
  document.addEventListener("scroll", wait, { capture: true, passive: true });
  vids.forEach((v) => {
    io.observe(v);
    const btn = v.parentElement.querySelector(".chapter__pause");
    if (!btn) return;
    btn.hidden = false;
    btn.addEventListener("click", () => {
      const hold = btn.getAttribute("aria-pressed") !== "true";
      btn.setAttribute("aria-pressed", String(hold));
      if (hold) { v.dataset.held = "1"; v.pause(); return; }
      delete v.dataset.held;
      if ((seen.get(v) || 0) > 0) play(v); // pressed on purpose: no need to wait
    });
  });
})();
