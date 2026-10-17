"""Claude yozgan slaydlarni Chromium'da 1080x1350 JPEG'ga aylantiradi."""
import os
from pathlib import Path

from playwright.sync_api import sync_playwright

from bot import photos

DESIGN = Path(__file__).parent / "design"
HANDLE = "@mr_abdulazz"
FONTS = "https://fonts.googleapis.com/css2?family=Inter:ital,wght@0,400..800;1,500..800&display=block"
POSITIONS = ("bottom", "center", "top")

# Matn shu chegaradan pastga tushmasin (pastda handle, nuqtalar va "→" tugmasi turadi)
CHECK_JS = """(limit) => {
  const out = [];
  for (const img of document.images) {
    if (!img.complete || img.naturalWidth === 0) { out.push('rasm ochilmadi: ' + img.getAttribute('src')); img.style.display = 'none'; }
  }
  const skip = '.bg-photo,.shade,.handle,.dots,.arrow';
  for (const el of document.querySelectorAll('.slide *')) {
    if (el.closest(skip) || !el.textContent.trim() || el.children.length) continue;
    const r = el.getBoundingClientRect();
    if (r.width && (r.bottom > limit || r.top < 120 || r.right > 1082 || r.left < -2))
      out.push('matn sig\\'madi: «' + el.textContent.trim().slice(0, 40) + '»');
  }
  return out;
}"""


def _photo(slide, assets_dir, credits, used):
    """Fon rasmi: egasining rasmi (ref-..), keyin haqiqiy rasm qidiruvi, keyin bepul fotobaza."""
    ref = slide.get("photo_ref", "")
    if ref and (assets_dir / ref).is_file():
        return ref
    query = slide.get("photo_search", "").strip()
    if not query:
        return None
    path = photos.search_real(query, assets_dir, used)
    if path:
        return path.name
    path, credit = photos.find(query, assets_dir)
    if path:
        if credit:
            credits.append(credit)
        return path.name
    return None


def _page(slide, photo, index, total):
    pos = slide.get("position") if slide.get("position") in POSITIONS else "bottom"
    bg = f'<img class="bg-photo" src="{photo}"><div class="shade"></div>' if photo else '<div class="shade"></div>'
    dots = "".join('<i class="on"></i>' if n == index else "<i></i>" for n in range(1, total + 1))
    arrow = '<div class="arrow">→</div>' if index < total else ""
    return f"""<!doctype html><html><head><meta charset="utf-8">
<link rel="stylesheet" href="{FONTS}">
<style>{(DESIGN / 'base.css').read_text()}</style></head><body>
<div class="slide pos-{pos}">
  {bg}
  {slide['html']}
  {arrow}
  <div class="handle">{HANDLE}</div>
  <div class="dots">{dots}</div>
</div></body></html>"""


def render_post(slides, out_dir, assets_dir):
    """(slayd_rasmlari, foto_mualliflari, muammolar) qaytaradi. muammolar: {slayd_raqami: [..]}"""
    out_dir, assets_dir = Path(out_dir), Path(assets_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    assets_dir.mkdir(parents=True, exist_ok=True)
    credits, problems, outputs, used = [], {}, [], set()
    total = len(slides)
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=os.environ.get("CHROMIUM_PATH") or None)
        page = browser.new_page(viewport={"width": 1080, "height": 1350})
        for i, slide in enumerate(slides, start=1):
            photo = _photo(slide, assets_dir, credits, used)
            src = assets_dir / f"_slide-{i:02d}.html"
            src.write_text(_page(slide, photo, i, total), encoding="utf-8")
            page.goto(src.as_uri(), wait_until="networkidle")
            page.evaluate("document.fonts.ready")
            issues = page.evaluate(CHECK_JS, 1105)
            if not photo:
                issues.append("fon rasmi topilmadi — photo_search'ni boshqacha, aniqroq yoz")
            if issues:
                problems[i] = issues
            out = out_dir / f"{i:02d}.jpg"
            page.screenshot(path=str(out), type="jpeg", quality=92)
            outputs.append(out)
        browser.close()
    return outputs, list(dict.fromkeys(credits)), problems
