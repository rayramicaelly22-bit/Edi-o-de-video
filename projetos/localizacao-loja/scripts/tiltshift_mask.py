"""Máscara do tilt-shift (branco = desfocado): topo borrado até ~30% da altura, base levemente borrada."""
import sys

import numpy as np
from PIL import Image

W, H = 1080, 1920
y = np.arange(H) / H


def smooth(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


top = 1 - smooth(0.0, 0.30, y)
bottom = 0.55 * smooth(0.86, 1.0, y)
m = np.clip(top + bottom, 0, 1)
img = (np.repeat(m[:, None], W, axis=1) * 255).astype(np.uint8)
Image.fromarray(img, "L").convert("RGB").save(sys.argv[1])
