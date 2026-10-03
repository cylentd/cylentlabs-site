/* The chapter rail: follows body[data-active] (set by chapters.js) to mark the chapter being read, names it on the
   phone pill, and opens and closes the pill's list. */
(() => {
  const rail = document.querySelector(".rail");
  if (!rail) return;
  const pill = rail.querySelector(".rail__pill"), now = rail.querySelector(".rail__now"), links = [...rail.querySelectorAll(".rail__list a")];
  const label = now.textContent;

  const mark = () => {
    const id = document.body.dataset.active;
    let lit = null;
    links.forEach((a) => {
      const on = a.dataset.for === id;
      if (on) { a.setAttribute("aria-current", "true"); lit = a; } else a.removeAttribute("aria-current");
    });
    now.textContent = lit ? lit.textContent : label;
    pill.style.cssText = lit ? lit.style.cssText : "";
    if (id === "hero") close();
  };
  const close = () => pill.setAttribute("aria-expanded", "false");

  pill.addEventListener("click", () => pill.setAttribute("aria-expanded", String(pill.getAttribute("aria-expanded") !== "true")));
  links.forEach((a) => a.addEventListener("click", close));
  document.addEventListener("click", (e) => { if (!rail.contains(e.target)) close(); });
  // Escape closes the open list; focus inside it would be left on a hidden link, so it goes back to the pill
  document.addEventListener("keydown", (e) => {
    if (e.key !== "Escape" || pill.getAttribute("aria-expanded") !== "true") return;
    const inside = rail.contains(document.activeElement);
    close();
    if (inside) pill.focus();
  });
  // the footer's wordmark sits where the phone pill does: step aside while it is on screen
  const foot = document.querySelector(".foot");
  if (foot) new IntersectionObserver(([e]) => { rail.classList.toggle("is-off", e.isIntersecting); if (e.isIntersecting) close(); }).observe(foot);
  new MutationObserver(mark).observe(document.body, { attributes: true, attributeFilter: ["data-active"] });
  mark();
})();
