"""Vigil brand assets — iris mark and banner generation."""

import os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

_DIR = os.path.dirname(os.path.abspath(__file__))

# Idle state colors
_IDLE_EYE = (0, 212, 255)    # #00d4ff
_IDLE_BG  = (10, 10, 18)     # #0a0a12

# Recording state colors
_REC_EYE  = (255, 68, 68)    # #ff4444
_REC_BG   = (18, 8, 8)       # #120808


def render_vigil_eye(size: int = 64, idle: bool = True, almond: bool = True) -> Image.Image:
    """Render the Vigil iris mark as a PIL RGBA image.

    Args:
        size:   Output image size in pixels (square).
        idle:   True = cyan eye, False = red (recording) eye.
        almond: Draw the decorative almond frame. Auto-suppressed at size < 48.

    Returns:
        PIL Image in RGBA mode, size × size.
    """
    eye_c = _IDLE_EYE if idle else _REC_EYE
    bg_c  = _IDLE_BG  if idle else _REC_BG

    scale = 8
    s     = size * scale    # internal canvas side (512 at size=64)
    cx    = s // 2
    cy    = s // 2

    # Geometry (all ratios × s)
    pad    = max(2, int(0.04 * s))
    glow_r = int(0.22 * s)
    ring_r = int(0.14 * s)
    ring_w = max(2, int(0.03 * s))
    pup_r  = int(0.08 * s)
    shi_r  = max(1, int(0.03 * s))
    shi_dx = int(-0.05 * s)
    shi_dy = int(-0.05 * s)
    alm_rx = int(0.32 * s)
    alm_ry = int(0.17 * s)

    img  = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Background circle with cyan border
    draw.ellipse(
        [pad, pad, s - pad, s - pad],
        fill=bg_c + (255,),
        outline=eye_c + (128,),   # 0.5 opacity
        width=max(2, ring_w // 2),
    )

    # Almond frame (decorative, only at size >= 48)
    if almond and size >= 48:
        draw.ellipse(
            [cx - alm_rx, cy - alm_ry, cx + alm_rx, cy + alm_ry],
            outline=eye_c + (102,),   # 0.4 opacity
            width=max(1, ring_w // 3),
        )

    # Radial glow
    glow_img  = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow_img)
    glow_draw.ellipse(
        [cx - glow_r, cy - glow_r, cx + glow_r, cy + glow_r],
        fill=eye_c + (140,),   # 0.55 opacity
    )
    glow_img = glow_img.filter(ImageFilter.GaussianBlur(radius=int(glow_r * 0.6)))
    img  = Image.alpha_composite(img, glow_img)
    draw = ImageDraw.Draw(img)

    # Iris ring
    draw.ellipse(
        [cx - ring_r, cy - ring_r, cx + ring_r, cy + ring_r],
        outline=eye_c + (153,),   # 0.6 opacity
        width=ring_w,
    )

    # Pupil
    draw.ellipse(
        [cx - pup_r, cy - pup_r, cx + pup_r, cy + pup_r],
        fill=eye_c + (255,),
    )

    # Shine dot (top-left offset)
    sx, sy = cx + shi_dx, cy + shi_dy
    draw.ellipse(
        [sx - shi_r, sy - shi_r, sx + shi_r, sy + shi_r],
        fill=(255, 255, 255, 166),   # 0.65 opacity
    )

    return img.resize((size, size), Image.LANCZOS)


def make_tray_icon(recording: bool = False) -> Image.Image:
    """Return a 64×64 tray icon. Idle = cyan, recording = red."""
    return render_vigil_eye(size=64, idle=not recording)


def generate_app_icon(size: int = 128) -> Image.Image:
    """Vigil eye without the almond frame — for .desktop / launcher use."""
    return render_vigil_eye(size=size, idle=True, almond=False)


def generate_banner(out_path: str | None = None) -> Image.Image:
    """Generate the 1280×640 GitHub banner.

    Saves to out_path if provided. Returns the final PIL Image (RGB).
    """
    w, h = 1280, 640

    # Gradient background (#03030a → #04050e, diagonal)
    xs = np.linspace(0.0, 1.0, w, dtype=np.float32)
    ys = np.linspace(0.0, 1.0, h, dtype=np.float32)
    xg, yg = np.meshgrid(xs, ys)
    t = (xg + yg) * 0.5
    arr = np.zeros((h, w, 3), dtype=np.uint8)
    arr[:, :, 0] = np.clip(3 + t,     0, 255).astype(np.uint8)
    arr[:, :, 1] = np.clip(3 + t * 2, 0, 255).astype(np.uint8)
    arr[:, :, 2] = np.clip(10 + t * 4, 0, 255).astype(np.uint8)
    banner = Image.fromarray(arr, "RGB").convert("RGBA")

    # Grid overlay (36px, #00d4ff at ~2.5% → alpha 6)
    grid = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    gd   = ImageDraw.Draw(grid)
    for x in range(0, w, 36):
        gd.line([(x, 0), (x, h)], fill=(0, 212, 255, 6))
    for y in range(0, h, 36):
        gd.line([(0, y), (w, y)], fill=(0, 212, 255, 6))
    banner = Image.alpha_composite(banner, grid)

    # Center glow blob (200px radius, #00d4ff at 12% → alpha 30)
    glow_cx = w // 2
    glow_cy = h // 2 - 60
    glow    = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    gd2     = ImageDraw.Draw(glow)
    gr      = 200
    gd2.ellipse(
        [glow_cx - gr, glow_cy - gr, glow_cx + gr, glow_cy + gr],
        fill=(0, 212, 255, 30),
    )
    glow   = glow.filter(ImageFilter.GaussianBlur(radius=80))
    banner = Image.alpha_composite(banner, glow)

    # Vigil eye (160px, centered horizontally, above vertical center)
    eye    = render_vigil_eye(size=160, idle=True)
    eye_x  = (w - 160) // 2
    eye_y  = h // 2 - 200
    banner.paste(eye, (eye_x, eye_y), eye)

    # Text (VIGIL + tagline)
    _draw_banner_text(banner, w, h)

    result = banner.convert("RGB")
    if out_path:
        result.save(out_path)
    return result


def _draw_banner_text(img: Image.Image, w: int, h: int) -> None:
    """Draw VIGIL brand name and tagline onto the banner image in-place."""
    try:
        from PIL import ImageFont
        import subprocess
        fc = subprocess.run(
            ["fc-match", "DejaVu Sans:bold", "--format=%{file}"],
            capture_output=True, text=True,
        ).stdout.strip()
        font_big = ImageFont.truetype(fc, 72) if fc else ImageFont.load_default()
        fc2 = subprocess.run(
            ["fc-match", "DejaVu Sans", "--format=%{file}"],
            capture_output=True, text=True,
        ).stdout.strip()
        font_tag = ImageFont.truetype(fc2, 20) if fc2 else font_big
    except Exception:
        font_big = None
        font_tag = None

    bd     = ImageDraw.Draw(img)
    text_y = h // 2 + 20

    if font_big:
        letters  = list("VIGIL")
        spacing  = 22
        widths   = [font_big.getlength(c) for c in letters]
        total_w  = sum(widths) + spacing * (len(letters) - 1)
        lx       = int((w - total_w) // 2)
        for ch, cw in zip(letters, widths):
            bd.text((lx, text_y), ch, fill=(232, 234, 240, 255), font=font_big)
            lx += int(cw) + spacing

        tagline = "VOICE · AI · LINUX"
        tl_w    = font_tag.getlength(tagline)
        tl_x    = int((w - tl_w) // 2)
        tl_y    = text_y + 90
        bd.text((tl_x, tl_y), tagline, fill=(0, 212, 255, 140), font=font_tag)
    else:
        bd.text((w // 2 - 40, text_y), "VIGIL", fill=(232, 234, 240, 255))
