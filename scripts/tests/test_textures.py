import sys, pathlib, subprocess
import numpy as np
from PIL import Image
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import textures

def _noise(h=64, w=64, seed=1):
    rng = np.random.default_rng(seed)
    return rng.random((h, w, 3), dtype=np.float32)

def _gradient(h=64, w=64):
    y, x = np.mgrid[0:h, 0:w]
    a = np.stack([x / w, y / h, np.full((h, w), 0.5)], axis=-1)
    return a.astype(np.float32)

def test_make_seamless_matches_opposite_edges():
    a = _gradient()
    s = textures.make_seamless(a)
    assert s.shape == a.shape and s.dtype == np.float32
    assert np.abs(s[0, :, :] - s[-1, :, :]).mean() < 0.1 * np.abs(a[0, :, :] - a[-1, :, :]).mean()
    assert np.abs(s[:, 0, :] - s[:, -1, :]).mean() < 0.1 * np.abs(a[:, 0, :] - a[:, -1, :]).mean()

def test_normal_is_blue_dominant_and_uint8():
    n = textures.normal_from_luminance(_noise(), strength=6.0, blur=2.5)
    assert n.dtype == np.uint8 and n.shape == (64, 64, 3)
    assert n[..., 2].mean() > 150

def test_flat_image_gives_neutral_normal():
    flat = np.full((16, 16, 3), 0.5, dtype=np.float32)
    n = textures.normal_from_luminance(flat)
    assert np.allclose(n[..., :2], 127, atol=2) and (n[..., 2] >= 253).all()

def test_cli_writes_both_files(tmp_path):
    src = tmp_path / "in.png"
    Image.fromarray((_noise() * 255).astype(np.uint8), "RGB").save(src)
    alb, nrm = tmp_path / "alb.png", tmp_path / "nrm.png"
    r = subprocess.run([sys.executable, str(pathlib.Path(textures.__file__)), str(src), str(alb), str(nrm), "--strength", "6"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert Image.open(alb).size == (64, 64) and Image.open(nrm).size == (64, 64)
