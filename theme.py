"""Vigil unified theme — Pandora × Neon Hybrid palette."""

# ── Backgrounds ───────────────────────────────────────────────────────────
BG_DEEP     = "#03030a"     # deepest background
BG          = "#05050a"     # primary window background
BG_CARD     = "#0a0a12"     # card / elevated surface
BG_HOVER    = "#12121e"     # card hover state
BG_INPUT    = "#0a0a12"     # input fields, sliders

# ── Borders (hex approximations — CTkinter takes no rgba) ─────────────────
# BORDER      ≈ #00d4ff at 12% opacity on BG
# BORDER_GLOW ≈ #00d4ff at 35% opacity on BG
BORDER      = "#0d1a1f"
BORDER_GLOW = "#004d66"

# ── Text ──────────────────────────────────────────────────────────────────
FG          = "#e8eaf0"     # primary text
FG_DIM      = "#8a8f98"     # secondary / muted text
FG_ACCENT   = "#d0d6e0"     # slightly muted

# ── Accent ────────────────────────────────────────────────────────────────
ACCENT       = "#00d4ff"    # cyan accent
ACCENT_HOVER = "#33ddff"    # accent hover
ACCENT_DIM   = "#007acc"    # accent muted

# ── Semantic (unchanged) ──────────────────────────────────────────────────
RED         = "#ff4444"
RED_HOVER   = "#ff6666"
GREEN       = "#55cc77"
YELLOW      = "#ffaa00"

# ── Title bar ─────────────────────────────────────────────────────────────
TITLE_BG    = "#03030a"
CLOSE_HOVER = "#ff4444"

# ── Fonts ─────────────────────────────────────────────────────────────────
FONT_FAMILY = "Segoe UI" if __import__("sys").platform == "win32" else "DejaVu Sans"
FONT_TITLE  = (FONT_FAMILY, 12, "bold")
FONT_BODY   = (FONT_FAMILY, 11)
FONT_SMALL  = (FONT_FAMILY, 10)
FONT_TINY   = (FONT_FAMILY, 9)

# ── Spacing ───────────────────────────────────────────────────────────────
PAD_S  = 4
PAD_M  = 8
PAD_L  = 16
PAD_XL = 24
