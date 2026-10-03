/* Demos: each chapter's clip plays only while it is on screen. Reduced motion keeps the poster still. */
(() => {
  const vids = document.querySelectorAll(".chapter__demo");
  if (!vids.length || matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  const io = new IntersectionObserver((entries) => {
    for (const e of entries) {
      const v = e.target;
      if (e.isIntersecting) { v.preload = "auto"; v.play().catch(() => {}); } else v.pause();
    }
  }, { threshold: 0.4 });
  vids.forEach((v) => io.observe(v));
})();
