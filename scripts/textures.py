"""Seamless tile plus wrap-aware normal map, the-archive's verified recipe.

(a) seamless: roll the image by half in both axes, then smoothstep cross-fade
    the original against the rolled copy weighted by distance to the border
    (border trusts the rolled, continuous copy; center trusts the original).
(b) normal: wrap-aware Sobel on a Gaussian-blurred luminance of the SEAMLESS
    image at the given strength. Strength ~6 makes a flat print read as form.

CLI: python textures.py <in.png> <out_albedo.png> <out_normal.png> [--strength 6] [--blur 2.5]
"""
from __future__ import annotations

import argparse
import numpy as np
from PIL import Image, ImageFilter


def make_seamless(rgb: np.ndarray, band: float = 0.18) -> np.ndarray:
    a = rgb.astype(np.float32)
    H, W, _ = a.shape
    rolled = np.roll(np.roll(a, H // 2, axis=0), W // 2, axis=1)
    yy = np.linspace(0, 1, H, endpoint=False)
    xx = np.linspace(0, 1, W, endpoint=False)
    dy = np.minimum(yy, 1 - yy)
    dx = np.minimum(xx, 1 - xx)
    DX, DY = np.meshgrid(dx, dy)
    d = np.minimum(DX, DY)
    t = np.clip(d / band, 0, 1)
    w = (t * t * (3 - 2 * t))[..., None]
    return (a * w + rolled * (1 - w)).astype(np.float32)


def _sobel_wrap(h: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    kx = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], dtype=np.float32)
    ky = kx.T
    gx = np.zeros_like(h)
    gy = np.zeros_like(h)
    for i in range(3):
        for j in range(3):
            sh = np.roll(np.roll(h, i - 1, axis=0), j - 1, axis=1)
            gx += kx[i, j] * sh
            gy += ky[i, j] * sh
    return gx, gy


def normal_from_luminance(rgb: np.ndarray, strength: float = 6.0, blur: float = 2.5) -> np.ndarray:
    a = rgb.astype(np.float32)
    lum = 0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]
    lum_img = Image.fromarray(np.clip(lum * 255, 0, 255).astype(np.uint8), "L")
    if blur > 0:
        lum_img = lum_img.filter(ImageFilter.GaussianBlur(radius=blur))
    h = np.asarray(lum_img, dtype=np.float32) / 255.0
    gx, gy = _sobel_wrap(h)
    nx, ny, nz = -gx * strength, -gy * strength, np.ones_like(h)
    ln = np.sqrt(nx * nx + ny * ny + nz * nz)
    nrm = np.stack([nx / ln * 0.5 + 0.5, ny / ln * 0.5 + 0.5, nz / ln * 0.5 + 0.5], axis=-1) * 255.0
    return np.clip(nrm, 0, 255).astype(np.uint8)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("inp")
    p.add_argument("out_albedo")
    p.add_argument("out_normal")
    p.add_argument("--strength", type=float, default=6.0)
    p.add_argument("--blur", type=float, default=2.5)
    p.add_argument("--band", type=float, default=0.18)
    args = p.parse_args()
    rgb = np.asarray(Image.open(args.inp).convert("RGB"), dtype=np.float32) / 255.0
    seam = make_seamless(rgb, band=args.band)
    Image.fromarray(np.clip(seam * 255, 0, 255).astype(np.uint8), "RGB").save(args.out_albedo)
    Image.fromarray(normal_from_luminance(seam, args.strength, args.blur), "RGB").save(args.out_normal)
    print("wrote", args.out_albedo, args.out_normal, "strength", args.strength, "blur", args.blur)


if __name__ == "__main__":
    main()
