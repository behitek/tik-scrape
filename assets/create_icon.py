"""Generate assets/icon.ico and assets/icon.png for the app."""
import math
import os
from PIL import Image, ImageDraw

TEAL = (37, 244, 238)
RED  = (254, 44, 85)
BG   = (10, 10, 15)
WHITE = (255, 255, 255)


def draw_icon(size: int) -> Image.Image:
    scale = 4
    s = size * scale
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # rounded-square background
    r = s // 6
    d.rounded_rectangle([0, 0, s - 1, s - 1], radius=r, fill=(*BG, 255))

    # teal top-right arc accent (TikTok style)
    arc_r = s * 0.38
    cx, cy = s * 0.62, s * 0.38
    d.ellipse(
        [cx - arc_r, cy - arc_r, cx + arc_r, cy + arc_r],
        outline=(*TEAL, 200), width=max(1, s // 26),
    )

    # draw camera-body shape
    cam_margin = s * 0.18
    cam_l = cam_margin
    cam_r = s - cam_margin
    cam_t = s * 0.30
    cam_b = s * 0.72
    cam_r_rad = s // 18
    body_color = (*WHITE, 230)
    d.rounded_rectangle(
        [cam_l, cam_t, cam_r, cam_b],
        radius=cam_r_rad, fill=None, outline=body_color, width=max(2, s // 22),
    )

    # lens circle
    lens_cx, lens_cy = s * 0.50, (cam_t + cam_b) / 2
    lens_r = (cam_b - cam_t) * 0.28
    d.ellipse(
        [lens_cx - lens_r, lens_cy - lens_r, lens_cx + lens_r, lens_cy + lens_r],
        outline=(*TEAL, 255), width=max(2, s // 22),
    )

    # lens inner dot
    dot_r = lens_r * 0.38
    d.ellipse(
        [lens_cx - dot_r, lens_cy - dot_r, lens_cx + dot_r, lens_cy + dot_r],
        fill=(*TEAL, 255),
    )

    # flash bump on top
    bump_w = s * 0.14
    bump_h = s * 0.10
    bump_x = s * 0.25
    bump_y = cam_t - bump_h + (s // 50)
    d.rounded_rectangle(
        [bump_x, bump_y, bump_x + bump_w, cam_t + (s // 50)],
        radius=s // 30, fill=body_color,
    )

    # red dot (record indicator)
    dot2_r = s * 0.055
    d.ellipse(
        [cam_r - cam_margin * 0.9 - dot2_r, cam_t + cam_margin * 0.3,
         cam_r - cam_margin * 0.9 + dot2_r, cam_t + cam_margin * 0.3 + dot2_r * 2],
        fill=(*RED, 240),
    )

    img = img.resize((size, size), Image.LANCZOS)
    return img


def main():
    out_dir = os.path.dirname(__file__)
    sizes = [16, 32, 48, 64, 128, 256]
    images = [draw_icon(s) for s in sizes]

    ico_path = os.path.join(out_dir, "icon.ico")
    images[0].save(
        ico_path,
        format="ICO",
        sizes=[(s, s) for s in sizes],
        append_images=images[1:],
    )
    print(f"Saved {ico_path}")

    png_path = os.path.join(out_dir, "icon.png")
    images[-1].save(png_path, format="PNG")
    print(f"Saved {png_path}")


if __name__ == "__main__":
    main()
