#!/usr/bin/env python3
"""
Genera la web de BryceLz en docs/ a partir de content/ y static/.

    python3 build.py

GitHub Pages publica lo generado en docs/ (rama main). Solo hace falta
Python 3, sin instalar nada.

Idiomas: el español va en la raíz (/, /aviso-legal/, /apps/allthegames/...)
y los demás bajo su código (/en/, /pt/, /it/, /fr/, /de/). La nota de
privacidad mantiene sus direcciones de siempre (/apps/allthegames/privacidad/<idioma>/),
que son las que figuran en la tienda; los términos de compra siguen el mismo
esquema (/apps/allthegames/terminos/<idioma>/).

Norma: la web no muestra el número de juegos (cambia cada vez que se añade uno)
ni los juegos que la app tiene ocultos ("hidden": true en games.json).
"""
import hashlib
import html
import json
from typing import Callable
import math
import re
import shutil
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONTENT = ROOT / 'content'
STATIC = ROOT / 'static'
# `python3 build.py --local` hace la copia local (docs-local/, sin publicar) con las apps en desarrollo.
LOCAL = '--local' in sys.argv
OUT = ROOT / ('docs-local' if LOCAL else 'docs')

SITE = json.loads((CONTENT / 'site.json').read_text('utf-8'))
UI = json.loads((CONTENT / 'ui.json').read_text('utf-8'))
# Apps en desarrollo: solo en la copia local.
PLANNED = json.loads((CONTENT / 'planned-apps.json').read_text('utf-8'))['apps'] if LOCAL else []
BRAND = SITE['brand']
OWNER = SITE['owner']
EMAIL = SITE['email']
YEAR = SITE['year']
# Huella de la hoja de estilos: cambia la dirección en cada versión para que nadie se quede con la vieja en caché.
CSS_VER = hashlib.sha1((STATIC / 'site.css').read_bytes()).hexdigest()[:8]

# Orden del selector de idioma (el mismo que la app).
LANGS = ['es', 'en', 'pt', 'it', 'fr', 'de']
LANG_NAMES = {l: UI[l]['langName'] for l in LANGS}
HTML_LANG = {'es': 'es', 'en': 'en', 'pt': 'pt-BR', 'it': 'it', 'fr': 'fr', 'de': 'de'}
# Texto de la web alrededor de la nota de privacidad, en cada idioma.
PRIVACY_CHROME = {
    l: {'terms': UI[l]['termsLong'], 'langs': UI[l]['langMenu']} for l in LANGS
}

THEME_COLOR = {'studio': '#6E1F2A', 'atg': '#935127', 'party': '#2A0F1A'}

# Enlaces dentro de los textos legales (solo nombres exactos).
AUTO_LINKS = {
    'rae-api.com': 'https://rae-api.com',
    'flagcdn.com': 'https://flagcdn.com',
    'aepd.es': 'https://www.aepd.es',
    'reportaproblem.apple.com': 'https://reportaproblem.apple.com',
}

# ---------------------------------------------------------------------------
# Colores (las mismas recetas que la app).

BAND_INK = '#2B2118'


def mix(a: str, b: str, t: float) -> str:
    pa, pb = int(a[1:], 16), int(b[1:], 16)
    ch = lambda n, s: (n >> s) & 255
    return '#' + ''.join(
        f'{round(ch(pa, s) + (ch(pb, s) - ch(pa, s)) * t):02X}' for s in (16, 8, 0)
    )


def band_fill(accent: str) -> str:
    return mix(accent, BAND_INK, 0.34)


def band_lip(accent: str) -> str:
    return mix(accent, BAND_INK, 0.58)


def _lin(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _srgb(c: float) -> float:
    return 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055


def _hue(hexc: str) -> float:
    n = int(hexc[1:], 16)
    r, g, b = (_lin(((n >> s) & 255) / 255) for s in (16, 8, 0))
    l = (0.4122214708 * r + 0.5363015264 * g + 0.0514459929 * b) ** (1 / 3)
    m = (0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b) ** (1 / 3)
    s = (0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b) ** (1 / 3)
    a = 1.9779984951 * l - 2.428592205 * m + 0.4505937099 * s
    bb = 0.0259040371 * l + 0.7827717662 * m - 0.808675766 * s
    h = math.degrees(math.atan2(bb, a))
    return h + 360 if h < 0 else h


def _oklch(L: float, C: float, h: float) -> str:
    rad = math.radians(h)

    def to_lin(c: float):
        a, b = c * math.cos(rad), c * math.sin(rad)
        l_ = L + 0.3963377774 * a + 0.2158037573 * b
        m_ = L - 0.1055613458 * a - 0.0638541728 * b
        s_ = L - 0.0894841775 * a - 1.291485548 * b
        l, m, s = l_ ** 3, m_ ** 3, s_ ** 3
        return [
            4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
            -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
            -0.0041960863 * l - 0.7034186147 * m + 1.707614701 * s,
        ]

    c = C
    rgb = to_lin(c)
    for _ in range(24):
        if all(-0.0005 <= x <= 1.0005 for x in rgb):
            break
        c *= 0.9
        rgb = to_lin(c)
    return '#' + ''.join(
        f'{round(min(1, max(0, _srgb(min(1, max(0, x))))) * 255):02X}' for x in rgb
    )


def pastel(accent: str, amount: float = 0.12) -> str:
    """Igual que tintFace() de la app (tema claro)."""
    return _oklch(0.975 - amount * 0.38, amount * 0.3, _hue(accent))


# ---------------------------------------------------------------------------
# Utilidades


def esc(text: str) -> str:
    return html.escape(text, quote=True)


def mail_link(email: str = EMAIL) -> str:
    return f'<a href="mailto:{esc(email)}">{esc(email)}</a>'


def rich(text: str, extra: dict | None = None) -> str:
    """Escapa el texto y añade los enlaces conocidos y los marcadores {x}."""
    out = esc(text)
    for word, url in AUTO_LINKS.items():
        out = re.sub(
            rf'(?<![\w./]){re.escape(word)}(?![\w])',
            f'<a href="{url}">{word}</a>',
            out,
            count=1,
        )
    marks = {'email': mail_link()}
    if extra:
        marks.update(extra)
    for key, value in marks.items():
        out = out.replace('{' + key + '}', value)
    return out


def slug(text: str) -> str:
    t = unicodedata.normalize('NFKD', text.lower())
    t = ''.join(ch for ch in t if not unicodedata.combining(ch))
    return re.sub(r'[^a-z0-9]+', '-', t).strip('-')


def T(lang: str, key: str, **kw) -> str:
    """Un texto de la web en un idioma, con sus marcadores {x} sustituidos (sin escapar)."""
    text = UI[lang][key]
    for k, v in kw.items():
        text = text.replace('{' + k + '}', str(v))
    return text


def lp(lang: str, path: str) -> str:
    """La dirección de una página en un idioma: el español en la raíz, el resto bajo su código."""
    return path if lang == 'es' else f'{lang}/{path}'


class Ctx:
    """Dónde está la página: para escribir enlaces relativos (o absolutos en 404)."""

    def __init__(self, here: str, absolute: bool = False):
        self.here = here
        self.absolute = absolute

    def to(self, target: str) -> str:
        if self.absolute:
            return '/' + target
        a = [p for p in self.here.strip('/').split('/') if p]
        b = [p for p in target.strip('/').split('/') if p]
        i = 0
        while i < min(len(a), len(b)) and a[i] == b[i]:
            i += 1
        path = '/'.join(['..'] * (len(a) - i) + b[i:])
        if target.endswith('/') and path:
            path += '/'
        return path or './'


# ---------------------------------------------------------------------------
# Piezas comunes


def nav_items(lang: str) -> list[tuple[str, str]]:
    """Los apartados del banner. De momento: Inicio y AllTheGames."""
    return [(lp(lang, ''), T(lang, 'home')), (lp(lang, 'apps/allthegames/'), 'AllTheGames'),
            (lp(lang, PARTY), 'AllThePartyGames')] + [(lp(lang, f"apps/{a['id']}/"), a['name']) for a in PLANNED]


def wordmark(c: Ctx, lang: str) -> str:
    return (
        f'<a class="wordmark" href="{c.to(lp(lang, ""))}" aria-label="{esc(T(lang, "homeAria"))}">'
        f'<img class="wordmark-img" src="{c.to("static/brand/logo.webp")}" alt="{BRAND}" width="640" height="188"></a>'
    )


GLOBE = (
    '<svg viewBox="0 0 20 20" width="18" height="18" aria-hidden="true" fill="none" stroke="currentColor" '
    'stroke-width="1.8"><circle cx="10" cy="10" r="7.5"/><path d="M2.5 10h15M10 2.5c2.2 2.3 3.2 4.8 3.2 7.5S12.2 15.2 10 17.5'
    'M10 2.5C7.8 4.8 6.8 7.3 6.8 10s1 5.2 3.2 7.5"/></svg>'
)


def lang_menu(c: Ctx, lang: str, links: dict) -> str:
    """Selector de idioma: cada idioma lleva a la misma página en ese idioma."""
    items = []
    for l in LANGS:
        cur = ' aria-current="true"' if l == lang else ''
        items.append(
            f'<li><a href="{c.to(links[l])}" hreflang="{HTML_LANG[l]}" lang="{HTML_LANG[l]}"{cur}>{LANG_NAMES[l]}</a></li>'
        )
    return f'''<details class="lang-menu">
      <summary aria-label="{esc(T(lang, 'langMenu'))}: {LANG_NAMES[lang]}">{GLOBE}<span>{lang.upper()}</span></summary>
      <ul>{''.join(items)}</ul>
    </details>'''


def site_header(c: Ctx, section: str | None, lang: str, links: dict) -> str:
    """El banner de arriba, como los de la app: banda honda con labio y botones dentro."""
    tabs = ''.join(_nav_link(c, path, label, section) for path, label in nav_items(lang))
    return f'''<header class="banner">
  <div class="wrap banner-row">
    {wordmark(c, lang)}
    <div class="banner-end">
      <nav class="banner-nav" aria-label="{esc(T(lang, 'navAria'))}">{tabs}</nav>
      {lang_menu(c, lang, links)}
    </div>
  </div>
</header>'''


def _nav_link(c: Ctx, path: str, label: str, section: str | None) -> str:
    current = ' aria-current="page"' if section == path else ''
    return f'<a class="banner-tab" href="{c.to(path)}"{current}>{label}</a>'


def site_footer(c: Ctx, lang: str) -> str:
    """El pie cierra la página como el banner la abre: banda honda, esquinas de arriba redondas."""
    return f'''<footer class="site-foot">
  <div class="wrap foot-row">
    {wordmark(c, lang)}
    <nav class="foot-links" aria-label="{esc(T(lang, 'footAria'))}">
      <a href="{c.to(lp(lang, 'aviso-legal/'))}">{esc(T(lang, 'legalNotice'))}</a>
      {mail_link()}
    </nav>
    <p class="foot-copy">© {YEAR} {esc(OWNER)} ({esc(T(lang, 'ownerNote'))})</p>
  </div>
</footer>'''


def same_page(path: str) -> dict:
    """La misma página en los 6 idiomas (para páginas que existen en todos)."""
    return {l: lp(l, path) for l in LANGS}


def page(
    path: str,
    *,
    title: str,
    description: str,
    main: str,
    theme: str,
    section: str | None,
    lang: str = 'es',
    links: dict | None = None,
    hreflang: bool = True,
    pre_main: str = '',
    absolute: bool = False,
    favicon: str | None = None,
) -> None:
    """Escribe una página. `links` dice dónde está esta misma página en cada idioma."""
    here = path if (path == '' or path.endswith('/')) else (path.rsplit('/', 1)[0] + '/' if '/' in path else '')
    c = Ctx(here, absolute)
    base = SITE['baseUrl'].rstrip('/')
    canonical = base + '/' + (path if path.endswith('/') or path == '' else path)
    links = links or {l: lp(l, '') for l in LANGS}
    alt = ''
    if hreflang and len(set(links.values())) == len(LANGS):
        alt = ''.join(
            f'\n  <link rel="alternate" hreflang="{HTML_LANG[l]}" href="{base}/{p}">' for l, p in links.items()
        ) + f'\n  <link rel="alternate" hreflang="x-default" href="{base}/{links["es"]}">'
    icon = favicon or 'static/brand/favicon-64.png'
    doc = f'''<!doctype html>
<html lang="{HTML_LANG[lang]}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(title)}</title>
  <meta name="description" content="{esc(description)}">
  <link rel="canonical" href="{canonical}">{alt}
  <meta property="og:title" content="{esc(title)}">
  <meta property="og:description" content="{esc(description)}">
  <meta property="og:type" content="website">
  <meta property="og:url" content="{canonical}">
  <meta property="og:image" content="{base}/static/brand/og.png">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="theme-color" content="{THEME_COLOR.get(theme, '#6E1F2A')}">
  <link rel="icon" href="{c.to(icon)}">
  <link rel="apple-touch-icon" href="{c.to('static/brand/apple-touch-icon.png')}">
  <link rel="stylesheet" href="{c.to('static/site.css')}?v={CSS_VER}">
</head>
<body class="theme-{theme}">
<a class="skip" href="#contenido">{esc(T(lang, 'skip'))}</a>
{site_header(c, section, lang, links)}
{pre_main}
<main id="contenido">
{main}
</main>
{site_footer(c, lang)}
<script>
  // El selector de idioma se cierra al tocar fuera o con Escape.
  (function () {{
    var m = document.querySelector('.lang-menu');
    if (!m) return;
    document.addEventListener('click', function (e) {{ if (m.open && !m.contains(e.target)) m.open = false; }});
    document.addEventListener('keydown', function (e) {{ if (e.key === 'Escape' && m.open) {{ m.open = false; m.querySelector('summary').focus(); }} }});
  }})();
</script>
</body>
</html>
'''
    target = OUT / (path + 'index.html' if path == '' or path.endswith('/') else path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(doc, 'utf-8')


# ---------------------------------------------------------------------------
# Contenido


def load() -> dict:
    base = CONTENT / 'apps' / 'allthegames'
    app = json.loads((base / 'app.json').read_text('utf-8'))
    app_i18n = json.loads((base / 'app.i18n.json').read_text('utf-8'))
    catalog = json.loads((base / 'catalog-i18n.json').read_text('utf-8'))
    faq = {'es': json.loads((base / 'faq.es.json').read_text('utf-8'))}
    for l in LANGS[1:]:
        faq[l] = json.loads((base / f'faq.{l}.json').read_text('utf-8'))
    return {
        'app': app,
        'appI18n': app_i18n,
        'catalog': catalog,
        # Los juegos que la app tiene ocultos tampoco salen en la web.
        'games': [g for g in json.loads((base / 'games.json').read_text('utf-8')) if not g.get('hidden')],
        'privacy': json.loads((base / 'privacy.json').read_text('utf-8')),
        'terms': {l: json.loads((base / f'terms.{l}.json').read_text('utf-8')) for l in LANGS},
        'faq': faq,
        # Cómo borrar la cuenta en la nube (Google Play exige una página pública).
        'deleteAccount': json.loads((base / 'delete-account.json').read_text('utf-8')),
        # Nombre y descripciones de cada juego en los 6 idiomas, copiados de la app (tools/export-games.mts).
        'gameText': json.loads((base / 'games-text.json').read_text('utf-8')),
    }


def app_text(d: dict, lang: str, key: str):
    """Texto de la ficha de AllTheGames (lead, facts) en un idioma."""
    return d['app'][key] if lang == 'es' else d['appI18n'][lang][key]


def game_name(d: dict, lang: str, g: dict) -> str:
    """Nombre del juego tal como lo dice la app en ese idioma."""
    return g['name'] if lang == 'es' else d['catalog'][lang]['games'][g['slug']]['name']


def cat_label(d: dict, lang: str, cat: dict) -> str:
    return cat['label'] if lang == 'es' else d['catalog'][lang]['folders'][cat['id']]


PRIMARY = '#C9692E'  # el naranja de la app (botones principales)
STUDIO = '#6E1F2A'  # el granate del estudio


def carousel(c: Ctx, tiles: list[dict], lang: str) -> str:
    """Pared de ladrillos con los juegos de todas las apps: filas desplazadas que van una hacia cada lado."""

    def tile(t: dict, copy: bool) -> str:
        hidden = ' aria-hidden="true" tabindex="-1"' if copy else ''
        return (
            f'<li style="--tile:{pastel(t["accent"], 0.14)};--tag:{band_fill(t["accent"])}">'
            f'<a href="{t["href"]}"{hidden}>'
            f'<img src="{t["img"]}" alt="" width="96" height="96" loading="lazy">'
            f'<span class="tile-name">{esc(t["name"])}</span>'
            f'</a></li>'
        )

    rows = SITE.get('carouselRows', 4)
    per = math.ceil(len(tiles) / rows)
    lines = []
    for r in range(rows):
        part = tiles[r * per:(r + 1) * per]
        k = (r * 2) % max(1, len(part))
        part = part[k:] + part[:k]
        first = ''.join(tile(t, False) for t in part)
        again = ''.join(tile(t, True) for t in part) * 2
        lines.append(f'<ul class="carousel-track">{first}{again}</ul>')
    pause, resume = json.dumps(T(lang, 'pause')), json.dumps(T(lang, 'resume'))
    return f'''<div class="carousel" data-carousel>
    {''.join(lines)}
  </div>
  <div class="wrap carousel-bar">
    <button class="carousel-toggle" type="button" data-carousel-toggle aria-pressed="false">
      <svg class="icon-pause" viewBox="0 0 20 20" width="18" height="18" aria-hidden="true"><rect x="4" y="3" width="4.2" height="14" rx="1.6"/><rect x="11.8" y="3" width="4.2" height="14" rx="1.6"/></svg>
      <svg class="icon-play" viewBox="0 0 20 20" width="18" height="18" aria-hidden="true"><path d="M6 3.6c0-1 1.1-1.6 2-1.1l9 5.9c.8.5.8 1.7 0 2.2l-9 5.9c-.9.5-2-.1-2-1.1z"/></svg>
      <span data-carousel-label>{esc(T(lang, 'pause'))}</span>
    </button>
  </div>
<script>
  (function () {{
    var box = document.querySelector('[data-carousel]');
    var btn = document.querySelector('[data-carousel-toggle]');
    if (!box || !btn) return;
    var label = btn.querySelector('[data-carousel-label]');
    btn.addEventListener('click', function () {{
      var paused = box.classList.toggle('is-paused');
      btn.setAttribute('aria-pressed', paused ? 'true' : 'false');
      label.textContent = paused ? {resume} : {pause};
    }});
  }})();
</script>'''


def mixed_by_category(categories: list[dict], games: list[dict]) -> list[dict]:
    """Los juegos de una app, alternando categorías (uno de cada en cada vuelta)."""
    queues = {cat['id']: [g for g in games if g['folder'] == cat['id']] for cat in categories}
    out = []
    while any(queues.values()):
        for cat in categories:
            if queues[cat['id']]:
                out.append(queues[cat['id']].pop(0))
    return out


def home_tiles(c: Ctx, d: dict, p: dict, lang: str) -> list[dict]:
    """Las fichas del carrusel: juegos de AllTheGames y de AllThePartyGames, intercalados."""
    atg_acc = {cat['id']: cat['accent'] for cat in d['app']['categories']}
    atg = [{
        'img': c.to(f'static/apps/allthegames/games/{g["slug"]}.webp'), 'name': game_name(d, lang, g),
        'href': c.to(game_path('allthegames', g['slug'], lang)), 'accent': atg_acc[g['folder']],
    } for g in mixed_by_category(d['app']['categories'], d['games'])]
    if not p:
        return atg
    p_acc = {cat['id']: cat['accent'] for cat in p['app']['categories']}
    party = [{
        'img': c.to(f'static/apps/allthepartygames/games/{g["slug"]}.webp'), 'name': p['i18n'][lang]['games'][g['slug']],
        'href': c.to(game_path('allthepartygames', g['slug'], lang)), 'accent': p_acc[g['folder']],
    } for g in mixed_by_category(p['app']['categories'], p['app']['games'])]
    # Reparto proporcional: cada cierto número de juegos de una app, uno de la otra.
    out, step = [], max(1, round(len(atg) / max(1, len(party))))
    for i, t in enumerate(atg):
        out.append(t)
        if (i + 1) % step == 0 and party:
            out.append(party.pop(0))
    return out + party


def app_feature(c: Ctx, lang: str, *, name: str, here: str, logo: str, logo_size: tuple, lead: str,
                chips: list[tuple[str, str]], store_published: bool, privacy: str, badge: str = '') -> str:
    """La tarjeta de una app en la portada (todas iguales)."""
    chip_html = ''.join(f'<li style="--chip:{acc}">{esc(label)}</li>' for label, acc in chips)
    store = T(lang, 'storeYes') if store_published else T(lang, 'storeSoon')
    badge_html = f' <span class="age-badge">{badge}</span>' if badge else ''
    return f'''<article class="feature card">
    <a class="feature-art" href="{c.to(here)}" tabindex="-1" aria-hidden="true">
      <img src="{c.to(logo)}" alt="" width="{logo_size[0]}" height="{logo_size[1]}" loading="lazy">
    </a>
    <div class="feature-copy">
      <h3 class="display feature-name"><a href="{c.to(here)}">{name}</a>{badge_html}</h3>
      <p>{esc(lead)}</p>
      <ul class="chips" aria-label="{esc(T(lang, 'byCategory'))}">{chip_html}</ul>
      <p class="muted">{esc(T(lang, 'forAndroid'))} {esc(store)}</p>
      <div class="actions">
        <a class="sticker" href="{c.to(here)}">{esc(T(lang, 'seeApp'))}</a>
        <a class="sticker sticker-soft" href="{c.to(here + 'soporte/')}">{esc(T(lang, 'support'))}</a>
        <a class="sticker sticker-soft" href="{c.to(privacy)}">{esc(T(lang, 'privacy'))}</a>
      </div>
    </div>
  </article>'''


def build_home(d: dict, p: dict, lang: str) -> None:
    """Inicio: la portada del estudio, con todas sus apps en pie de igualdad."""
    here = lp(lang, '')
    c = Ctx(here)
    features = [app_feature(
        c, lang, name='AllTheGames', here=lp(lang, 'apps/allthegames/'), logo='static/apps/allthegames/logo.webp',
        logo_size=(743, 500), lead=app_text(d, lang, 'lead'),
        chips=[(cat_label(d, lang, cat), cat['accent']) for cat in d['app']['categories']],
        store_published=d['app'].get('storePublished', False), privacy=privacy_paths()[lang])]
    supports = [('AllTheGames', lp(lang, 'apps/allthegames/soporte/'))]
    if p:
        features.append(app_feature(
            c, lang, name='AllThePartyGames', here=lp(lang, PARTY), logo='static/apps/allthepartygames/logo.webp',
            logo_size=(760, 541), lead=p['i18n'][lang]['tagline'],
            chips=[(p['i18n'][lang]['categories'][cat['id']], cat['accent']) for cat in p['app']['categories']],
            store_published=p['app'].get('storePublished', False), privacy=party_paths('privacy')[lang], badge='+18'))
        supports.append(('AllThePartyGames', lp(lang, PARTY + 'soporte/')))
    features += [planned_feature(c, lang, a) for a in PLANNED]
    support_buttons = ''.join(
        f'<a class="sticker{"" if i == 0 else " sticker-soft"}" href="{c.to(path)}">{esc(T(lang, "appSupportTitle", app=name))}</a>'
        for i, (name, path) in enumerate(supports)
    )
    subject = T(lang, 'workSubject').replace(' ', '%20')
    main = f'''<section class="wrap hero">
  <div class="hero-copy">
    <h1 class="display hero-title">{esc(T(lang, 'headline'))}</h1>
    <p class="lead">{esc(T(lang, 'intro'))}</p>
    <div class="actions">
      <a class="sticker" href="#apps">{esc(T(lang, 'ctaApps'))}</a>
      <a class="sticker sticker-soft" href="#contacto">{esc(T(lang, 'ctaWrite'))}</a>
    </div>
  </div>
  <div class="hero-art" aria-hidden="true">
    <img class="hero-icon" src="{c.to('static/brand/mark-512.png')}" alt="" width="384" height="384">
    <span class="hero-chip chip-a" style="--chip:#2F7A55">{esc(T(lang, 'chipAndroid'))}</span>
    <span class="hero-chip chip-b" style="--chip:#2D63A6">{esc(T(lang, 'chipLangs'))}</span>
    <span class="hero-chip chip-c" style="--chip:#7048A8">{esc(T(lang, 'chipNoAccount'))}</span>
  </div>
</section>

<section class="games-wall" aria-labelledby="juegos-h">
  <div class="wrap section-head">
    <h2 id="juegos-h" class="display">{esc(T(lang, 'wallAll'))}</h2>
  </div>
  {carousel(c, home_tiles(c, d, p, lang), lang)}
</section>

<section class="wrap block apps-list" id="apps" aria-labelledby="app-h">
  <h2 id="app-h" class="display">{esc(T(lang, 'theApps'))}</h2>
  {''.join(features)}
</section>

<section class="wrap block" id="contacto" aria-labelledby="contacto-h">
  <div class="card sheet-card">
    <h2 id="contacto-h" class="band-title" style="--fill:{band_fill(STUDIO)};--lip:{band_lip(STUDIO)}">{esc(T(lang, 'contact'))}</h2>
    <div class="contact-grid">
      <div>
        <h3>{esc(T(lang, 'helpTitle'))}</h3>
        <p>{esc(T(lang, 'helpBody'))}</p>
        <div class="actions">{support_buttons}</div>
      </div>
      <div>
        <h3>{esc(T(lang, 'workTitle'))}</h3>
        <p>{esc(T(lang, 'workBody'))}</p>
        <a class="sticker sticker-soft" href="mailto:{EMAIL}?subject={esc(subject)}">{esc(T(lang, 'writeTo', email=EMAIL))}</a>
      </div>
    </div>
  </div>
</section>'''
    page(here, title=T(lang, 'homeTitle'), description=T(lang, 'intro'), main=main,
         theme='studio', section=here, lang=lang, links=same_page(''))


def build_legal_notice(d: dict, lang: str) -> None:
    here = lp(lang, 'aviso-legal/')
    docs = ('<a href="https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages">'
            f'{esc(T(lang, "legalDocs"))}</a>')
    owner = esc(T(lang, 'legalOwner')).replace('{owner}', esc(OWNER)).replace(
        '{note}', esc(T(lang, 'ownerNote'))).replace('{email}', mail_link())
    data = esc(T(lang, 'legalData')).replace('{docs}', docs)
    main = f'''<div class="wrap narrow sheet legal">
  <h1 class="band-title" style="--fill:{band_fill(STUDIO)};--lip:{band_lip(STUDIO)}">{esc(T(lang, 'legalTitle'))}</h1>
  <h2>{esc(T(lang, 'legalOwnerH'))}</h2>
  <p>{owner}</p>
  <h2>{esc(T(lang, 'legalWhatH'))}</h2>
  <p>{esc(T(lang, 'legalWhat'))}</p>
  <h2>{esc(T(lang, 'legalDataH'))}</h2>
  <p>{data}</p>
</div>'''
    page(here, title=f'{T(lang, "legalTitle")} · {BRAND}', description=T(lang, 'legalDescription'),
         main=main, theme='studio', section=None, lang=lang, links=same_page('aviso-legal/'))


def build_404(d: dict) -> None:
    """Una sola página 404 para toda la web: en español y, debajo, en inglés."""
    main = f'''<div class="wrap narrow sheet">
  <h1 class="band-title" style="--fill:{band_fill(STUDIO)};--lip:{band_lip(STUDIO)}">{esc(T('es', 'notFoundTitle'))}</h1>
  <p class="lead">{esc(T('es', 'notFoundBody'))}</p>
  <p lang="en">{esc(T('en', 'notFoundTitle'))}. {esc(T('en', 'notFoundBody'))}</p>
  <p><a class="sticker" href="/">{esc(T('es', 'notFoundHome'))}</a></p>
</div>'''
    page('404.html', title=f'{T("es", "notFoundMeta")} · {BRAND}', description=T('es', 'notFoundMeta'), main=main,
         theme='studio', section=None, hreflang=False, absolute=True)


# ---------------------------------------------------------------------------
# AllTheGames

PIZARRA = '#4A6076'
ATG_ICON = 'static/apps/allthegames/favicon.png'


def atg_tabs(lang: str) -> list[tuple[str, str]]:
    return [
        (lp(lang, 'apps/allthegames/'), T(lang, 'tabApp')),
        (lp(lang, 'apps/allthegames/soporte/'), T(lang, 'support')),
        (privacy_paths()[lang], T(lang, 'privacy')),
        (terms_paths()[lang], T(lang, 'tabTerms')),
    ]


def atg_nav(c: Ctx, current: str, lang: str) -> str:
    tabs = ''.join(_tab(c, p, label, current) for p, label in atg_tabs(lang))
    return f'''<div class="appnav">
  <div class="wrap appnav-row">
    <a class="appnav-brand" href="{c.to(lp(lang, 'apps/allthegames/'))}">
      <img src="{c.to('static/apps/allthegames/icon.webp')}" alt="" width="40" height="40">
      <span>AllTheGames</span>
    </a>
    <nav class="appnav-tabs" aria-label="AllTheGames">{tabs}</nav>
  </div>
</div>'''


def _tab(c: Ctx, p: str, label: str, current: str) -> str:
    cur = ' aria-current="page"' if p == current else ''
    return f'<a href="{c.to(p)}"{cur}>{esc(label)}</a>'


# Capturas que no se muestran en la galería (ninguna de momento). Que la propia app
# enseñe un recuento en su pantalla no cuenta: la norma es para textos y titulares.
SCREEN_SKIP: set[str] = set()

SCREEN_CATS = {'cartas': 'cartas', 'mesa': 'mesa', 'numeros': 'numeros', 'letras': 'letras',
               'accion': 'accion', 'puzzles': 'puzzle'}


def screens(c: Ctx, d: dict, lang: str) -> str:
    """Galería con las capturas de Google Play en el idioma de la página (tools/export-screens.py)."""
    folder = STATIC / 'apps' / 'allthegames' / 'screens' / lang
    files = sorted(f for f in folder.glob('*.webp') if f.stem not in SCREEN_SKIP) if folder.exists() else []
    if not files:
        return ''
    cats = {cat['id']: cat for cat in d['app']['categories']}
    items = []
    for f in files:
        key = f.stem.split('-', 1)[1]
        if key == 'inicio':
            alt = T(lang, 'screenHome')
        elif key == 'juegos':
            alt = T(lang, 'screenGames')
        elif key in SCREEN_CATS and SCREEN_CATS[key] in cats:
            alt = T(lang, 'screenCat', cat=cat_label(d, lang, cats[SCREEN_CATS[key]]))
        else:
            alt = 'AllTheGames'
        src = c.to(f'static/apps/allthegames/screens/{lang}/{f.name}')
        items.append(f'<li><img src="{src}" alt="{esc(alt)}" width="540" height="960" loading="lazy"></li>')
    return f'''<section class="wrap shots" aria-labelledby="capturas">
  <h2 id="capturas" class="atg-h2">{esc(T(lang, 'screensTitle'))}</h2>
  <ul class="shots-strip" tabindex="0" aria-label="{esc(T(lang, 'screensAria'))}">{''.join(items)}</ul>
</section>
'''


def build_atg_home(d: dict, lang: str) -> None:
    app, games = d['app'], d['games']
    here = lp(lang, 'apps/allthegames/')
    c = Ctx(here)
    s = lambda p: c.to('static/apps/allthegames/' + p)
    facts = ''.join(f'<li>{esc(f)}</li>' for f in app_text(d, lang, 'facts'))
    cats = []
    for cat in app['categories']:
        mine = [g for g in games if g['folder'] == cat['id']]
        tiles = ''.join(
            f'''<li class="game"><a href="{c.to(game_path('allthegames', g['slug'], lang))}">
        <img src="{s('games/' + g['slug'] + '.webp')}" alt="" width="72" height="72" loading="lazy">
        <span>{esc(game_name(d, lang, g))}</span>
      </a></li>'''
            for g in mine
        )
        cats.append(f'''<section class="cat" aria-labelledby="cat-{cat['id']}">
    <h3 class="cat-band" id="cat-{cat['id']}" style="--fill:{band_fill(cat['accent'])};--lip:{band_lip(cat['accent'])}">
      <img src="{s('categories/' + cat['id'] + '.webp')}" alt="" width="44" height="44">
      <span>{esc(cat_label(d, lang, cat))}</span>
    </h3>
    <ul class="games">
      {tiles}
    </ul>
  </section>''')
    store = (
        f'<a class="sticker" href="{esc(app["storeUrl"])}&amp;hl={HTML_LANG[lang]}">{esc(T(lang, "download"))}</a>'
        if app.get('storePublished') else f'<p class="soon">{esc(T(lang, "soon"))}</p>'
    )
    main = f'''<section class="wrap atg-hero">
  <img class="atg-logo" src="{s('logo.webp')}" alt="" width="743" height="500">
  <div class="atg-intro">
    <h1 class="visually-hidden">AllTheGames</h1>
    <p class="lead">{esc(app_text(d, lang, 'lead'))}</p>
    {store}
    <ul class="facts">{facts}</ul>
  </div>
</section>
{screens(c, d, lang)}<section class="wrap catalog" aria-labelledby="los-juegos">
  <h2 id="los-juegos" class="atg-h2">{esc(T(lang, 'atgGames'))}</h2>
  {''.join(cats)}
</section>
<section class="wrap atg-help" aria-labelledby="atg-ayuda">
  <h2 id="atg-ayuda" class="atg-h2">{esc(T(lang, 'atgHelp'))}</h2>
  <div class="help-row">
    <a class="sticker" href="{c.to(lp(lang, 'apps/allthegames/soporte/'))}">{esc(T(lang, 'support'))}</a>
    <a class="sticker sticker-soft" href="{c.to(privacy_paths()[lang])}">{esc(T(lang, 'privacy'))}</a>
    <a class="sticker sticker-soft" href="{c.to(terms_paths()[lang])}">{esc(T(lang, 'termsLong'))}</a>
  </div>
</section>'''
    page(here, title=f'AllTheGames · {BRAND}', description=app_text(d, lang, 'lead'), main=main, theme='atg',
         section=here, lang=lang, links=same_page('apps/allthegames/'),
         pre_main=atg_nav(c, here, lang), favicon=ATG_ICON)


def build_atg_support(d: dict, lang: str) -> None:
    here = lp(lang, 'apps/allthegames/soporte/')
    c = Ctx(here)
    items = ''.join(
        f'''<details class="faq" id="{slug(q)}">
    <summary>{esc(q)}</summary>
    <p>{rich(a)}</p>
  </details>'''
        for q, a in d['faq'][lang]
    )
    subject = T(lang, 'supportSubject').replace(' · ', '%20%C2%B7%20').replace(' ', '%20')
    write = esc(T(lang, 'supportWrite')).replace('{email}', mail_link())
    main = f'''<div class="wrap narrow sheet">
  <h1 class="band-title" style="--fill:{band_fill(PRIMARY)};--lip:{band_lip(PRIMARY)}">{esc(T(lang, 'supportTitle'))}</h1>
  <p class="lead">{esc(T(lang, 'supportLead'))}</p>
  {items}
  <section class="contact">
    <h2>{esc(T(lang, 'supportWriteH'))}</h2>
    <p>{write}</p>
    <a class="sticker" href="mailto:{esc(EMAIL)}?subject={esc(subject)}">{esc(T(lang, 'supportButton'))}</a>
  </section>
</div>
<script>
  // Un enlace a una pregunta (#como-cancelo...) la abre.
  function abrirPregunta() {{
    var el = document.getElementById(decodeURIComponent(location.hash.slice(1)));
    if (el && el.tagName === 'DETAILS') el.open = true;
  }}
  abrirPregunta();
  window.addEventListener('hashchange', abrirPregunta);
</script>'''
    page(here, title=f'{T(lang, "supportPageTitle")} · {BRAND}', description=T(lang, 'supportDescription'),
         main=main, theme='atg', section=lp(lang, 'apps/allthegames/'), lang=lang,
         links=same_page('apps/allthegames/soporte/'), pre_main=atg_nav(c, here, lang), favicon=ATG_ICON)


def privacy_paths() -> dict:
    return {l: 'apps/allthegames/privacidad/' + ('' if l == 'es' else l + '/') for l in LANGS}


def terms_paths() -> dict:
    return {l: 'apps/allthegames/terminos/' + ('' if l == 'es' else l + '/') for l in LANGS}


def delete_paths() -> dict:
    return {l: 'apps/allthegames/borrar-cuenta/' + ('' if l == 'es' else l + '/') for l in LANGS}


def lang_chips(c: Ctx, lang: str, here: str, paths: dict) -> str:
    """Los idiomas de un texto legal, como fichas (la del idioma actual, marcada)."""
    chips = []
    for l in LANGS:
        on = l == lang and here == paths[lang]
        cls = 'chip chip-on' if on else 'chip'
        cur = ' aria-current="page"' if on else ''
        chips.append(f'<a class="{cls}" href="{c.to(paths[l])}" hreflang="{HTML_LANG[l]}" lang="{HTML_LANG[l]}"{cur}>{LANG_NAMES[l]}</a>')
    return ''.join(chips)


def privacy_main(d: dict, lang: str, here: str) -> str:
    c = Ctx(here)
    p = d['privacy'][lang]
    chrome = PRIVACY_CHROME[lang]
    paths = privacy_paths()
    count = 1
    while f's{count + 1}Title' in p:
        count += 1
    sections = ''.join(
        f'<h2>{esc(p[f"s{i}Title"])}</h2>\n  <p>{rich(p[f"s{i}Body"])}</p>\n  ' for i in range(1, count + 1)
    )
    title = p['title'][:1] + p['title'][1:].lower()
    delete = d.get('deleteAccount', {}).get(lang)
    delete_link = (
        f' · <a href="{c.to(delete_paths()[lang])}">{esc(delete["linkText"])}</a>' if delete else ''
    )
    return f'''<div class="wrap narrow sheet legal">
  <h1 class="band-title" style="--fill:{band_fill(PIZARRA)};--lip:{band_lip(PIZARRA)}">{esc(title)}</h1>
  <p class="meta">{esc(p['updated'].replace('{date}', p['date']))}</p>
  <nav class="langs" aria-label="{esc(chrome['langs'])}">{lang_chips(c, lang, here, paths)}</nav>
  <p class="lead">{rich(p['intro'])}</p>
  {sections}
  <p class="legal-links"><a href="{c.to(terms_paths()[lang])}">{esc(chrome['terms'])}</a>{delete_link}</p>
</div>'''


def build_atg_delete_account(d: dict) -> None:
    """Cómo borrar la cuenta en la nube, en los 6 idiomas (la URL que pide Google Play)."""
    paths = delete_paths()

    def main_for(lang: str, here: str) -> str:
        c = Ctx(here)
        t = d['deleteAccount'][lang]
        sections = ''.join(f'<h2>{esc(h)}</h2>\n  <p>{rich(b)}</p>\n  ' for h, b in t['sections'])
        return f'''<div class="wrap narrow sheet legal">
  <h1 class="band-title" style="--fill:{band_fill(PIZARRA)};--lip:{band_lip(PIZARRA)}">{esc(t['title'])}</h1>
  <p class="meta">{esc(t['updated'])}</p>
  <nav class="langs" aria-label="{esc(T(lang, 'langMenu'))}">{lang_chips(c, lang, here, paths)}</nav>
  <p class="lead">{rich(t['lead'])}</p>
  {sections}
  <p class="legal-links"><a href="{c.to(privacy_paths()[lang])}">{esc(T(lang, 'privacy'))}</a></p>
</div>'''

    for lang in LANGS:
        here = paths[lang]
        t = d['deleteAccount'][lang]
        page(here, title=f'{t["title"]} · AllTheGames', description=t['lead'], main=main_for(lang, here),
             theme='atg', section=lp(lang, 'apps/allthegames/'), lang=lang, links=paths,
             pre_main=atg_nav(Ctx(here), here, lang), favicon=ATG_ICON)


def build_atg_privacy(d: dict) -> None:
    version = d['app']['policyVersion']
    paths = privacy_paths()
    for lang in LANGS:
        p = d['privacy'][lang]
        title = p['title'][:1] + p['title'][1:].lower()
        here = paths[lang]
        page(here, title=f'{title} · AllTheGames', description=p['intro'], main=privacy_main(d, lang, here),
             theme='atg', section=lp(lang, 'apps/allthegames/'), lang=lang, links=paths,
             pre_main=atg_nav(Ctx(here), here, lang), favicon=ATG_ICON)
    # Versión vigente y versiones anteriores (content/apps/allthegames/privacy-archive/<fecha>.json),
    # cada una en su URL con fecha y en español.
    versions = {version: d}
    for f in sorted((CONTENT / 'apps' / 'allthegames' / 'privacy-archive').glob('*.json')):
        versions.setdefault(f.stem, {**d, 'privacy': json.loads(f.read_text('utf-8'))})
    for ver, dv in versions.items():
        dated = f'apps/allthegames/privacidad/{ver}/'
        page(dated, title=f'Privacidad ({ver}) · AllTheGames', description=dv['privacy']['es']['intro'],
             main=privacy_main(dv, 'es', dated), theme='atg', section='apps/allthegames/', links=paths,
             hreflang=False, pre_main=atg_nav(Ctx(dated), paths['es'], 'es'), favicon=ATG_ICON)


def build_atg_terms(d: dict) -> None:
    """Los términos de compra, en los 6 idiomas (copiados de la app con tools/export-terms.py)."""
    paths = terms_paths()

    def main_for(lang: str, here: str) -> str:
        c = Ctx(here)
        t = d['terms'][lang]
        priv = f'<a href="{c.to(privacy_paths()[lang])}">{esc(t.get("privacyLinkText", "nota de privacidad"))}</a>'
        sections = ''.join(
            f'<h2>{esc(h)}</h2>\n  <p>{rich(b, {"privacyLink": priv})}</p>\n  ' for h, b in t['sections']
        )
        return f'''<div class="wrap narrow sheet legal">
  <h1 class="band-title" style="--fill:{band_fill(PIZARRA)};--lip:{band_lip(PIZARRA)}">{esc(t['title'])}</h1>
  <p class="meta">{esc(t['updated'])}</p>
  <nav class="langs" aria-label="{esc(T(lang, 'langMenu'))}">{lang_chips(c, lang, here, paths)}</nav>
  <p class="lead">{esc(t['intro'])}</p>
  {sections}
</div>'''

    for lang in LANGS:
        here = paths[lang]
        t = d['terms'][lang]
        page(here, title=f'{t["title"]} · AllTheGames', description=t['intro'], main=main_for(lang, here),
             theme='atg', section=lp(lang, 'apps/allthegames/'), lang=lang, links=paths,
             pre_main=atg_nav(Ctx(here), here, lang), favicon=ATG_ICON)
    es = d['terms']['es']
    dated = f'apps/allthegames/terminos/{es["version"]}/'
    page(dated, title=f'{es["title"]} ({es["version"]}) · AllTheGames', description=es['intro'],
         main=main_for('es', dated), theme='atg', section='apps/allthegames/', links=paths, hreflang=False,
         pre_main=atg_nav(Ctx(dated), paths['es'], 'es'), favicon=ATG_ICON)


# ---------------------------------------------------------------------------
# AllThePartyGames (+18). Sus datos los copia tools/export-party.py desde la app.

PARTY = 'apps/allthepartygames/'
PARTY_ICON = 'static/apps/allthepartygames/favicon.png'
PARTY_ACCENT = '#B8233F'


def load_party() -> dict:
    base = CONTENT / 'apps' / 'allthepartygames'
    if not (base / 'app.json').exists():
        return {}
    d = {
        'app': json.loads((base / 'app.json').read_text('utf-8')),
        'i18n': json.loads((base / 'i18n.json').read_text('utf-8')),
    }
    for kind in ('privacy', 'terms'):
        d[kind] = {l: json.loads((base / f'{kind}.{l}.json').read_text('utf-8')) for l in LANGS}
    return d


def party_paths(kind: str) -> dict:
    folder = {'privacy': 'privacidad/', 'terms': 'terminos/'}[kind]
    return {l: PARTY + folder + ('' if l == 'es' else l + '/') for l in LANGS}


def party_nav(c: Ctx, current: str, lang: str) -> str:
    tabs = [
        (lp(lang, PARTY), T(lang, 'tabApp')),
        (lp(lang, PARTY + 'soporte/'), T(lang, 'support')),
        (party_paths('privacy')[lang], T(lang, 'privacy')),
        (party_paths('terms')[lang], T(lang, 'tabTerms')),
    ]
    links = ''.join(_tab(c, p, label, current) for p, label in tabs)
    return f'''<div class="appnav">
  <div class="wrap appnav-row">
    <a class="appnav-brand" href="{c.to(lp(lang, PARTY))}">
      <img src="{c.to('static/apps/allthepartygames/icon.webp')}" alt="" width="40" height="40">
      <span>AllThePartyGames</span><span class="age-badge" aria-label="{esc(T(lang, 'adultsTitle'))}">+18</span>
    </a>
    <nav class="appnav-tabs" aria-label="AllThePartyGames">{links}</nav>
  </div>
</div>'''


def age_notice(p: dict, lang: str, compact: bool = False) -> str:
    """El aviso de edad, con el texto de la puerta de edad de la app tal cual."""
    g = p['i18n'][lang]['ageGate']
    if compact:
        return f'<p class="age-strip"><span class="age-badge">+18</span> {esc(g["body"])}</p>'
    return f'''<aside class="age-notice" aria-label="{esc(T(lang, 'adultsTitle'))}">
    <span class="age-badge age-badge-big">+18</span>
    <div>
      <p class="age-title">{esc(g['title'])}</p>
      <p>{esc(g['body'])}</p>
      <p class="muted">{esc(g['drinkResponsibly'])}</p>
    </div>
  </aside>'''


def build_party_home(p: dict, lang: str) -> None:
    app, tx = p['app'], p['i18n'][lang]
    here = lp(lang, PARTY)
    c = Ctx(here)
    s = lambda f: c.to('static/apps/allthepartygames/' + f)
    perks = ''.join(f'<li>{esc(x)}</li>' for x in tx['perks'])
    cats = []
    for cat in app['categories']:
        mine = [g for g in app['games'] if g['folder'] == cat['id']]
        tiles = ''.join(
            f'''<li class="game"><a href="{c.to(game_path('allthepartygames', g['slug'], lang))}">
        <img src="{s('games/' + g['slug'] + '.webp')}" alt="" width="72" height="72" loading="lazy">
        <span>{esc(tx['games'][g['slug']])}</span>
      </a></li>'''
            for g in mine
        )
        cats.append(f'''<section class="cat" aria-labelledby="cat-{cat['id']}">
    <h3 class="cat-band" id="cat-{cat['id']}" style="--fill:{band_fill(cat['accent'])};--lip:{band_lip(cat['accent'])}">
      <img src="{s('categories/' + cat['id'] + '.webp')}" alt="" width="44" height="44">
      <span>{esc(tx['categories'][cat['id']])}</span>
    </h3>
    <ul class="games">
      {tiles}
    </ul>
  </section>''')
    store = (
        f'<a class="sticker" href="{esc(app["storeUrl"])}&amp;hl={HTML_LANG[lang]}">{esc(T(lang, "download"))}</a>'
        if app.get('storePublished') else f'<p class="soon">{esc(T(lang, "soon"))}</p>'
    )
    main = f'''<section class="wrap atg-hero">
  <img class="atg-logo" src="{s('logo.webp')}" alt="" width="760" height="541">
  <div class="atg-intro">
    <h1 class="visually-hidden">AllThePartyGames</h1>
    <p class="lead">{esc(tx['tagline'])}</p>
    {store}
    <ul class="facts">{perks}</ul>
  </div>
</section>
<div class="wrap">{age_notice(p, lang)}</div>
<section class="wrap catalog" aria-labelledby="los-juegos">
  <h2 id="los-juegos" class="atg-h2">{esc(T(lang, 'atgGames'))}</h2>
  {''.join(cats)}
</section>
<section class="wrap atg-help" aria-labelledby="ayuda">
  <h2 id="ayuda" class="atg-h2">{esc(T(lang, 'atgHelp'))}</h2>
  <div class="help-row">
    <a class="sticker" href="{c.to(lp(lang, PARTY + 'soporte/'))}">{esc(T(lang, 'support'))}</a>
    <a class="sticker sticker-soft" href="{c.to(party_paths('privacy')[lang])}">{esc(T(lang, 'privacy'))}</a>
    <a class="sticker sticker-soft" href="{c.to(party_paths('terms')[lang])}">{esc(T(lang, 'termsLong'))}</a>
  </div>
</section>'''
    page(here, title=f'AllThePartyGames · {BRAND}', description=tx['tagline'], main=main, theme='party',
         section=here, lang=lang, links=same_page(PARTY), pre_main=party_nav(c, here, lang), favicon=PARTY_ICON)


def build_party_support(p: dict, lang: str) -> None:
    tx = p['i18n'][lang]
    here = lp(lang, PARTY + 'soporte/')
    c = Ctx(here)
    items = ''.join(
        f'''<details class="faq" id="{slug(q)}">
    <summary>{esc(q)}</summary>
    <p>{rich(a)}</p>
  </details>'''
        for q, a in tx['faq']
    )
    subject = T(lang, 'appSupportSubject', app='AllThePartyGames').replace(' · ', '%20%C2%B7%20').replace(' ', '%20')
    write = esc(T(lang, 'supportWrite')).replace('{email}', mail_link())
    main = f'''<div class="wrap narrow sheet">
  <h1 class="band-title" style="--fill:{band_fill(PARTY_ACCENT)};--lip:{band_lip(PARTY_ACCENT)}">{esc(T(lang, 'supportTitle'))}</h1>
  {age_notice(p, lang, compact=True)}
  <p class="lead">{esc(T(lang, 'supportLead'))}</p>
  {items}
  <section class="contact">
    <h2>{esc(T(lang, 'supportWriteH'))}</h2>
    <p>{write}</p>
    <a class="sticker" href="mailto:{esc(EMAIL)}?subject={esc(subject)}">{esc(T(lang, 'supportButton'))}</a>
  </section>
</div>'''
    page(here, title=f'{T(lang, "appSupportTitle", app="AllThePartyGames")} · {BRAND}',
         description=T(lang, 'appSupportDesc', app='AllThePartyGames'), main=main, theme='party', section=lp(lang, PARTY),
         lang=lang, links=same_page(PARTY + 'soporte/'), pre_main=party_nav(c, here, lang), favicon=PARTY_ICON)


def build_party_legal(p: dict, kind: str) -> None:
    """Privacidad o términos de AllThePartyGames, en los 6 idiomas, copiados de la app."""
    paths = party_paths(kind)

    def main_for(lang: str, here: str) -> str:
        c = Ctx(here)
        t = p[kind][lang]
        priv = f'<a href="{c.to(party_paths("privacy")[lang])}">{esc(t.get("privacyLinkText", "nota de privacidad"))}</a>'
        sections = ''.join(
            f'<h2>{esc(h)}</h2>\n  <p>{rich(b, {"privacyLink": priv})}</p>\n  ' for h, b in t['sections']
        )
        other = 'terms' if kind == 'privacy' else 'privacy'
        other_label = T(lang, 'termsLong') if other == 'terms' else T(lang, 'privacy')
        return f'''<div class="wrap narrow sheet legal">
  <h1 class="band-title" style="--fill:{band_fill(PIZARRA)};--lip:{band_lip(PIZARRA)}">{esc(t['title'])}</h1>
  <p class="meta">{esc(t['updated'])}</p>
  <nav class="langs" aria-label="{esc(T(lang, 'langMenu'))}">{lang_chips(c, lang, here, paths)}</nav>
  <p class="lead">{rich(t['intro'])}</p>
  {sections}
  <p class="legal-links"><a href="{c.to(party_paths(other)[lang])}">{esc(other_label)}</a></p>
</div>'''

    for lang in LANGS:
        here = paths[lang]
        t = p[kind][lang]
        page(here, title=f'{t["title"]} · AllThePartyGames', description=t['intro'], main=main_for(lang, here),
             theme='party', section=lp(lang, PARTY), lang=lang, links=paths,
             pre_main=party_nav(Ctx(here), here, lang), favicon=PARTY_ICON)
    es = p[kind]['es']
    dated = paths['es'] + es['version'] + '/'
    page(dated, title=f'{es["title"]} ({es["version"]}) · AllThePartyGames', description=es['intro'],
         main=main_for('es', dated), theme='party', section=PARTY, links=paths, hreflang=False,
         pre_main=party_nav(Ctx(dated), paths['es'], 'es'), favicon=PARTY_ICON)


# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Ficha de cada juego: descripción (la de la app) y la app en la que se juega.


def game_path(app_id: str, game_slug: str, lang: str) -> str:
    return lp(lang, f'apps/{app_id}/juegos/{game_slug}/')


def build_game_pages(*, app_id: str, app_name: str, theme: str, favicon: str, logo: str, logo_size: tuple,
                     lead: Callable[[str], str], store_published: bool, store_url: str,
                     categories: list[dict], cat_name: Callable[[str, str], str], games: list[dict],
                     text: Callable[[str, str], dict], nav: Callable, notice: Callable[[str], str] = lambda l: '',
                     img: Callable[[str], str] | None = None, status: Callable[[str], str] | None = None) -> None:
    """Una página por juego y por idioma. Los textos vienen de la app; aquí no se escribe ninguno."""
    accents = {cat['id']: cat['accent'] for cat in categories}
    app_home = f'apps/{app_id}/'
    img = img or (lambda game_slug: f'static/apps/{app_id}/games/{game_slug}.webp')
    for lang in LANGS:
        for g in games:
            here = game_path(app_id, g['slug'], lang)
            c = Ctx(here)
            t = text(lang, g['slug'])
            acc, cat = accents[g['folder']], cat_name(lang, g['folder'])
            store = (
                status(lang) if status else
                f'<a class="sticker" href="{esc(store_url)}&amp;hl={HTML_LANG[lang]}">{esc(T(lang, "download"))}</a>'
                if store_published else f'<p class="soon">{esc(T(lang, "soon"))}</p>'
            )
            others = ''.join(
                f'''<li class="game"><a href="{c.to(game_path(app_id, o['slug'], lang))}">
        <img src="{c.to(img(o['slug']))}" alt="" width="72" height="72" loading="lazy">
        <span>{esc(text(lang, o['slug'])['name'])}</span>
      </a></li>'''
                for o in games if o['folder'] == g['folder'] and o['slug'] != g['slug']
            )
            more = f'''<section class="game-more" aria-labelledby="mas">
    <h2 id="mas" class="game-h2">{esc(T(lang, 'moreGames', cat=cat))}</h2>
    <ul class="games">{others}</ul>
  </section>''' if others else ''
            main = f'''<div class="wrap narrow sheet game-page">
  <h1 class="band-title" style="--fill:{band_fill(acc)};--lip:{band_lip(acc)}">{esc(t['name'])}</h1>
  <nav class="crumbs" aria-label="{esc(T(lang, 'crumbs'))}">
    <a href="{c.to(lp(lang, app_home))}">{app_name}</a> <span aria-hidden="true">›</span>
    <a href="{c.to(lp(lang, app_home))}#cat-{g['folder']}">{esc(cat)}</a>
  </nav>
  {notice(lang)}
  <div class="game-hero">
    <img src="{c.to(img(g['slug']))}" alt="" width="144" height="144">
    <div>
      <p class="lead">{esc(t['short'])}</p>
      {f"<p>{esc(t['long'])}</p>" if t['long'] else ''}
    </div>
  </div>
  <section class="play-in" aria-labelledby="donde">
    <h2 id="donde" class="game-h2">{esc(T(lang, 'playIn'))}</h2>
    <div class="play-card">
      <a href="{c.to(lp(lang, app_home))}" tabindex="-1" aria-hidden="true"><img src="{c.to(logo)}" alt="" width="{logo_size[0]}" height="{logo_size[1]}" loading="lazy"></a>
      <div>
        <p class="play-card-name display">{app_name}</p>
        <p>{esc(lead(lang))}</p>
        <div class="actions">{store}<a class="sticker sticker-soft" href="{c.to(lp(lang, app_home))}">{esc(T(lang, 'seeApp'))}</a></div>
      </div>
    </div>
  </section>
  {more}
</div>'''
            page(here, title=f"{t['name']} · {app_name}", description=t['short'], main=main, theme=theme,
                 section=lp(lang, app_home), lang=lang, links=same_page(f'apps/{app_id}/juegos/{g["slug"]}/'),
                 pre_main=nav(c, lp(lang, app_home), lang), favicon=favicon)


def build_all_game_pages(d: dict, p: dict) -> None:
    build_game_pages(
        app_id='allthegames', app_name='AllTheGames', theme='atg', favicon=ATG_ICON,
        logo='static/apps/allthegames/logo.webp', logo_size=(743, 500), lead=lambda l: app_text(d, l, 'lead'),
        store_published=d['app'].get('storePublished', False), store_url=d['app']['storeUrl'],
        categories=d['app']['categories'], cat_name=lambda l, f: cat_label(d, l, next(x for x in d['app']['categories'] if x['id'] == f)),
        games=d['games'], text=lambda l, g: d['gameText'][l][g], nav=atg_nav)
    if not p:
        return
    build_game_pages(
        app_id='allthepartygames', app_name='AllThePartyGames', theme='party', favicon=PARTY_ICON,
        logo='static/apps/allthepartygames/logo.webp', logo_size=(760, 541), lead=lambda l: p['i18n'][l]['tagline'],
        store_published=p['app'].get('storePublished', False), store_url=p['app']['storeUrl'],
        categories=p['app']['categories'], cat_name=lambda l, f: p['i18n'][l]['categories'][f],
        games=p['app']['games'],
        text=lambda l, g: {'name': p['i18n'][l]['games'][g], **p['i18n'][l]['gameText'][g]},
        nav=party_nav, notice=lambda l: age_notice(p, l, compact=True))


# ---------------------------------------------------------------------------
# Apps en desarrollo (solo en la copia local). Textos provisionales en español
# (content/planned-apps.json) e imágenes provisionales generadas aquí.


def svg_tile(text: str, accent: str) -> str:
    initials = ''.join(w[0] for w in re.findall(r'[A-Za-zÁÉÍÓÚÑáéíóúñ¿?]+', text) if w[0].isalpha())[:2].upper() or '?'
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 96 96"><rect x="6" y="6" width="84" height="84" rx="22" '
            f'fill="{accent}" stroke="#2A1A1D" stroke-width="4"/><text x="48" y="60" text-anchor="middle" '
            f'font-family="Arial Black, Arial, sans-serif" font-weight="900" font-size="34" fill="#FFF8EE">{esc(initials)}</text></svg>')


def svg_logo(word: str, accent: str) -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 270"><g font-family="Arial Black, Arial, sans-serif" '
            f'font-weight="900" text-anchor="middle" stroke="#2A1A1D" stroke-width="8" paint-order="stroke">'
            f'<text x="200" y="70" font-size="62" fill="#FFF8EE">AllThe</text>'
            f'<text x="200" y="165" font-size="96" fill="{accent}">{esc(word)}</text>'
            f'<text x="200" y="240" font-size="62" fill="#FFF8EE">Games</text></g></svg>')


def planned_static(a: dict) -> None:
    base = OUT / 'static' / 'planned' / a['id']
    (base / 'games').mkdir(parents=True, exist_ok=True)
    (base / 'logo.svg').write_text(svg_logo(a['word'], a['accent']), 'utf-8')
    acc = {cat['id']: cat['accent'] for cat in a['categories']}
    for g in a['games']:
        (base / 'games' / f"{g['slug']}.svg").write_text(svg_tile(g['name'], acc[g['folder']]), 'utf-8')


def in_dev(lang: str) -> str:
    return f'<p class="soon">{esc(T(lang, "inDev"))}</p>'


def planned_feature(c: Ctx, lang: str, a: dict) -> str:
    here = lp(lang, f"apps/{a['id']}/")
    chips = ''.join(f'<li style="--chip:{cat["accent"]}">{esc(cat["label"])}</li>' for cat in a['categories'])
    return f'''<article class="feature card">
    <a class="feature-art" href="{c.to(here)}" tabindex="-1" aria-hidden="true">
      <img src="{c.to(f"static/planned/{a['id']}/logo.svg")}" alt="" width="400" height="270" loading="lazy">
    </a>
    <div class="feature-copy">
      <h3 class="display feature-name"><a href="{c.to(here)}">{a['name']}</a></h3>
      <p>{esc(a['tagline'])}</p>
      <ul class="chips" aria-label="{esc(T(lang, 'byCategory'))}">{chips}</ul>
      {in_dev(lang)}
      <div class="actions"><a class="sticker" href="{c.to(here)}">{esc(T(lang, 'seeApp'))}</a></div>
    </div>
  </article>'''


def build_planned(a: dict) -> None:
    planned_static(a)
    for lang in LANGS:
        here = lp(lang, f"apps/{a['id']}/")
        c = Ctx(here)
        perks = ''.join(f'<li>{esc(x)}</li>' for x in a['perks'])
        cats = []
        for cat in a['categories']:
            tiles = ''.join(
                f'''<li class="game"><a href="{c.to(game_path(a['id'], g['slug'], lang))}">
        <img src="{c.to(f"static/planned/{a['id']}/games/{g['slug']}.svg")}" alt="" width="72" height="72" loading="lazy">
        <span>{esc(g['name'])}</span>
      </a></li>'''
                for g in a['games'] if g['folder'] == cat['id'])
            cats.append(f'''<section class="cat" aria-labelledby="cat-{cat['id']}">
    <h3 class="cat-band" id="cat-{cat['id']}" style="--fill:{band_fill(cat['accent'])};--lip:{band_lip(cat['accent'])}">
      <span>{esc(cat['label'])}</span>
    </h3>
    <ul class="games">
      {tiles}
    </ul>
  </section>''')
        main = f'''<section class="wrap atg-hero">
  <img class="atg-logo" src="{c.to(f"static/planned/{a['id']}/logo.svg")}" alt="" width="400" height="270">
  <div class="atg-intro">
    <h1 class="visually-hidden">{a['name']}</h1>
    <p class="lead">{esc(a['tagline'])}</p>
    {in_dev(lang)}
    <ul class="facts">{perks}</ul>
  </div>
</section>
<section class="wrap catalog" aria-labelledby="los-juegos">
  <h2 id="los-juegos" class="atg-h2">{esc(T(lang, 'atgGames'))}</h2>
  {''.join(cats)}
</section>'''
        page(here, title=f"{a['name']} · {BRAND}", description=a['tagline'], main=main, theme='studio',
             section=here, lang=lang, links=same_page(f"apps/{a['id']}/"))
    by_slug = {g['slug']: g for g in a['games']}
    build_game_pages(
        app_id=a['id'], app_name=a['name'], theme='studio', favicon='static/brand/favicon-64.png',
        logo=f"static/planned/{a['id']}/logo.svg", logo_size=(400, 270), lead=lambda l: a['tagline'],
        store_published=False, store_url='', categories=a['categories'],
        cat_name=lambda l, f: next(x['label'] for x in a['categories'] if x['id'] == f),
        games=a['games'], text=lambda l, g: {'name': by_slug[g]['name'], 'short': by_slug[g]['short'], 'long': ''},
        nav=lambda c, cur, l: '', img=lambda g: f"static/planned/{a['id']}/games/{g}.svg", status=in_dev)


def build() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    shutil.copytree(STATIC, OUT / 'static')
    (OUT / '.nojekyll').write_text('', 'utf-8')
    (OUT / 'app-ads.txt').write_text(f'google.com, {SITE["admobPublisher"]}, DIRECT, f08c47fec0942fa0\n', 'utf-8')
    (OUT / 'robots.txt').write_text(f'User-agent: *\nAllow: /\nSitemap: {SITE["baseUrl"].rstrip("/")}/sitemap.xml\n', 'utf-8')
    if SITE.get('domain'):
        (OUT / 'CNAME').write_text(SITE['domain'] + '\n', 'utf-8')
    d = load()
    party = load_party()
    for lang in LANGS:
        build_home(d, party, lang)
        build_legal_notice(d, lang)
        build_atg_home(d, lang)
        build_atg_support(d, lang)
    build_404(d)
    build_atg_privacy(d)
    build_atg_terms(d)
    build_atg_delete_account(d)
    if party:
        for lang in LANGS:
            build_party_home(party, lang)
            build_party_support(party, lang)
        build_party_legal(party, 'privacy')
        build_party_legal(party, 'terms')
    build_all_game_pages(d, party)
    for a in PLANNED:
        build_planned(a)
    base = SITE['baseUrl'].rstrip('/')
    urls = sorted(
        p.parent.relative_to(OUT).as_posix() for p in OUT.rglob('index.html') if 'static' not in p.parts
    )
    sitemap = ''.join(
        f'  <url><loc>{base}/{"" if u == "." else u + "/"}</loc></url>\n' for u in urls
    )
    (OUT / 'sitemap.xml').write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + sitemap + '</urlset>\n',
        'utf-8',
    )
    print(f'Web generada en {OUT.name}/ ({len(urls)} páginas).')


if __name__ == '__main__':
    build()
