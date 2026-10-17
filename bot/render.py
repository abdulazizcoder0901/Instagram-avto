"""Claude yozgan HTML slaydlarni Chromium'da 1080x1350 JPEG'ga aylantiradi."""
import html
import os
import re
from pathlib import Path

from playwright.sync_api import sync_playwright

from bot import photos

DESIGN = Path(__file__).parent / "design"
HANDLE = "@mr_abdulazz"
FONTS = ("https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800"
         "&family=Montserrat:wght@700;800;900&display=block")
BACKGROUNDS = ("orange", "blue", "yellow", "cream", "dark")

# Matn shu chegaradan pastga tushmasin (oxirgisidan boshqa slaydlarda pastda "Keyingisi" tugmasi turadi)
CHECK_JS = """(limit) => {
  const out = [];
  for (const img of document.images) {
    if (!img.complete || img.naturalWidth === 0) { out.push('rasm ochilmadi: ' + img.getAttribute('src')); img.style.display = 'none'; }
  }
  const skip = '.photo-bg,.photo-bg-tint,.watermark,.chrome-top,.next,.abs';
  for (const el of document.querySelectorAll('.slide *')) {
    if (el.closest(skip) || !el.textContent.trim() || el.children.length) continue;
    const r = el.getBoundingClientRect();
    if (r.width && (r.bottom > limit || r.right > 1082 || r.left < -2))
      out.push('matn sig\\'madi: «' + el.textContent.trim().slice(0, 40) + '»');
  }
  return out;
}"""


def _page(slide, index, total):
    bg = slide["bg"] if slide["bg"] in BACKGROUNDS else "orange"
    nxt = '<div class="next">Keyingisi</div>' if index < total else ""
    return f"""<!doctype html><html><head><meta charset="utf-8">
<link rel="stylesheet" href="{FONTS}">
<style>{(DESIGN / 'base.css').read_text()}</style></head><body>
<div class="slide bg-{bg}">
  <div class="chrome-top"><span class="handle">{HANDLE}</span><span class="count">{index:02d} / {total:02d}</span></div>
  {slide['html']}
  {nxt}
</div></body></html>"""


def _resolve_photos(markup, assets_dir, credits):
    """<img data-q="so'rov"> teglariga bepul foto topib qo'yadi; topilmasa tegni olib tashlaydi."""
    def repl(m):
        tag = m.group(0)
        query = html.unescape(m.group(1))
        path, credit = photos.find(query, assets_dir)
        if not path:
            return ""
        if credit:
            credits.append(credit)
        tag = re.sub(r'\ssrc="[^"]*"', "", tag)
        return tag.replace("<img", f'<img src="{path.name}"', 1)
    return re.sub(r'<img\b[^>]*\bdata-q="([^"]+)"[^>]*>', repl, markup)


def render_post(slides, out_dir, assets_dir):
    """(slayd_rasmlari, foto_mualliflari, muammolar) qaytaradi. muammolar: {slayd_raqami: [..]}"""
    out_dir, assets_dir = Path(out_dir), Path(assets_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    assets_dir.mkdir(parents=True, exist_ok=True)
    credits, problems, outputs = [], {}, []
    total = len(slides)
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=os.environ.get("CHROMIUM_PATH") or None)
        page = browser.new_page(viewport={"width": 1080, "height": 1350})
        for i, slide in enumerate(slides, start=1):
            slide = {**slide, "html": _resolve_photos(slide["html"], assets_dir, credits)}
            src = assets_dir / f"_slide-{i:02d}.html"
            src.write_text(_page(slide, i, total), encoding="utf-8")
            page.goto(src.as_uri(), wait_until="networkidle")
            page.evaluate("document.fonts.ready")
            issues = page.evaluate(CHECK_JS, 1195 if i < total else 1300)
            if issues:
                problems[i] = issues
            out = out_dir / f"{i:02d}.jpg"
            page.screenshot(path=str(out), type="jpeg", quality=92)
            outputs.append(out)
        browser.close()
    return outputs, list(dict.fromkeys(credits)), problems
