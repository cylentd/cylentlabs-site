/* Demos: each chapter's clip plays only while it is on screen, and its pause button holds it still until pressed again.
   Reduced motion keeps the poster still and the button hidden. */
(() => {
  const vids = document.querySelectorAll(".chapter__demo");
  if (!vids.length || matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  const onScreen = new WeakMap();
  const play = (v) => { v.preload = "auto"; v.play().catch(() => {}); };
  const io = new IntersectionObserver((entries) => {
    for (const e of entries) {
      const v = e.target;
      onScreen.set(v, e.isIntersecting);
      if (e.isIntersecting && !v.dataset.held) play(v); else v.pause();
    }
  }, { threshold: 0.4 });
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
      if (onScreen.get(v)) play(v);
    });
  });
})();
