"""Generador de Tarjetas de Reddit / Redes Sociales para Hooks Visuales en Video.

Crea tarjetas con estética 100% idéntica a Reddit (avatar Snoo, subreddit, usuario,
upvotes, comentarios y texto del gancho) en PNG transparente para superponer en
los primeros 3-4 segundos del video vertical sobre el gameplay.
"""

import os
import random
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

SUBREDDITS = {
    "reddit": ["r/Historias", "r/Confesiones", "r/Venganzas", "r/PreguntasReddit", "r/HistoriasDeVida"],
    "mystery": ["r/Paranormal", "r/Terror", "r/Creepypastas", "r/MisteriosSinResolver", "r/ArchivosSecretos"],
    "bizarre": ["r/GenteLoca", "r/CosasTurbias", "r/KarmaInstantaneo", "r/Sinverguenzas", "r/HistoriasBizarras"],
}

USERNAMES = [
    "u/anonimo_nocturno",
    "u/ex_empleado_hotel",
    "u/testigo_silencioso",
    "u/ojo_critico99",
    "u/vecino_observador",
    "u/abogado_confuso",
    "u/camionero_del_sur",
    "u/guardia_turno_noche",
    "u/cajero_nocturno",
    "u/inquilino_furioso",
]


def _generate_upvotes_and_comments() -> tuple[str, str]:
    """Genera cifras realistas de upvotes y comentarios de alto impacto."""
    up_k = random.uniform(8.5, 38.0)
    upvotes = f"{up_k:.1f}k"
    com_num = random.randint(450, 2400)
    comments = f"{com_num/1000:.1f}k" if com_num >= 1000 else str(com_num)
    return upvotes, comments


def generate_reddit_card(
    hook_text: str,
    output_path: str,
    category: str = "reddit",
    theme: str = "light",  # "light" o "dark"
) -> str:
    """Genera un archivo PNG transparente de la tarjeta de Reddit usando Playwright.

    Args:
        hook_text: Texto del gancho (título o primeras líneas impactantes).
        output_path: Ruta de destino del PNG.
        category: 'reddit', 'mystery' o 'bizarre'.
        theme: 'light' o 'dark'.

    Returns:
        Ruta del PNG generado.
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    # Limpiar y limitar longitud del texto del gancho para que entre perfecto en la tarjeta
    clean_text = hook_text.strip().replace('"', '&quot;').replace("'", "&#39;")
    if len(clean_text) > 230:
        clean_text = clean_text[:225].rsplit(" ", 1)[0] + "..."

    sub_list = SUBREDDITS.get(category, SUBREDDITS["reddit"])
    subreddit = random.choice(sub_list)
    username = random.choice(USERNAMES)
    hours_ago = random.randint(2, 9)
    upvotes, comments = _generate_upvotes_and_comments()

    # Colores según tema
    is_dark = (theme == "dark")
    bg_color = "#1A1A1B" if is_dark else "#FFFFFF"
    text_color = "#D7DADC" if is_dark else "#1C1C1C"
    meta_color = "#818384" if is_dark else "#787C7E"
    pill_bg = "#272729" if is_dark else "#F6F7F8"
    pill_text = "#D7DADC" if is_dark else "#576F76"
    border_color = "#343536" if is_dark else "rgba(0,0,0,0.08)"

    # Icono Snoo estilizado en SVG
    snoo_svg = """
    <svg viewBox="0 0 100 100" width="46" height="46">
        <circle cx="50" cy="50" r="48" fill="#FF4500"/>
        <circle cx="50" cy="52" r="32" fill="#FFFFFF"/>
        <ellipse cx="40" cy="48" rx="4.5" ry="5.5" fill="#FF4500"/>
        <ellipse cx="60" cy="48" rx="4.5" ry="5.5" fill="#FF4500"/>
        <path d="M 40 60 Q 50 68 60 60" stroke="#FF4500" stroke-width="3.5" fill="none" stroke-linecap="round"/>
        <circle cx="21" cy="48" r="6.5" fill="#FFFFFF"/>
        <circle cx="79" cy="48" r="6.5" fill="#FFFFFF"/>
        <path d="M 50 20 L 58 10 L 68 14" stroke="#FFFFFF" stroke-width="3" fill="none" stroke-linecap="round"/>
        <circle cx="70" cy="14" r="5" fill="#FFFFFF"/>
    </svg>
    """

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <style>
        body {{
          margin: 0;
          padding: 30px;
          background: transparent;
          font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        }}
        .card {{
          background: {bg_color};
          border: 1px solid {border_color};
          border-radius: 26px;
          padding: 28px 34px;
          width: 880px;
          box-shadow: 0 18px 45px rgba(0, 0, 0, 0.45);
          box-sizing: border-box;
        }}
        .header {{
          display: flex;
          align-items: center;
          gap: 15px;
          margin-bottom: 18px;
        }}
        .meta {{
          display: flex;
          flex-direction: column;
        }}
        .sub {{
          font-weight: 800;
          font-size: 24px;
          color: {text_color};
          letter-spacing: -0.3px;
        }}
        .user {{
          font-size: 17px;
          color: {meta_color};
          margin-top: 2px;
        }}
        .title {{
          font-size: 34px;
          font-weight: 700;
          line-height: 1.35;
          color: {text_color};
          margin-bottom: 24px;
          letter-spacing: -0.4px;
        }}
        .footer {{
          display: flex;
          gap: 14px;
          align-items: center;
        }}
        .pill {{
          background: {pill_bg};
          border-radius: 999px;
          padding: 10px 18px;
          font-size: 19px;
          font-weight: 700;
          color: {pill_text};
          display: flex;
          align-items: center;
          gap: 9px;
        }}
        .upvote {{
          color: #FF4500;
        }}
      </style>
    </head>
    <body>
      <div class="card" id="reddit-card">
        <div class="header">
          {snoo_svg}
          <div class="meta">
            <span class="sub">{subreddit}</span>
            <span class="user">Publicado por {username} • hace {hours_ago} h</span>
          </div>
        </div>
        <div class="title">
          {clean_text}
        </div>
        <div class="footer">
          <div class="pill upvote">▲ {upvotes} ▼</div>
          <div class="pill">💬 {comments} comentarios</div>
          <div class="pill">↗ Compartir</div>
        </div>
      </div>
    </body>
    </html>
    """

    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1080, "height": 1000})
            page.set_content(html)
            card = page.locator("#reddit-card")
            card.screenshot(path=output_path, omit_background=True)
            browser.close()
        logger.info("✓ Tarjeta de Reddit generada con Playwright: %s", output_path)
        return output_path
    except Exception as exc:
        logger.warning("Fallo al generar tarjeta con Playwright (%s). Usando fallback de Pillow...", exc)
        return _generate_card_pillow(clean_text, output_path, subreddit, username, upvotes, comments, is_dark)


def _generate_card_pillow(
    text: str,
    output_path: str,
    subreddit: str,
    username: str,
    upvotes: str,
    comments: str,
    is_dark: bool = False,
) -> str:
    """Generador alternativo con Pillow en caso de que Playwright no esté disponible."""
    from PIL import Image, ImageDraw, ImageFont

    card_w, card_h = 880, 420
    img = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    bg_color = (26, 26, 27, 255) if is_dark else (255, 255, 255, 255)
    text_color = (215, 218, 220, 255) if is_dark else (28, 28, 28, 255)
    meta_color = (129, 131, 132, 255) if is_dark else (120, 124, 126, 255)

    # Tarjeta redondeada
    draw.rounded_rectangle([0, 0, card_w, card_h], radius=24, fill=bg_color)

    # Snoo círculo
    draw.ellipse([34, 30, 84, 80], fill=(255, 69, 0, 255))
    draw.ellipse([46, 42, 72, 68], fill=(255, 255, 255, 255))

    # Textos
    try:
        font_sub = ImageFont.truetype("arialbd.ttf", 22)
        font_user = ImageFont.truetype("arial.ttf", 16)
        font_body = ImageFont.truetype("arialbd.ttf", 28)
        font_pill = ImageFont.truetype("arialbd.ttf", 18)
    except Exception:
        font_sub = font_user = font_body = font_pill = ImageFont.load_default()

    draw.text((98, 34), subreddit, font=font_sub, fill=text_color)
    draw.text((98, 62), f"Publicado por {username}", font=font_user, fill=meta_color)

    # Wrap simple de texto
    words = text.split()
    lines = []
    cur_line = []
    for w in words:
        cur_line.append(w)
        if len(" ".join(cur_line)) > 42:
            lines.append(" ".join(cur_line))
            cur_line = []
    if cur_line:
        lines.append(" ".join(cur_line))

    y = 110
    for l in lines[:4]:
        draw.text((36, y), l, font=font_body, fill=text_color)
        y += 42

    # Pills inferiores
    pill_y = card_h - 65
    draw.rounded_rectangle([36, pill_y, 180, pill_y + 40], radius=20, fill=(240, 242, 243, 255))
    draw.text((54, pill_y + 8), f"▲ {upvotes} ▼", font=font_pill, fill=(255, 69, 0, 255))

    draw.rounded_rectangle([195, pill_y, 410, pill_y + 40], radius=20, fill=(240, 242, 243, 255))
    draw.text((215, pill_y + 8), f"💬 {comments}", font=font_pill, fill=(87, 111, 118, 255))

    img.save(output_path, "PNG")
    logger.info("✓ Tarjeta de Reddit generada con Pillow: %s", output_path)
    return output_path
