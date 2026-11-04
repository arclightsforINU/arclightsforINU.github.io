// Finger dimmer: the gap between thumb and index finger moves a p5 slider, and the slider's
// level goes to the Arduino (finger_led.ino) as "LEVEL:<0-255>".
// The slider follows the fingers only while middle, ring and pinky are folded; open the hand
// or take it away and the level stays where it was.

const BAUD_RATE = 9600;
const CLOSED_CM = 2;     // thumb-index gap at or below this gives level 0
const OPEN_CM = 10;      // gap at or above this gives level 255
const GAP_SMOOTHING = { minCutoff: 0.5, beta: 0.2, dCutoff: 1.0 };   // One Euro filter, gap in cm

const COLORS = { active: '#f59e0b', idle: '#e2e8f0', folded: '#22c55e', open: '#94a3b8' };

let video, slider, link;
let hand = null;         // latest detected hand, or null
let gapCm = null;        // smoothed thumb-index gap of that hand
let folded = [];         // middle, ring, pinky
let gripping = false;
let arduinoReady = false;
let arduinoDuty = null;  // PWM duty the Arduino last reported
let linkBusy = false;
const gapFilter = new OneEuroFilter(GAP_SMOOTHING);

async function setup() {
  createCanvas(640, 480).parent('stage');
  textFont('sans-serif');
  // Ask for 4:3 so the frame is not stretched into the 640x480 canvas.
  video = createCapture({ video: { width: 640, height: 480 }, audio: false }, { flipped: true });
  video.size(640, 480);
  video.hide();

  slider = createSlider(0, 255, 0, 1).parent('slider-slot').id('level');
  slider.input(levelChanged);
  link = new SerialLink(BAUD_RATE, arduinoSaid, arduinoClosed);
  select('#connect').mousePressed(toggleArduino);
  if (!('serial' in navigator)) showLink('이 브라우저는 Web Serial을 지원하지 않습니다. Chrome이나 Edge로 여세요.');

  const handPose = await ml5.handPose({ maxHands: 1, flipped: true });
  handPose.detectStart(video, handsFound);
  select('#hint').html('엄지와 검지만 펴고 나머지 세 손가락을 접으면 조절됩니다.');
}

function handsFound(results) {
  hand = results[0] ?? null;
  if (!hand) {
    gapFilter.reset();
    gripping = false;
    return;
  }
  gapCm = gapFilter.filter(pinchGapCm(hand), performance.now() / 1000);
  folded = foldedFingers(hand);
  gripping = folded.every(Boolean);
  if (!gripping) return;
  const level = gapToLevel(gapCm, CLOSED_CM, OPEN_CM);
  if (level === Number(slider.value())) return;
  slider.value(level);
  levelChanged();
}

function levelChanged() {
  select('#level-out').html(slider.value() + ' / 255');
  if (arduinoReady) link.sendLatest('LEVEL:' + slider.value());
}

async function toggleArduino() {
  if (linkBusy) return;
  linkBusy = true;
  try {
    if (link.isOpen) {
      await link.close();
    } else {
      await link.open();
      arduinoReady = false;
      showLink('연결됨, Arduino 준비 기다리는 중...');
    }
  } catch (error) {
    showLink(error.name === 'NotFoundError' ? '포트를 고르지 않았습니다.' : '연결 실패: ' + error.message);
  } finally {
    linkBusy = false;
    select('#connect').html(link.isOpen ? 'Arduino 연결 끊기' : 'Arduino 연결');
  }
}

// The board resets when the port opens and prints READY when it can listen again.
function arduinoSaid(line) {
  if (line === 'READY') {
    arduinoReady = true;
    showLink('연결됨');
    levelChanged();
    return;
  }
  const duty = line.match(/^PWM:(\d+)$/);
  if (duty) {
    arduinoDuty = Number(duty[1]);
    select('#duty-out').html('Arduino PWM ' + arduinoDuty + ' / 255');
    return;
  }
  showLink('Arduino: ' + line);
}

function arduinoClosed() {
  arduinoReady = false;
  arduinoDuty = null;
  showLink('연결 안 됨');
  select('#duty-out').html('');
  select('#connect').html('Arduino 연결');
}

function showLink(message) {
  select('#link-state').html(message);
}

function draw() {
  image(video, 0, 0, width, height);
  if (hand) drawHand(hand);
  drawBadge();
}

function drawHand(h) {
  const k = h.keypoints;
  [12, 16, 20].forEach((tip, i) => {
    noStroke();
    fill(folded[i] ? COLORS.folded : COLORS.open);
    circle(k[tip].x, k[tip].y, 14);
  });

  const thumb = k[4];
  const index = k[8];
  const color = gripping ? COLORS.active : COLORS.idle;
  stroke(color);
  strokeWeight(gripping ? 5 : 2);
  line(thumb.x, thumb.y, index.x, index.y);
  noFill();
  circle(thumb.x, thumb.y, 22);
  circle(index.x, index.y, 22);

  const label = gapCm.toFixed(1) + ' cm';
  const x = (thumb.x + index.x) / 2 + 16;
  const y = (thumb.y + index.y) / 2;
  textSize(16);
  noStroke();
  fill(0, 160);
  rect(x - 6, y - 15, textWidth(label) + 12, 24, 6);
  fill(color);
  text(label, x, y + 2);
}

function drawBadge() {
  const message = !hand ? '손을 보여 주세요'
    : gripping ? '조절 중'
    : '고정 (세 손가락을 접으면 조절)';
  textSize(18);
  noStroke();
  fill(0, 170);
  rect(12, 12, textWidth(message) + 24, 34, 8);
  fill(gripping ? COLORS.active : 255);
  text(message, 24, 35);
}
