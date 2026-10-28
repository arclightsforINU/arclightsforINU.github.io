# Measures domino cycle periods in a hardware video from the blue LED glow, frame by frame.
import subprocess
import sys

W, H = 192, 108
video = sys.argv[1]
window = [float(t) for t in sys.argv[2:4]]
raw = subprocess.run(
    ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", video, "-vf", f"scale={W}:{H}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
    capture_output=True, check=True).stdout
fps_text = subprocess.run(
    ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=avg_frame_rate", "-of", "default=nw=1:nk=1", video],
    capture_output=True, text=True, check=True).stdout.strip()
num, den = map(int, fps_text.split("/"))
fps = num / den

size = W * H
frames = [raw[i * size * 3 + 2:(i + 1) * size * 3:3] for i in range(len(raw) // (size * 3))]
start = int(window[0] * fps) if window else 0
frames = frames[start:int(window[1] * fps)] if window else frames
mean = [sum(f[p] for f in frames) / len(frames) for p in range(size)]
var = [sum((f[p] - mean[p]) ** 2 for f in frames) / len(frames) for p in range(size)]
cut = sorted(var)[int(size * 0.99)]
mask = [p for p in range(size) if var[p] >= cut]
signal = [sum(f[p] for p in mask) / len(mask) for f in frames]

ordered = sorted(signal)
lo, hi = ordered[len(ordered) // 10], ordered[len(ordered) * 9 // 10]
up, down = lo + (hi - lo) * 0.6, lo + (hi - lo) * 0.4
rises, falls, on = [], [], False
for i, v in enumerate(signal):
    if not on and v > up:
        on = True
        rises.append(i)
    elif on and v < down:
        on = False
        falls.append(i)

xs, ys = [p % W for p in mask], [p // W for p in mask]
print(f"frames {len(frames)} @ {fps:g} fps, glow area x{min(xs)}-{max(xs)} y{min(ys)}-{max(ys)} of {W}x{H}")
periods = []
for a, b in zip(rises, rises[1:]):
    fall = next((f for f in falls if f > a), b)
    period = (b - a) / fps * 1000
    periods.append(period)
    print(f"start {(start + a) / fps:6.2f}s  period {period:5.0f} ms  lit/period {(fall - a) / (b - a):.2f}")
print(f"cycles {len(periods)}  min {min(periods):.0f} ms  max {max(periods):.0f} ms")
