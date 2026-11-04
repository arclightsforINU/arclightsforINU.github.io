// Checks the hand geometry and the One Euro filter in finger-led/app/pinch.js.
// Run: node pinch_test.mjs
import fs from 'node:fs';
import vm from 'node:vm';

const ctx = vm.createContext({ Math });
vm.runInContext(fs.readFileSync(new URL('../../finger-led/app/pinch.js', import.meta.url), 'utf8'), ctx);
const { pinchGapCm, foldedFingers, isGripping, gapToLevel, OneEuroFilter } =
  vm.runInContext('({ pinchGapCm, foldedFingers, isGripping, gapToLevel, OneEuroFilter })', ctx);

let ok = true;
function expect(name, pass, detail = '') {
  console.log(`${name.padEnd(58)} ${pass ? 'PASS' : 'FAIL'} ${detail}`);
  ok &&= pass;
}

// A right hand in world metres: wrist at the origin, fingers pointing up (-y), palm 9 cm long.
// Each finger is [MCP x, curled]; a curled finger bends its PIP joint and points the tip back at the palm.
function hand({ curled, gapCm = 5 }) {
  const k = Array.from({ length: 21 }, () => ({ x: 0, y: 0, z: 0 }));
  const fingers = [[5, -0.035, false], [9, -0.01, curled], [13, 0.012, curled], [17, 0.032, curled]];
  for (const [mcp, x, bent] of fingers) {
    k[mcp] = { x, y: -0.09, z: 0 };
    k[mcp + 1] = { x, y: -0.135, z: 0 };                                // PIP
    k[mcp + 2] = bent ? { x, y: -0.13, z: -0.03 } : { x, y: -0.16, z: 0 }; // DIP
    k[mcp + 3] = bent ? { x, y: -0.105, z: -0.035 } : { x, y: -0.18, z: 0 }; // tip
  }
  k[1] = { x: -0.03, y: -0.03, z: 0 };
  k[2] = { x: -0.05, y: -0.05, z: 0 };
  k[3] = { x: -0.06, y: -0.07, z: 0 };
  // Thumb tip placed gapCm from the index tip, along x and z so the distance is truly 3D.
  const g = gapCm / 100;
  k[4] = { x: k[8].x - g * 0.6, y: k[8].y, z: k[8].z - g * 0.8 };
  return { keypoints3D: k };
}

expect('gap is the 3D thumb-index distance in cm', Math.abs(pinchGapCm(hand({ curled: false, gapCm: 7 })) - 7) < 1e-9);
expect('open hand: no finger folded', JSON.stringify(foldedFingers(hand({ curled: false }))) === '[false,false,false]');
expect('three fingers curled: gripping', isGripping(hand({ curled: true })));
const oneOpen = hand({ curled: true });
oneOpen.keypoints3D[20] = { x: 0.032, y: -0.18, z: 0 };
expect('pinky straight: not gripping', !isGripping(oneOpen));

// Turn the hand 120 degrees in the image plane, then tip it 60 degrees toward the camera.
function rotated(h) {
  const [a, b] = [2 * Math.PI / 3, Math.PI / 3];
  const keypoints3D = h.keypoints3D.map(({ x, y, z }) => {
    const [x1, y1] = [x * Math.cos(a) - y * Math.sin(a), x * Math.sin(a) + y * Math.cos(a)];
    return { x: x1, y: y1 * Math.cos(b) - z * Math.sin(b), z: y1 * Math.sin(b) + z * Math.cos(b) };
  });
  return { keypoints3D };
}
expect('rotated and tilted: gripping hand still gripping', isGripping(rotated(hand({ curled: true }))));
expect('rotated and tilted: open hand still open', !foldedFingers(rotated(hand({ curled: false }))).some(Boolean));
expect('rotated and tilted: gap unchanged', Math.abs(pinchGapCm(rotated(hand({ curled: true, gapCm: 7 }))) - 7) < 1e-9);

expect('gap <= closed -> 0', gapToLevel(1, 2, 10) === 0 && gapToLevel(2, 2, 10) === 0);
expect('gap >= open -> 255', gapToLevel(10, 2, 10) === 255 && gapToLevel(25, 2, 10) === 255);
expect('gap halfway -> 128', gapToLevel(6, 2, 10) === 128);

// Seeded noise so the run is repeatable.
let seed = 1;
const noise = () => ((seed = (seed * 16807) % 2147483647) / 2147483647 - 0.5) * 2;
const params = { minCutoff: 0.5, beta: 0.2, dCutoff: 1.0 };   // same as GAP_SMOOTHING in sketch.js
const fps = 30;

{
  const f = new OneEuroFilter(params);
  expect('first sample passes through', f.filter(4.2, 0) === 4.2);
  expect('repeated timestamp returns last value', f.filter(9, 0) === 4.2);
}
{
  // A still hand: 6 cm with +-0.4 cm jitter for 3 s.
  const f = new OneEuroFilter(params);
  const levels = [];
  for (let i = 0; i < 3 * fps; i++) {
    const raw = 6 + 0.4 * noise();
    const out = f.filter(raw, i / fps);
    if (i >= fps) levels.push({ raw: gapToLevel(raw, 2, 10), out: gapToLevel(out, 2, 10) });
  }
  const spread = key => Math.max(...levels.map(l => l[key])) - Math.min(...levels.map(l => l[key]));
  expect('still hand: filtered level spread <= 1/4 of raw', spread('out') * 4 <= spread('raw'),
    `(raw ${spread('raw')}, filtered ${spread('out')} levels)`);
}
{
  // Opening the fingers from 3 cm to 9 cm in 0.3 s, then holding.
  const f = new OneEuroFilter(params);
  let settledAt = null;
  for (let i = 0; i < 2 * fps; i++) {
    const t = i / fps;
    const target = t < 0.5 ? 3 : t < 0.8 ? 3 + 6 * (t - 0.5) / 0.3 : 9;
    const out = f.filter(target, t);
    if (t >= 0.8 && settledAt === null && Math.abs(out - 9) < 0.25) settledAt = t;
  }
  const lag = settledAt === null ? Infinity : Math.round((settledAt - 0.8) * 1000);
  expect('fast move: within 0.25 cm of target <= 250 ms after it stops', lag <= 250, `(${lag} ms)`);
}
{
  const f = new OneEuroFilter(params);
  f.filter(3, 0);
  f.filter(3, 1 / fps);
  f.reset();
  expect('reset: next sample passes through', f.filter(8, 2 / fps) === 8);
}

console.log(ok ? 'ALL PASS' : 'SOME FAILED');
process.exit(ok ? 0 : 1);
