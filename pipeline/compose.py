"""Coloca o motion atras da pessoa: a mascara de segmentacao deixa a pessoa por cima."""
import subprocess

import mediapipe as mp
import numpy as np

W, H, FPS = 1080, 1920, 30
BASE = "base.mp4"
OVERLAY = "../motion/out/overlay.mov"
VIDEO_ONLY = "motion_video.mp4"
OUT = "motion_base.mp4"

segmenter = mp.solutions.selfie_segmentation.SelfieSegmentation(model_selection=0)

base_frames = subprocess.Popen(
    ["ffmpeg", "-v", "error", "-i", BASE, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
    stdout=subprocess.PIPE,
)
over_frames = subprocess.Popen(
    ["ffmpeg", "-v", "error", "-i", OVERLAY, "-f", "rawvideo", "-pix_fmt", "rgba", "-"],
    stdout=subprocess.PIPE,
)
encoder = subprocess.Popen(
    ["ffmpeg", "-y", "-v", "error",
     "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
     "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", VIDEO_ONLY],
    stdin=subprocess.PIPE,
)

frame_bytes = W * H * 3
over_bytes = W * H * 4
n = 0
while True:
    b = base_frames.stdout.read(frame_bytes)
    o = over_frames.stdout.read(over_bytes)
    if len(b) < frame_bytes or len(o) < over_bytes:
        break
    base = np.frombuffer(b, np.uint8).reshape(H, W, 3).astype(np.float32)
    ov = np.frombuffer(o, np.uint8).reshape(H, W, 4).astype(np.float32)
    rgb_ov = ov[..., :3]
    a = ov[..., 3:4] / 255.0

    # mascara da pessoa (1 = pessoa, 0 = fundo)
    res = segmenter.process(np.frombuffer(b, np.uint8).reshape(H, W, 3))
    m = np.clip((res.segmentation_mask - 0.35) / 0.3, 0.0, 1.0)[..., None]

    # fundo = motion por cima do video; pessoa = video original por cima do motion
    bg = a * rgb_ov + (1.0 - a) * base
    out = m * base + (1.0 - m) * bg
    encoder.stdin.write(np.clip(out, 0, 255).astype(np.uint8).tobytes())
    n += 1
    if n % 300 == 0:
        print("frames:", n, flush=True)

encoder.stdin.close()
encoder.wait()
base_frames.kill()
over_frames.kill()

# junta o video composto com o audio do base
subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", VIDEO_ONLY, "-i", BASE,
                "-map", "0:v", "-map", "1:a", "-c", "copy", OUT], check=True)
print("composto:", n, "frames")

