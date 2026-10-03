/* Back to top: the corner button shows once the hero has scrolled away, and hides while the footer (which has its own
   top link) is on screen. On a phone it also steps aside while the page scrolls: rail.js marks that, chapters.css hides it. */
(() => {
  const btn = document.querySelector(".to-top"), hero = document.querySelector(".hero"), foot = document.querySelector(".foot");
  if (!btn || !hero || !foot) return;
  let pastHero = false, footSeen = false;
  const show = () => { btn.hidden = !(pastHero && !footSeen); };
  new IntersectionObserver(([e]) => { pastHero = !e.isIntersecting; show(); }).observe(hero);
  new IntersectionObserver(([e]) => { footSeen = e.isIntersecting; show(); }).observe(foot);
})();
