"""临时配乐：按 timeline.json 合成一条声音轨，只用来在预览里感受节奏。正式版请换成真的配乐和你的旁白。

    python3 sound.py          → ../temp_audio.wav（48kHz 立体声）

里面有：低频铺底（随场景换和弦）、三次盖印的磬声、连乘时的轻响、26 颗星亮起时的一点高音、
翻页声、费米那段的无线电底噪、金唱片那段的唱片沙沙声、几个钢琴单音。全部用正弦波和噪声算出来，没有采样素材，不涉及版权。
"""

import json
import wave
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
SR = 48000
TL = json.loads((HERE / "timeline.json").read_text(encoding="utf-8"))
M = TL["markers"]
TOTAL = TL["total"]
N = int(TOTAL * SR)
rng = np.random.default_rng(2026)


def sent_start(s):
    return next(x["start"] for x in TL["sentences"] if s in x["text"])


def tt(dur):
    return np.arange(int(dur * SR)) / SR


def band(x, lo, hi):
    """FFT 带通，边缘做平滑过渡，避免振铃。"""
    f = np.fft.rfftfreq(len(x), 1 / SR)
    m = 1 / (1 + (lo / np.maximum(f, 1)) ** 4) / (1 + (f / hi) ** 4)
    return np.fft.irfft(np.fft.rfft(x) * m, len(x))


def reverb(x, secs=2.2, wet=.35, seed=1):
    r = np.random.default_rng(seed)
    n = int(secs * SR)
    ir = r.standard_normal(n) * np.exp(-np.arange(n) / SR * 3.2)
    ir = band(ir, 200, 7000)
    ir /= np.sqrt(np.sum(ir ** 2))
    size = 1 << int(np.ceil(np.log2(len(x) + n)))
    y = np.fft.irfft(np.fft.rfft(x, size) * np.fft.rfft(ir, size), size)[: len(x) + n]
    out = np.zeros(len(x) + n)
    out[: len(x)] += x * (1 - wet)
    return out + y * wet


L = np.zeros(N + 10 * SR)
R = np.zeros(N + 10 * SR)


def put(sig, at, gain=1.0, pan=0.0):
    """把单声道信号放到 at 秒处，pan -1（左）到 1（右）。"""
    i = int(at * SR)
    if i >= len(L):
        return
    sig = sig[: len(L) - i]
    L[i:i + len(sig)] += sig * gain * np.sqrt((1 - pan) / 2)
    R[i:i + len(sig)] += sig * gain * np.sqrt((1 + pan) / 2)


# ---------- 低频铺底：随场景换和弦，3 秒交叉淡化 ----------
chords = [
    (0.0, [55.0, 82.41, 110.0, 130.81]),                      # 开场到伦敦：A 小调
    (M["yours"], [43.65, 65.41, 87.31, 110.0]),               # 历书、十二年、你：F
    (M["fermi"], [36.71, 55.0, 73.42]),                       # 银河与城市：D，更空
    (M["spoke"], [65.41, 98.0, 130.81, 164.81]),              # 金唱片：C，亮一点
    (sent_start("你的公式里"), [55.0, 82.41, 110.0, 138.59]),   # 结尾：A 大调，落地
]
t_all = np.arange(N) / SR
pad_l, pad_r = np.zeros(N), np.zeros(N)
for k, (t0, freqs) in enumerate(chords):
    t1 = chords[k + 1][0] if k + 1 < len(chords) else TOTAL
    env = np.clip((t_all - (t0 - 1.5)) / 3, 0, 1) * np.clip(((t1 + 1.5) - t_all) / 3, 0, 1)
    idx = np.nonzero(env)[0]
    tt_ = t_all[idx]
    for j, f in enumerate(freqs):
        amp = (.9 / (1 + j * .45)) * (.75 + .25 * np.sin(2 * np.pi * (.05 + .013 * j) * tt_ + j))
        pad_l[idx] += env[idx] * amp * np.sin(2 * np.pi * (f - .12) * tt_ + j)
        pad_r[idx] += env[idx] * amp * np.sin(2 * np.pi * (f + .12) * tt_ + 2 * j)
air = band(rng.standard_normal(N), 120, 900) * .05
L[:N] += (pad_l + air) * .055
R[:N] += (pad_r + air) * .055


# ---------- 磬：三次盖印 ----------
def bell(f0, dur=7.0):
    x = tt(dur)
    s = np.zeros_like(x)
    for ratio, amp, decay in [(1, 1, 6.0), (2.76, .5, 3.0), (5.40, .25, 1.6), (8.93, .12, .9)]:
        for det in (-.6, .6):
            s += amp * np.exp(-x / decay) * np.sin(2 * np.pi * (f0 * ratio + det) * x)
    s *= np.minimum(1, x / .002)
    hit = band(rng.standard_normal(int(.03 * SR)), 1500, 9000) * np.exp(-np.arange(int(.03 * SR)) / SR / .006) * .6
    s[: len(hit)] += hit
    return reverb(s / np.max(np.abs(s)), 2.8, .4, seed=int(f0))


for at, f0, gain in [(M["s1961"] + 2.0, 329.63, .2), (M["multiplied"] + 1.7, 349.23, .32), (M["inhand"] + 1.6, 440.0, .32)]:
    put(bell(f0), at, gain, -.1)


# ---------- 钢琴单音 ----------
def piano(freqs, dur=6.0):
    x = tt(dur)
    s = np.zeros_like(x)
    for f0 in freqs:
        for n in range(1, 9):
            fn = n * f0 * np.sqrt(1 + .0004 * n * n)
            s += (1 / n ** 1.4) * np.exp(-x / (3.2 / n ** .7)) * np.sin(2 * np.pi * fn * x)
    s *= np.minimum(1, x / .005)
    return reverb(s / np.max(np.abs(s)), 2.4, .45, seed=7)


put(piano([659.25]), M["L"] + 1.2, .16, .2)
put(piano([523.25]), M["spoke"] + .2, .14, -.2)
put(piano([220.0, 329.63, 554.37]), M["out3"] + .1, .2, 0)


# ---------- 连乘的轻响，最后一下重一点 ----------
def tock(f=180, strong=False):
    x = tt(.35)
    s = np.sin(2 * np.pi * f * x * (1 - .35 * x)) * np.exp(-x / (.09 if strong else .06))
    s += band(rng.standard_normal(len(x)), 1200, 4000) * np.exp(-x / .012) * .5
    return reverb(s / np.max(np.abs(s)), 1.2, .3, seed=3)


for at in (M["x20"] + .2, M["x2"] + .2, M["x10"] + .2):
    put(tock(), at, .18, .15)
put(tock(140, True), M["n26"] + .5, .26, 0)


# ---------- 26 颗星亮起：一点高音 ----------
x = tt(3.5)
sh = sum(np.sin(2 * np.pi * f * x) for f in (1760, 2093, 2637)) * np.minimum(1, x / .6) * np.exp(-x / 1.4)
put(reverb(sh / 3, 2.5, .5, seed=5), M["n26"] + .6, .05, .3)

# ---------- 翻页 ----------
x = tt(.7)
swish = band(rng.standard_normal(len(x)), 1500, 6000) * np.sin(np.pi * x / .7) ** 2
put(swish, M["yours"], .12, .4)


# ---------- 费米那段的无线电底噪 ----------
def bed(t0, t1, lo, hi, gain, fade=2.0, clicks=0.0, seed=11):
    n = int((t1 - t0) * SR)
    r = np.random.default_rng(seed)
    s = band(r.standard_normal(n), lo, hi)
    s *= .6 + .4 * np.interp(np.arange(n), np.linspace(0, n, 40), r.random(40))
    if clicks:
        pos = r.integers(0, n - 200, int(clicks * (t1 - t0)))
        for p in pos:
            s[p:p + 120] += r.choice([-1, 1]) * np.exp(-np.arange(120) / 18) * r.uniform(2, 6)
    env = np.clip(np.arange(n) / (fade * SR), 0, 1) * np.clip((n - np.arange(n)) / (fade * SR), 0, 1)
    put(s * env / np.max(np.abs(s)), t0, gain)


bed(M["fermi"], M["cityalso"] + 2, 900, 5000, .035, seed=11)
bed(M["spoke"], sent_start("你的公式里") + .5, 400, 9000, .02, clicks=9, seed=12)

# ---------- 母带：首尾淡入淡出，限幅 ----------
mix = np.stack([L[:N], R[:N]], axis=1)
fade_in = np.clip(np.arange(N) / (2 * SR), 0, 1)
fade_out = np.clip((N - np.arange(N)) / (2.5 * SR), 0, 1)
mix *= (fade_in * fade_out)[:, None]
mix = np.tanh(mix * 1.1) / np.tanh(1.1)
mix *= .89 / max(1e-9, np.max(np.abs(mix)))
pcm = (mix * 32767).astype("<i2")
with wave.open(str(HERE.parent / "temp_audio.wav"), "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(pcm.tobytes())
rms = 20 * np.log10(np.sqrt(np.mean(mix ** 2)) + 1e-12)
print(f"wrote ../temp_audio.wav  {TOTAL:.1f}s  RMS {rms:.1f} dBFS")
