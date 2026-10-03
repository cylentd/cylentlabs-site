/* Chapters: the hero's helix, then one chapter per project. The active one is the last whose motif box has risen past
   62% of the screen height; the field draws that shape inside the box and scrolls it with the page. */
window.LAB = window.LAB || {};
(() => {
  const L = window.LAB;
  const hero = document.querySelector(".helix__stage");
  if (!hero || !L.field) return;
  const stops = [{ id: "hero", box: hero }].concat(
    [...document.querySelectorAll(".chapter")].map((s) => ({ id: s.dataset.stop, box: s.querySelector(".chapter__motif") }))
  );
  const LINE = 0.62;
  let active = -1, queued = false;

  const measure = (el) => { const r = el.getBoundingClientRect(); return { sx: r.left, sy: r.top + scrollY, sw: r.width, sh: r.height }; };

  function update(remeasure) {
    queued = false;
    const line = innerHeight * LINE;
    let k = 0;
    stops.forEach((s, i) => { if (i && s.box.getBoundingClientRect().top < line) k = i; });
    if (k !== active || remeasure) {
      active = k;
      document.body.dataset.active = stops[k].id;
      L.field.setStop(stops[k].id, measure(stops[k].box), -scrollY);
    } else L.field.setOffset(-scrollY);
  }
  const queue = (remeasure) => { if (!queued) { queued = true; requestAnimationFrame(() => update(remeasure === true)); } };
  addEventListener("scroll", queue, { passive: true });
  addEventListener("resize", queue); // the 62% line moves with the window height; the boxes only move on lab:layout
  // lab:layout: the boxes moved (field.js once a resize settles, built.js on a toggle). Re-measuring rebuilds the
  // shape, so cancelling the event tells field.js not to rebuild it a second time.
  addEventListener("lab:layout", (e) => { e.preventDefault(); queue(true); });
  // web fonts change the layout after first paint; measure the boxes again once they are in
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(() => queue(true));
  update(true);

})();
