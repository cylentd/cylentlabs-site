/* How it's built: each chapter's button opens its notes in place, then scrolls just enough to keep them on screen.
   The page below moves down, so the field re-measures the active motif. */
window.LAB = window.LAB || {};
(() => {
  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
  for (const btn of document.querySelectorAll(".chapter__how")) {
    const box = document.getElementById(btn.getAttribute("aria-controls"));
    if (!box) continue;
    btn.addEventListener("click", () => {
      const open = btn.getAttribute("aria-expanded") !== "true";
      btn.setAttribute("aria-expanded", String(open));
      box.hidden = !open;
      if (open) box.scrollIntoView({ block: "nearest", behavior: reduce ? "auto" : "smooth" });
      dispatchEvent(new Event("resize")); // the motifs below have moved
    });
  }
})();
