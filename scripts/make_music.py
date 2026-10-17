"""Mualliflik huquqisiz, sokin fon musiqasini (ambient/lo-fi) generatsiya qiladi.

Ishlatish:
    python3 scripts/make_music.py music/calm-01.m4a --seed 1 --seconds 40

Har xil --seed har xil akkord va arpedjio beradi. O'zingizning litsenziyasi toza
(royalty-free) treklaringizni ham music/ papkaga tashlashingiz mumkin.
"""
import argparse
import subprocess
import tempfile
import wave
from pathlib import Path

import numpy as np

SR = 44100
PROGRESSIONS = [
    [[57, 60, 64], [53, 57, 60], [48, 52, 55], [55, 59, 62]],  # Am F C G
    [[50, 53, 57], [46, 50, 53], [53, 57, 60], [48, 52, 55]],  # Dm Bb F C
    [[52, 55, 59], [48, 52, 55], [55, 59, 62], [50, 54, 57]],  # Em C G D
    [[48, 52, 55, 59], [45, 48, 52, 55], [41, 45, 48, 52], [43, 47, 50, 53]],  # Cmaj7 Am7 Fmaj7 G7
]


def hz(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


def envelope(n, attack, release):
    env = np.ones(n)
    a, r = int(attack * SR), int(release * SR)
    env[:a] = np.linspace(0, 1, a)
    env[-r:] *= np.linspace(1, 0, r)
    return env


def pad(freq, n, rng):
    t = np.arange(n) / SR
    detune = 1 + rng.uniform(-0.002, 0.002)
    wave_ = (np.sin(2 * np.pi * freq * t) + 0.35 * np.sin(2 * np.pi * freq * 2 * detune * t)
             + 0.12 * np.sin(2 * np.pi * freq * 3 * t))
    return wave_ * envelope(n, 1.2, 1.5)


def pluck(freq, n):
    t = np.arange(n) / SR
    return np.sin(2 * np.pi * freq * t) * np.exp(-t * 4.5)


def echo(signal, delay=0.33, feedback=0.35, repeats=4):
    out = signal.copy()
    d = int(delay * SR)
    for i in range(1, repeats + 1):
        shifted = np.zeros_like(signal)
        shifted[d * i:] = signal[:-d * i] * feedback ** i
        out += shifted
    return out


def generate(seconds, seed):
    rng = np.random.default_rng(seed)
    prog = PROGRESSIONS[seed % len(PROGRESSIONS)]
    bar = 4.0
    total = int(seconds * SR)
    bar_n = int(bar * SR)
    bars = int(np.ceil(seconds / bar))
    mix = np.zeros(bars * bar_n + SR * 2)
    step = bar / 8
    for b in range(bars):
        chord = prog[b % len(prog)]
        start = b * bar_n
        for note in chord:
            mix[start:start + bar_n + SR] += 0.18 * pad(hz(note - 12), bar_n + SR, rng)
        mix[start:start + bar_n] += 0.22 * pad(hz(chord[0] - 24), bar_n, rng)
        for s in range(8):
            if rng.random() < 0.75:
                note = chord[rng.integers(len(chord))] + 12 * rng.integers(0, 2)
                p0 = start + int(s * step * SR)
                n = int(1.2 * SR)
                mix[p0:p0 + n] += 0.12 * pluck(hz(note), len(mix[p0:p0 + n]))
    mix = echo(mix)[:total]
    mix *= envelope(total, 1.5, 2.5)
    mix /= np.max(np.abs(mix)) + 1e-9
    return (mix * 0.8 * 32767).astype(np.int16)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--seconds", type=float, default=40)
    args = ap.parse_args()

    audio = generate(args.seconds, args.seed)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".wav") as tmp:
        with wave.open(tmp.name, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(SR)
            w.writeframes(audio.tobytes())
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", tmp.name,
                        "-c:a", "aac", "-b:a", "160k", "-ac", "2", str(out)], check=True)
    print(out)


if __name__ == "__main__":
    main()
