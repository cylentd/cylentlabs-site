// Runs every shape with a stub DOM and prints, per shape and layout, how many claimed dots land inside the stage box.
// tests/test_shapes.py reads the JSON. A shape whose targets never get set (all at 0,0) shows inside = 0.
const fs = require("fs");
const path = require("path");
global.window = global;
global.document = { querySelector: () => null, querySelectorAll: () => [] };
global.matchMedia = () => ({ matches: false });
global.addEventListener = () => {};
const src = path.join(__dirname, "..", "design", "src", "js");
for (const f of ["shapes.js", "helix.js"]) eval(fs.readFileSync(path.join(src, f), "utf8"));

const L = window.LAB, n = 1200, out = {};
const P = { n, w: 1280, h: 800, tx: new Float32Array(n), ty: new Float32Array(n), cls: new Uint8Array(n), lit: new Uint8Array(n),
  amb: new Uint8Array(n), fast: new Uint8Array(n), lvl: new Uint8Array(n), ord: new Float32Array(n), sz: new Float32Array(n).fill(1), enter: new Float32Array(n) };
const boxes = {
  wide: { small: false, sx: 120, sy: 900, sw: 1100, sh: 700 },
  phone: { small: true, sx: 16, sy: 900, sw: 220, sh: 560 },
};
for (const [id, shape] of Object.entries(L.shapes)) {
  for (const [layout, c] of Object.entries(boxes)) {
    P.tx.fill(-1e4); P.ty.fill(-1e4); // a target the shape never sets stays far outside every stage
    P.cls.fill(4); // a colour the shape never resets shows up as a stray project hue
    shape.init(P, c);
    if (shape.step) shape.step(P, c, 1.5);
    let claimed = 0, inside = 0, stray = 0, x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity;
    for (let i = 0; i < n; i++) {
      if (P.amb[i]) continue;
      claimed++;
      if (P.cls[i] >= 2 && !P.lit[i]) stray++; // a project hue on an unlit dot
      x0 = Math.min(x0, P.tx[i]); x1 = Math.max(x1, P.tx[i]); y0 = Math.min(y0, P.ty[i]); y1 = Math.max(y1, P.ty[i]);
      const pad = 24; // a ball arc or a ping ring may stray just past the box
      if (P.tx[i] >= c.sx - pad && P.tx[i] <= c.sx + c.sw + pad && P.ty[i] >= c.sy - pad && P.ty[i] <= c.sy + c.sh + pad) inside++;
    }
    out[`${id}/${layout}`] = { claimed, inside, stray, fillW: (x1 - x0) / c.sw, fillH: (y1 - y0) / c.sh };
  }
}
console.log(JSON.stringify(out));
