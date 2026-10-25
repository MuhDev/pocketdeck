import os
import io
import json
import glob
import math
import shutil
import hashlib
import ctypes
import threading
import urllib.request
from urllib.parse import urlparse
from ctypes import wintypes
from PIL import Image, ImageDraw, ImageFont

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_ICONS_DIR = os.path.join(ROOT_DIR, "data", "icons")
CACHE_DIR = os.path.join(DATA_ICONS_DIR, "cache")
CUSTOM_DIR = os.path.join(DATA_ICONS_DIR, "custom")
META_PATH = os.path.join(CACHE_DIR, "meta.json")

os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(CUSTOM_DIR, exist_ok=True)

_meta_lock = threading.Lock()
_process_exe_map: dict[str, str] = {}

def register_process_exe(proc_name: str, exe_path: str):
    """Caches a mapping from process base name (without .exe) to full executable path."""
    if proc_name and exe_path:
        _process_exe_map[proc_name.lower()] = exe_path


def _load_meta() -> dict[str, dict]:
    with _meta_lock:
        if os.path.exists(META_PATH):
            try:
                with open(META_PATH, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}


def _save_meta_entry(key: str, entry: dict):
    with _meta_lock:
        data = {}
        if os.path.exists(META_PATH):
            try:
                with open(META_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = {}
        data[key] = entry
        tmp_path = META_PATH + ".tmp"
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            os.replace(tmp_path, META_PATH)
        except Exception:
            pass


# --- Windows Shell IShellItemImageFactory Structures ---

class GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", ctypes.c_ulong),
        ("Data2", ctypes.c_ushort),
        ("Data3", ctypes.c_ushort),
        ("Data4", ctypes.c_ubyte * 8),
    ]


IID_IShellItemImageFactory = GUID(
    0xBCC18B79,
    0xBA16,
    0x442F,
    (ctypes.c_ubyte * 8)(0x80, 0xC4, 0x8A, 0x59, 0xC3, 0x0C, 0x46, 0x3B),
)


class BITMAP(ctypes.Structure):
    _fields_ = [
        ("bmType", wintypes.LONG),
        ("bmWidth", wintypes.LONG),
        ("bmHeight", wintypes.LONG),
        ("bmWidthBytes", wintypes.LONG),
        ("bmPlanes", wintypes.WORD),
        ("bmBitsPixel", wintypes.WORD),
        ("bmBits", ctypes.c_void_p),
    ]


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD),
        ("biWidth", wintypes.LONG),
        ("biHeight", wintypes.LONG),
        ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD),
        ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD),
        ("biXPelsPerMeter", wintypes.LONG),
        ("biYPelsPerMeter", wintypes.LONG),
        ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD),
    ]


ole32 = ctypes.windll.ole32
shell32 = ctypes.windll.shell32
gdi32 = ctypes.windll.gdi32
user32 = ctypes.windll.user32

SHCreateItemFromParsingName = shell32.SHCreateItemFromParsingName
SHCreateItemFromParsingName.argtypes = [
    wintypes.LPCWSTR,
    ctypes.c_void_p,
    ctypes.POINTER(GUID),
    ctypes.POINTER(ctypes.c_void_p),
]
SHCreateItemFromParsingName.restype = ctypes.c_long


def _extract_shell_icon(parsing_name: str, size: int = 256) -> Image.Image | None:
    """
    Extracts a high-resolution RGBA icon using Windows IShellItemImageFactory::GetImage.
    Supports file paths (.exe, .lnk, .ico, folders) and shell:AppsFolder\\<AppID>.
    """
    try:
        ole32.CoInitialize(None)
    except Exception:
        pass

    ppv = ctypes.c_void_p()
    hr = SHCreateItemFromParsingName(
        parsing_name, None, ctypes.byref(IID_IShellItemImageFactory), ctypes.byref(ppv)
    )
    if hr != 0 or not ppv.value:
        return None

    vtbl = ctypes.cast(ppv, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
    GetImage = ctypes.WINFUNCTYPE(
        ctypes.c_long,
        ctypes.c_void_p,
        ctypes.c_int64,
        ctypes.c_int,
        ctypes.POINTER(wintypes.HBITMAP),
    )(vtbl[3])
    Release = ctypes.WINFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p)(vtbl[2])

    hbm = wintypes.HBITMAP()
    size_packed = (size << 32) | size
    # SIIGBF_BIGGERSIZEOK (0x01) | SIIGBF_ICONONLY (0x04)
    hr2 = GetImage(ppv, size_packed, 0x04 | 0x01, ctypes.byref(hbm))
    if (hr2 != 0 or not hbm.value):
        # Retry without BIGGERSIZEOK
        hr2 = GetImage(ppv, size_packed, 0x04, ctypes.byref(hbm))
    Release(ppv)

    if hr2 != 0 or not hbm.value:
        return None

    try:
        bm = BITMAP()
        gdi32.GetObjectW(hbm, ctypes.sizeof(BITMAP), ctypes.byref(bm))
        w, h = bm.bmWidth, bm.bmHeight
        if w <= 0 or h <= 0:
            return None

        bmi = BITMAPINFOHEADER()
        bmi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bmi.biWidth = w
        bmi.biHeight = -h  # top-down DIB
        bmi.biPlanes = 1
        bmi.biBitCount = 32
        bmi.biCompression = 0

        buf = ctypes.create_string_buffer(w * h * 4)
        hdc = user32.GetDC(0)
        try:
            gdi32.GetDIBits(hdc, hbm, 0, h, buf, ctypes.byref(bmi), 0)
        finally:
            user32.ReleaseDC(0, hdc)

        img = Image.frombuffer("RGBA", (w, h), buf, "raw", "BGRA", 0, 1).copy()

        # Handle legacy 24-bit icons where alpha channel is all zero
        alpha_min, alpha_max = img.getchannel("A").getextrema()
        if alpha_max == 0:
            img.putalpha(255)

        return _normalize_icon_canvas(img, size)
    except Exception as e:
        print(f"Error converting HBITMAP for {parsing_name}: {e}")
        return None
    finally:
        gdi32.DeleteObject(hbm)


def _normalize_icon_canvas(img: Image.Image, target_size: int = 256) -> Image.Image:
    """
    Ensures the extracted icon fills the 256x256 canvas nicely without tiny 48x48
    postage-stamp margins, while preserving crisp edges and transparency.
    """
    img = img.convert("RGBA")
    bbox = img.getbbox()
    if bbox:
        bw = bbox[2] - bbox[0]
        bh = bbox[3] - bbox[1]
        # If the non-transparent content is small (< 70% of canvas) or larger than target
        if bw > 0 and bh > 0 and (max(bw, bh) < target_size * 0.72 or img.size != (target_size, target_size)):
            cropped = img.crop(bbox)
            usable = int(target_size * 0.88)
            scale = usable / float(max(bw, bh))
            new_w = max(1, int(round(bw * scale)))
            new_h = max(1, int(round(bh * scale)))
            resample = Image.Resampling.LANCZOS if scale < 2.0 else Image.Resampling.BICUBIC
            resized = cropped.resize((new_w, new_h), resample)
            canvas = Image.new("RGBA", (target_size, target_size), (0, 0, 0, 0))
            ox = (target_size - new_w) // 2
            oy = (target_size - new_h) // 2
            canvas.paste(resized, (ox, oy), resized)
            return canvas
    if img.size != (target_size, target_size):
        img = img.resize((target_size, target_size), Image.Resampling.LANCZOS)
    return img


def extract_dominant_accent(img: Image.Image) -> str:
    """
    Computes a vibrant hex color (#RRGGBB) from an RGBA icon image for key glow tinting.
    Falls back to #7C5CFF (brand electric violet) if no chromatic pixels are found.
    """
    try:
        small = img.convert("RGBA").resize((32, 32), Image.Resampling.BILINEAR)
        pixels = list(small.get_flattened_data()) if hasattr(small, "get_flattened_data") else list(small.getdata())
        r_sum = g_sum = b_sum = w_sum = 0.0

        for r, g, b, a in pixels:
            if a < 100:
                continue
            rf, gf, bf = r / 255.0, g / 255.0, b / 255.0
            cmax = max(rf, gf, bf)
            cmin = min(rf, gf, bf)
            delta = cmax - cmin
            sat = (delta / cmax) if cmax > 0 else 0.0
            val = cmax

            # Ignore near-black, near-white, and desaturated grey pixels
            if val < 0.18 or sat < 0.18:
                continue
            weight = (sat ** 1.4) * (val ** 0.8) * (a / 255.0)
            r_sum += r * weight
            g_sum += g * weight
            b_sum += b * weight
            w_sum += weight

        if w_sum <= 0.01:
            return "#7C5CFF"

        r_avg = int(min(255, max(0, round(r_sum / w_sum))))
        g_avg = int(min(255, max(0, round(g_sum / w_sum))))
        b_avg = int(min(255, max(0, round(b_sum / w_sum))))

        # Ensure minimum brightness so the glow is visible on dark surfaces
        peak = max(r_avg, g_avg, b_avg)
        if peak < 150 and peak > 0:
            boost = 165.0 / peak
            r_avg = min(255, int(r_avg * boost))
            g_avg = min(255, int(g_avg * boost))
            b_avg = min(255, int(b_avg * boost))

        return f"#{r_avg:02x}{g_avg:02x}{b_avg:02x}"
    except Exception:
        return "#7C5CFF"


def _draw_brand_url_icon(url: str, name: str, size: int = 256) -> Image.Image | None:
    """
    Renders crisp 256x256 vector-grade icons for popular web destinations (YouTube, Twitch,
    Spotify, GitHub, Netflix, Reddit, etc.), or fetches high-res site favicon if online.
    """
    try:
        parsed = urlparse(url if "://" in url else f"https://{url}")
        host = (parsed.hostname or "").lower().replace("www.", "")
    except Exception:
        host = ""

    # 1. Built-in high-precision vector render for YouTube (offline-ready & ultra-sharp)
    if "youtube.com" in host or "youtu.be" in host or name.lower() == "youtube":
        scale = 2
        S = size * scale
        im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        draw = ImageDraw.Draw(im)
        # Rounded squircle background in rich dark crimson/red gradient
        margin = int(S * 0.06)
        draw.rounded_rectangle(
            [margin, int(S * 0.18), S - margin, int(S * 0.82)],
            radius=int(S * 0.16),
            fill=(255, 0, 51, 255),
        )
        # White play triangle in center
        cx, cy = S // 2, S // 2
        tri = [
            (cx - int(S * 0.11), cy - int(S * 0.15)),
            (cx - int(S * 0.11), cy + int(S * 0.15)),
            (cx + int(S * 0.16), cy),
        ]
        draw.polygon(tri, fill=(255, 255, 255, 255))
        return im.resize((size, size), Image.Resampling.LANCZOS)

    # 2. Try fetching high-res favicon if online (short timeout so LAN never hangs)
    if host:
        favicon_urls = [
            f"https://www.google.com/s2/favicons?domain={host}&sz=256",
            f"https://icons.duckduckgo.com/ip3/{host}.ico",
        ]
        for fav_url in favicon_urls:
            try:
                req = urllib.request.Request(
                    fav_url,
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
                )
                with urllib.request.urlopen(req, timeout=2.0) as resp:
                    raw = resp.read()
                fav_img = Image.open(io.BytesIO(raw)).convert("RGBA")
                if fav_img.width >= 32 and fav_img.height >= 32:
                    return _normalize_icon_canvas(fav_img, size)
            except Exception:
                continue

    return None


def generate_fallback_icon(name: str, size: int = 256) -> Image.Image:
    """
    Generates a sleek, modern 256x256 squircle icon with a deterministic gradient
    and crisp geometric monogram initials when no native icon is available.
    """
    palettes = [
        ((124, 92, 255), (74, 46, 209)),   # Electric Violet
        ((56, 189, 248), (29, 78, 216)),    # Sky -> Royal Blue
        ((16, 185, 129), (5, 122, 85)),     # Emerald
        ((244, 63, 94), (190, 18, 60)),     # Rose
        ((245, 158, 11), (217, 119, 6)),    # Amber
        ((168, 85, 247), (107, 33, 168)),   # Purple
        ((20, 184, 166), (15, 118, 110)),   # Teal
    ]
    digest = int(hashlib.sha256((name or "App").encode("utf-8")).hexdigest()[:8], 16)
    top_rgb, bot_rgb = palettes[digest % len(palettes)]

    scale = 2
    S = size * scale
    base = Image.new("RGBA", (S, S), (0, 0, 0, 0))

    # Build vertical gradient image
    grad = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    grad_draw = ImageDraw.Draw(grad)
    for y in range(S):
        t = y / float(S - 1)
        r = int(top_rgb[0] * (1 - t) + bot_rgb[0] * t)
        g = int(top_rgb[1] * (1 - t) + bot_rgb[1] * t)
        b = int(top_rgb[2] * (1 - t) + bot_rgb[2] * t)
        grad_draw.line([(0, y), (S, y)], fill=(r, g, b, 255))

    # Rounded squircle mask
    mask = Image.new("L", (S, S), 0)
    mask_draw = ImageDraw.Draw(mask)
    pad = int(S * 0.06)
    radius = int(S * 0.22)
    mask_draw.rounded_rectangle([pad, pad, S - pad, S - pad], radius=radius, fill=255)
    base.paste(grad, (0, 0), mask)

    # Subtle inner border highlight
    draw = ImageDraw.Draw(base)
    draw.rounded_rectangle(
        [pad, pad, S - pad, S - pad],
        radius=radius,
        outline=(255, 255, 255, 55),
        width=4,
    )

    # Initials (1-2 chars)
    words = [w for w in (name or "A").replace("-", " ").replace("_", " ").split() if w]
    if len(words) >= 2:
        initials = (words[0][0] + words[1][0]).upper()
    elif words:
        initials = words[0][:2].capitalize()
    else:
        initials = "A"

    font_size = int(S * 0.40)
    try:
        font = ImageFont.truetype("C:\\Windows\\Fonts\\segoeuib.ttf", font_size)
    except Exception:
        try:
            font = ImageFont.truetype("arialbd.ttf", font_size)
        except Exception:
            font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), initials, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    tx = (S - tw) // 2 - bbox[0]
    ty = (S - th) // 2 - bbox[1]
    draw.text((tx, ty + 4), initials, font=font, fill=(0, 0, 0, 75))
    draw.text((tx, ty), initials, font=font, fill=(255, 255, 255, 245))

    return base.resize((size, size), Image.Resampling.LANCZOS)


def _resolve_app_target_for_icon(target: str, args: list | None = None) -> str | None:
    """
    Resolves an executable/shortcut/Squirrel path to the best file for icon extraction.
    """
    expanded = os.path.expandvars(target).strip('"')

    # Handle Squirrel Update.exe wrapper (e.g., Discord, Slack, Postman)
    if expanded.lower().endswith("update.exe"):
        parent_dir = os.path.dirname(expanded)
        app_ico = os.path.join(parent_dir, "app.ico")
        if os.path.exists(app_ico):
            return app_ico
        exe_name = None
        if args:
            for i, arg in enumerate(args):
                if arg.lower() == "--processstart" and i + 1 < len(args):
                    exe_name = args[i + 1]
                    break
        if exe_name:
            candidates = sorted(glob.glob(os.path.join(parent_dir, "app-*", exe_name)), reverse=True)
            if candidates:
                return candidates[0]

    if os.path.exists(expanded):
        return os.path.abspath(expanded)

    # Bare command name like "notepad.exe" -> resolve via PATH
    which_path = shutil.which(expanded)
    if which_path and os.path.exists(which_path):
        return os.path.abspath(which_path)

    return None


def _load_ico_or_image_file(path: str, size: int = 256) -> Image.Image | None:
    """Loads an .ico or image file directly at highest available resolution."""
    try:
        im = Image.open(path)
        if path.lower().endswith(".ico") and hasattr(im, "ico"):
            # Select largest size frame in .ico
            sizes = im.ico.sizes()
            if sizes:
                best = max(sizes, key=lambda s: s[0] * s[1])
                im = im.ico.getimage(best)
        return _normalize_icon_canvas(im.convert("RGBA"), size)
    except Exception:
        return None


def get_preset_icon(preset) -> tuple[str, str]:
    """
    Returns (png_file_path, accent_hex) for a PresetConfig.
    Uses disk cache in data/icons/cache/ unless custom icon or target changed.
    """
    signature = f"preset:{preset.id}:{preset.type}:{preset.target}:{preset.args}:{preset.icon}"
    cache_key = f"preset_{preset.id}_{hashlib.sha1(signature.encode('utf-8')).hexdigest()[:10]}"
    png_path = os.path.join(CACHE_DIR, f"{cache_key}.png")
    meta = _load_meta()

    if os.path.exists(png_path) and cache_key in meta:
        return png_path, meta[cache_key].get("accent", "#7C5CFF")

    img: Image.Image | None = None

    # 1. Custom icon override if specified
    if getattr(preset, "icon", None):
        custom_candidate = preset.icon
        if not os.path.isabs(custom_candidate):
            custom_candidate = os.path.join(CUSTOM_DIR, custom_candidate)
        if os.path.exists(custom_candidate):
            img = _load_ico_or_image_file(custom_candidate, 256)

    # 2. Extract based on preset type
    if img is None:
        if preset.type == "shell_app":
            img = _extract_shell_icon(f"shell:AppsFolder\\{preset.target}", 256)
        elif preset.type == "url":
            img = _draw_brand_url_icon(preset.target, preset.name, 256)
        elif preset.type in ("app", "folder", "steam"):
            resolved = _resolve_app_target_for_icon(preset.target, preset.args)
            if resolved:
                if resolved.lower().endswith((".ico", ".png", ".jpg", ".jpeg", ".webp")):
                    img = _load_ico_or_image_file(resolved, 256)
                if img is None:
                    img = _extract_shell_icon(resolved, 256)

    # 3. Fallback if extraction failed
    if img is None:
        img = generate_fallback_icon(preset.name, 256)

    accent = getattr(preset, "accent", None) or extract_dominant_accent(img)
    try:
        img.save(png_path, "PNG")
        _save_meta_entry(cache_key, {"accent": accent, "name": preset.name})
    except Exception as e:
        print(f"Error saving cached preset icon {png_path}: {e}")

    return png_path, accent


def get_installed_app_icon(app_id: str, name: str = "App") -> tuple[str, str]:
    """
    Returns (png_file_path, accent_hex) for an installed Start Menu app (shell:AppsFolder\\<AppID>).
    """
    key_hash = hashlib.sha1(app_id.encode("utf-8")).hexdigest()[:12]
    cache_key = f"installed_{key_hash}"
    png_path = os.path.join(CACHE_DIR, f"{cache_key}.png")
    meta = _load_meta()

    if os.path.exists(png_path) and cache_key in meta:
        return png_path, meta[cache_key].get("accent", "#7C5CFF")

    img = _extract_shell_icon(f"shell:AppsFolder\\{app_id}", 256)
    if img is None:
        img = generate_fallback_icon(name, 256)

    accent = extract_dominant_accent(img)
    try:
        img.save(png_path, "PNG")
        _save_meta_entry(cache_key, {"accent": accent, "name": name})
    except Exception:
        pass

    return png_path, accent


def get_process_icon(proc_name: str) -> tuple[str, str]:
    """
    Returns (png_file_path, accent_hex) for an audio session process name (e.g. 'Spotify', 'chrome').
    """
    clean_name = proc_name.replace(".exe", "").strip()
    key_hash = hashlib.sha1(clean_name.lower().encode("utf-8")).hexdigest()[:12]
    cache_key = f"proc_{key_hash}"
    png_path = os.path.join(CACHE_DIR, f"{cache_key}.png")
    meta = _load_meta()

    if os.path.exists(png_path) and cache_key in meta:
        return png_path, meta[cache_key].get("accent", "#7C5CFF")

    exe_path = _process_exe_map.get(clean_name.lower())
    if not exe_path:
        # Scan running processes via psutil
        import psutil
        target_exe = clean_name.lower() + ".exe"
        for proc in psutil.process_iter(["name", "exe"]):
            try:
                pname = (proc.info.get("name") or "").lower()
                if pname == target_exe or pname == clean_name.lower():
                    pexe = proc.info.get("exe")
                    if pexe and os.path.exists(pexe):
                        exe_path = pexe
                        _process_exe_map[clean_name.lower()] = pexe
                        break
            except Exception:
                continue

    if not exe_path:
        exe_path = shutil.which(clean_name + ".exe") or shutil.which(clean_name)

    img = None
    if exe_path and os.path.exists(exe_path):
        # Check if there is an app.ico in parent (e.g. Squirrel apps)
        parent_ico = os.path.join(os.path.dirname(os.path.dirname(exe_path)), "app.ico")
        if os.path.exists(parent_ico):
            img = _load_ico_or_image_file(parent_ico, 256)
        if img is None:
            img = _extract_shell_icon(exe_path, 256)

    if img is None:
        img = generate_fallback_icon(clean_name, 256)

    accent = extract_dominant_accent(img)
    try:
        img.save(png_path, "PNG")
        _save_meta_entry(cache_key, {"accent": accent, "name": clean_name})
    except Exception:
        pass

    return png_path, accent


def save_custom_icon(preset_id: str, file_bytes: bytes) -> str:
    """
    Validates, crops/resizes to 256x256 PNG, and saves a user-uploaded custom icon.
    Returns the filename stored in data/icons/custom/.
    """
    im = Image.open(io.BytesIO(file_bytes)).convert("RGBA")
    # Center square crop if non-square
    w, h = im.size
    if w != h:
        side = min(w, h)
        left = (w - side) // 2
        top = (h - side) // 2
        im = im.crop((left, top, left + side, top + side))
    im = im.resize((256, 256), Image.Resampling.LANCZOS)

    token = hashlib.sha1(file_bytes[:4096]).hexdigest()[:8]
    filename = f"custom_{preset_id}_{token}.png"
    out_path = os.path.join(CUSTOM_DIR, filename)
    im.save(out_path, "PNG")
    return filename
