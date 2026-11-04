// Hand geometry for the finger dimmer. Nothing here calls p5 or ml5, so it runs in tests too.
//
// Landmarks follow MediaPipe's 21-point hand layout. ml5 handPose gives each hand both
// `keypoints` (pixels on the video) and `keypoints3D` (world coordinates in metres around the
// hand's centre). Distances here use keypoints3D: they keep the hand's real size whether it is
// near the camera or far away, and do not shrink when the hand turns sideways.

const WRIST = 0;
const THUMB_TIP = 4;
const INDEX_TIP = 8;
const CURLING_FINGERS = [   // middle, ring and pinky as [PIP joint, fingertip]
  [10, 12],
  [14, 16],
  [18, 20],
];

function distance3D(a, b) {
  return Math.hypot(a.x - b.x, a.y - b.y, a.z - b.z);
}

function pinchGapCm(hand) {
  return 100 * distance3D(hand.keypoints3D[THUMB_TIP], hand.keypoints3D[INDEX_TIP]);
}

// A finger is folded when its tip is nearer the wrist than its middle joint;
// a straight finger always reaches past that joint.
function foldedFingers(hand) {
  const k = hand.keypoints3D;
  return CURLING_FINGERS.map(([pip, tip]) => distance3D(k[tip], k[WRIST]) < distance3D(k[pip], k[WRIST]));
}

function isGripping(hand) {
  return foldedFingers(hand).every(Boolean);
}

function gapToLevel(gapCm, closedCm, openCm) {
  const t = (gapCm - closedCm) / (openCm - closedCm);
  return Math.round(255 * Math.min(1, Math.max(0, t)));
}

// One Euro filter: Casiez, Roussel and Vogel, "1 Euro Filter", CHI 2012.
// A low-pass filter whose cutoff frequency rises with the signal's speed, so a still hand
// reads steady and a moving hand is followed without noticeable lag.
class OneEuroFilter {
  constructor({ minCutoff, beta, dCutoff }) {
    this.minCutoff = minCutoff;   // Hz, smoothing while still
    this.beta = beta;             // how fast the cutoff rises with speed
    this.dCutoff = dCutoff;       // Hz, smoothing of the speed estimate
    this.reset();
  }

  reset() {
    this.time = null;
  }

  filter(value, timeSeconds) {
    if (this.time === null) {
      this.time = timeSeconds;
      this.raw = value;
      this.value = value;
      this.speed = 0;
      return value;
    }
    const dt = timeSeconds - this.time;
    if (dt <= 0) return this.value;
    this.time = timeSeconds;
    this.speed += smoothingFactor(this.dCutoff, dt) * ((value - this.raw) / dt - this.speed);
    this.raw = value;
    const cutoff = this.minCutoff + this.beta * Math.abs(this.speed);
    this.value += smoothingFactor(cutoff, dt) * (value - this.value);
    return this.value;
  }
}

// Weight of the new sample in an exponential low-pass filter with the given cutoff frequency.
function smoothingFactor(cutoffHz, dt) {
  const r = 2 * Math.PI * cutoffHz * dt;
  return r / (r + 1);
}
