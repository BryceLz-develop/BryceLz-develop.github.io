#!/usr/bin/env python3
"""
Genera la web de BryceLz en docs/ a partir de content/ y static/.

    python3 build.py

GitHub Pages publica la carpeta docs/ de la rama main. Solo hace falta
Python 3, sin instalar nada.
"""
import html
import json
import math
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONTENT = ROOT / 'content'
STATIC = ROOT / 'static'
OUT = ROOT / 'docs'

SITE = json.loads((CONTENT / 'site.json').read_text('utf-8'))
BRAND = SITE['brand']
OWNER = SITE['owner']
EMAIL = SITE['email']
YEAR = SITE['year']

LANGS = ['es', 'en', 'fr', 'de', 'it', 'pt']
LANG_NAMES = {
    'es': 'Español', 'en': 'English', 'fr': 'Français',
    'de': 'Deutsch', 'it': 'Italiano', 'pt': 'Português',
}
# Texto de la web alrededor de la nota de privacidad, en cada idioma.
PRIVACY_CHROME = {
    'es': {'terms': 'Términos de las compras', 'langs': 'Otros idiomas'},
    'en': {'terms': 'Purchase terms (in Spanish)', 'langs': 'Other languages'},
    'fr': {'terms': 'Conditions d’achat (en espagnol)', 'langs': 'Autres langues'},
    'de': {'terms': 'Kaufbedingungen (auf Spanisch)', 'langs': 'Andere Sprachen'},
    'it': {'terms': 'Termini di acquisto (in spagnolo)', 'langs': 'Altre lingue'},
    'pt': {'terms': 'Termos de compra (em espanhol)', 'langs': 'Outros idiomas'},
}

# Enlaces dentro de los textos legales (solo nombres exactos).
AUTO_LINKS = {
    'rae-api.com': 'https://rae-api.com',
    'flagcdn.com': 'https://flagcdn.com',
    'aepd.es': 'https://www.aepd.es',
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
    t = text.lower()
    for a, b in zip('áéíóúüñ', 'aeiouun'):
        t = t.replace(a, b)
    return re.sub(r'[^a-z0-9]+', '-', t).strip('-')


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

# Los apartados del banner. De momento: Inicio y AllTheGames.
NAV = [('', 'Inicio'), ('apps/allthegames/', 'AllTheGames')]


def wordmark(c: Ctx) -> str:
    return (
        f'<a class="wordmark" href="{c.to("")}" aria-label="{BRAND}, inicio">'
        f'{BRAND}<span class="wordmark-dot" aria-hidden="true"></span></a>'
    )


def site_header(c: Ctx, section: str | None) -> str:
    """El banner de arriba, como los de la app: banda honda con labio y botones dentro."""
    tabs = ''.join(_nav_link(c, path, label, section) for path, label in NAV)
    return f'''<header class="banner">
  <div class="wrap banner-row">
    {wordmark(c)}
    <nav class="banner-nav" aria-label="Apartados">{tabs}</nav>
  </div>
</header>'''


def _nav_link(c: Ctx, path: str, label: str, section: str | None) -> str:
    current = ' aria-current="page"' if section == path else ''
    return f'<a class="banner-tab" href="{c.to(path)}"{current}>{label}</a>'


def site_footer(c: Ctx, apps: list[dict]) -> str:
    return f'''<footer class="site-foot">
  <div class="wrap foot-row">
    <p>© {YEAR} {esc(OWNER)}</p>
    <a href="{c.to('aviso-legal/')}">Aviso legal</a>
    {mail_link()}
  </div>
</footer>'''


def page(
    path: str,
    *,
    title: str,
    description: str,
    main: str,
    theme: str,
    section: str | None,
    apps: list[dict],
    lang: str = 'es',
    pre_main: str = '',
    alternates: dict | None = None,
    absolute: bool = False,
    favicon: str | None = None,
) -> None:
    here = path if (path == '' or path.endswith('/')) else (path.rsplit('/', 1)[0] + '/' if '/' in path else '')
    c = Ctx(here, absolute)
    base = SITE['baseUrl'].rstrip('/')
    canonical = base + '/' + (path if path.endswith('/') or path == '' else path)
    alt = ''
    if alternates:
        alt = ''.join(
            f'\n  <link rel="alternate" hreflang="{l}" href="{base}/{p}">' for l, p in alternates.items()
        )
    icon = favicon or 'static/brand/favicon-64.png'
    doc = f'''<!doctype html>
<html lang="{lang}">
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
  <meta name="theme-color" content="#141C3D">
  <link rel="icon" href="{c.to(icon)}">
  <link rel="apple-touch-icon" href="{c.to('static/brand/apple-touch-icon.png')}">
  <link rel="stylesheet" href="{c.to('static/site.css')}">
</head>
<body class="theme-{theme}">
<a class="skip" href="#contenido">Saltar al contenido</a>
{site_header(c, section)}
{pre_main}
<main id="contenido">
{main}
</main>
{site_footer(c, apps)}
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
    return {
        'app': app,
        'apps': [app],
        'games': json.loads((base / 'games.json').read_text('utf-8')),
        'privacy': json.loads((base / 'privacy.json').read_text('utf-8')),
        'terms': json.loads((base / 'terms.es.json').read_text('utf-8')),
        'faq': json.loads((base / 'faq.es.json').read_text('utf-8')),
    }


def build_home(d: dict) -> None:
    """Inicio: solo el carrusel con los iconos de los juegos de AllTheGames."""
    c = Ctx('')
    app, games = d['app'], d['games']
    accent = {cat['id']: cat['accent'] for cat in app['categories']}
    order = [cat['id'] for cat in app['categories']]
    # Intercaladas por categoría, para que los colores se vayan alternando.
    queues = {cid: [g for g in games if g['folder'] == cid] for cid in order}
    mixed = []
    while any(queues.values()):
        for cid in order:
            if queues[cid]:
                mixed.append(queues[cid].pop(0))

    def tile(g: dict, copy: bool) -> str:
        hidden = ' aria-hidden="true" tabindex="-1"' if copy else ''
        alt = '' if copy else esc(g['name'])
        return (
            f'<li style="--tile:{pastel(accent[g["folder"]], 0.14)}">'
            f'<a href="{c.to("apps/allthegames/")}#cat-{g["folder"]}" title="{esc(g["name"])}"{hidden}>'
            f'<img src="{c.to("static/apps/allthegames/games/" + g["slug"] + ".webp")}" alt="{alt}" width="96" height="96">'
            f'</a></li>'
        )

    # Varias filas, como una pared de ladrillos: cada fila va en un sentido.
    rows = SITE.get('carouselRows', 4)
    per = math.ceil(len(mixed) / rows)
    lines = []
    for r in range(rows):
        part = mixed[r * per:(r + 1) * per]
        # Cada fila empieza por otra categoría: los colores no se apilan en columnas.
        k = (r * 2) % max(1, len(part))
        part = part[k:] + part[:k]
        first = ''.join(tile(g, False) for g in part)
        # Tres copias: la fila llena también pantallas muy anchas al dar la vuelta.
        again = ''.join(tile(g, True) for g in part) * 2
        lines.append(f'<ul class="carousel-track">{first}{again}</ul>')
    main = f'''<h1 class="visually-hidden">{BRAND}</h1>
<section class="stage" aria-label="Juegos de AllTheGames">
  <div class="carousel" data-carousel>
    {''.join(lines)}
  </div>
  <div class="wrap carousel-bar">
    <button class="carousel-toggle" type="button" data-carousel-toggle aria-pressed="false">Pausar</button>
  </div>
</section>
<script>
  // El carrusel se mueve solo; este botón lo para y lo vuelve a mover.
  (function () {{
    var box = document.querySelector('[data-carousel]');
    var btn = document.querySelector('[data-carousel-toggle]');
    if (!box || !btn) return;
    btn.addEventListener('click', function () {{
      var paused = box.classList.toggle('is-paused');
      btn.setAttribute('aria-pressed', paused ? 'true' : 'false');
      btn.textContent = paused ? 'Reanudar' : 'Pausar';
    }});
  }})();
</script>'''
    page(
        '',
        title=f'{BRAND}',
        description=SITE['intro'],
        main=main,
        theme='brand',
        section='',
        apps=d['apps'],
    )


def build_legal_notice(d: dict) -> None:
    main = f'''<section class="page-head">
  <div class="wrap narrow">
    <h1>Aviso legal</h1>
  </div>
</section>
<section class="band band-tight">
  <div class="wrap narrow prose">
    <h2>Titular</h2>
    <p>Esta web y las apps que aparecen en ella son de {esc(OWNER)} ({esc(SITE['ownerNote'])}), que las publica con el nombre {BRAND}. Contacto: {mail_link()}.</p>
    <h2>Qué es esta web</h2>
    <p>Presenta las apps de {BRAND} y recoge su ayuda, su nota de privacidad y sus términos. Cada app tiene los suyos en su propia sección.</p>
    <h2>Datos y cookies</h2>
    <p>Esta web no usa cookies, ni analítica, ni formularios, y no carga nada de otros sitios. La aloja GitHub Pages: GitHub registra la dirección IP de las visitas por motivos de seguridad, como <a href="https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages">explica en su documentación</a>. Si me escribes, uso tu correo solo para contestarte.</p>
  </div>
</section>'''
    page('aviso-legal/', title=f'Aviso legal · {BRAND}', description=f'Titular y datos de la web de {BRAND}.',
         main=main, theme='brand', section=None, apps=d['apps'])


def build_404(d: dict) -> None:
    main = '''<section class="page-head">
  <div class="wrap narrow">
    <h1>Esta página no existe</h1>
    <p class="page-lead">Puede que la dirección esté mal escrita o que la página haya cambiado de sitio.</p>
    <p><a class="btn" href="/">Ir al inicio</a></p>
  </div>
</section>'''
    page('404.html', title=f'Página no encontrada · {BRAND}', description='Página no encontrada.', main=main,
         theme='brand', section=None, apps=d['apps'], absolute=True)


# ---------------------------------------------------------------------------
# AllTheGames

ATG_TABS = [
    ('apps/allthegames/', 'La app'),
    ('apps/allthegames/soporte/', 'Soporte'),
    ('apps/allthegames/privacidad/', 'Privacidad'),
    ('apps/allthegames/terminos/', 'Términos'),
]
PIZARRA = '#4A6076'
ATG_ICON = 'static/apps/allthegames/favicon.png'


def atg_nav(c: Ctx, current: str) -> str:
    tabs = ''.join(_tab(c, p, label, current) for p, label in ATG_TABS)
    return f'''<div class="appnav">
  <div class="wrap appnav-row">
    <a class="appnav-brand" href="{c.to('apps/allthegames/')}">
      <img src="{c.to('static/apps/allthegames/icon.webp')}" alt="" width="40" height="40">
      <span>AllTheGames</span>
    </a>
    <nav class="appnav-tabs" aria-label="AllTheGames">{tabs}</nav>
  </div>
</div>'''


def _tab(c: Ctx, p: str, label: str, current: str) -> str:
    cur = ' aria-current="page"' if p == current else ''
    return f'<a href="{c.to(p)}"{cur}>{label}</a>'


def build_atg_home(d: dict) -> None:
    app, games = d['app'], d['games']
    here = 'apps/allthegames/'
    c = Ctx(here)
    s = lambda p: c.to('static/apps/allthegames/' + p)
    facts = ''.join(f'<li>{esc(f)}</li>' for f in app['facts'])
    cats = []
    for cat in app['categories']:
        mine = [g for g in games if g['folder'] == cat['id']]
        tiles = ''.join(
            f'''<li class="game">
        <img src="{s('games/' + g['slug'] + '.webp')}" alt="" width="72" height="72" loading="lazy">
        <span>{esc(g['name'])}</span>
      </li>'''
            for g in mine
        )
        cats.append(f'''<section class="cat" aria-labelledby="cat-{cat['id']}">
    <h3 class="cat-band" id="cat-{cat['id']}" style="--fill:{band_fill(cat['accent'])};--lip:{band_lip(cat['accent'])}">
      <img src="{s('categories/' + cat['id'] + '.webp')}" alt="" width="44" height="44">
      <span>{esc(cat['label'])}</span>
      <span class="cat-count">{len(mine)} juegos</span>
    </h3>
    <ul class="games">
      {tiles}
    </ul>
  </section>''')
    store = (
        f'<a class="sticker" href="{esc(app["storeUrl"])}">Descargar en Google Play</a>'
        if app.get('storePublished') else '<p class="soon">Muy pronto en Google Play</p>'
    )
    main = f'''<section class="wrap atg-hero">
  <img class="atg-logo" src="{s('logo.webp')}" alt="" width="743" height="500">
  <div>
    <h1 class="visually-hidden">AllTheGames</h1>
    <p class="atg-lead">{esc(app['lead'])}</p>
    {store}
    <ul class="facts">{facts}</ul>
  </div>
</section>
<section class="wrap catalog" aria-labelledby="los-juegos">
  <h2 id="los-juegos" class="atg-h2">Los {len(games)} juegos</h2>
  {''.join(cats)}
</section>
<section class="wrap atg-help" aria-labelledby="atg-ayuda">
  <h2 id="atg-ayuda" class="atg-h2">Ayuda y textos legales</h2>
  <div class="help-row">
    <a class="sticker" href="soporte/">Soporte</a>
    <a class="sticker sticker-soft" href="privacidad/">Privacidad</a>
    <a class="sticker sticker-soft" href="terminos/">Términos de las compras</a>
  </div>
</section>'''
    page(here, title=f'AllTheGames · {BRAND}', description=app['lead'], main=main, theme='atg',
         section='apps/allthegames/', apps=d['apps'], pre_main=atg_nav(c, here), favicon=ATG_ICON)


def build_atg_support(d: dict) -> None:
    here = 'apps/allthegames/soporte/'
    c = Ctx(here)
    items = ''.join(
        f'''<details class="faq" id="{slug(q)}">
    <summary>{esc(q)}</summary>
    <p>{rich(a)}</p>
  </details>'''
        for q, a in d['faq']
    )
    main = f'''<div class="wrap narrow sheet">
  <h1 class="band-title" style="--fill:{band_fill('#C9692E')};--lip:{band_lip('#C9692E')}">Soporte</h1>
  <p class="atg-lead">Respuestas a lo que más se pregunta. Si no encuentras la tuya, escríbeme y te contesto.</p>
  {items}
  <section class="contact">
    <h2>Escribir a soporte</h2>
    <p>Cuéntame qué pasa, qué móvil usas y, si es un cobro, la fecha. Respondo desde {mail_link()}.</p>
    <a class="sticker" href="mailto:{esc(EMAIL)}?subject=AllTheGames%20%C2%B7%20Ayuda">Escribir un correo</a>
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
    page(here, title=f'Soporte de AllTheGames · {BRAND}', description='Preguntas frecuentes de AllTheGames y contacto.',
         main=main, theme='atg', section='apps/allthegames/', apps=d['apps'], pre_main=atg_nav(c, here), favicon=ATG_ICON)


def privacy_paths() -> dict:
    return {l: 'apps/allthegames/privacidad/' + ('' if l == 'es' else l + '/') for l in LANGS}


def privacy_main(d: dict, lang: str, here: str) -> str:
    c = Ctx(here)
    p = d['privacy'][lang]
    chrome = PRIVACY_CHROME[lang]
    paths = privacy_paths()
    sections = ''.join(
        f'<h2>{esc(p[f"s{i}Title"])}</h2>\n  <p>{rich(p[f"s{i}Body"])}</p>\n  ' for i in range(1, 11)
    )
    chips = []
    for l in LANGS:
        on = l == lang and here == paths[lang]
        cls = 'chip chip-on' if on else 'chip'
        cur = ' aria-current="page"' if on else ''
        chips.append(f'<a class="{cls}" href="{c.to(paths[l])}" hreflang="{l}" lang="{l}"{cur}>{LANG_NAMES[l]}</a>')
    title = p['title'][:1] + p['title'][1:].lower()
    return f'''<div class="wrap narrow sheet legal">
  <h1 class="band-title" style="--fill:{band_fill(PIZARRA)};--lip:{band_lip(PIZARRA)}">{esc(title)}</h1>
  <p class="meta">{esc(p['updated'].replace('{date}', p['date']))}</p>
  <nav class="langs" aria-label="{esc(chrome['langs'])}">{''.join(chips)}</nav>
  <p class="atg-lead">{rich(p['intro'])}</p>
  {sections}
  <p class="legal-links"><a href="{c.to('apps/allthegames/terminos/')}">{esc(chrome['terms'])}</a></p>
</div>'''


def build_atg_privacy(d: dict) -> None:
    version = d['app']['policyVersion']
    paths = privacy_paths()
    current = 'apps/allthegames/privacidad/'
    for lang in LANGS:
        p = d['privacy'][lang]
        title = p['title'][:1] + p['title'][1:].lower()
        here = paths[lang]
        page(here, title=f'{title} · AllTheGames', description=p['intro'], main=privacy_main(d, lang, here),
             theme='atg', section='apps/allthegames/', apps=d['apps'], lang=lang, alternates=paths,
             pre_main=atg_nav(Ctx(here), current), favicon=ATG_ICON)
    dated = f'apps/allthegames/privacidad/{version}/'
    page(dated, title=f'Privacidad ({version}) · AllTheGames', description=d['privacy']['es']['intro'],
         main=privacy_main(d, 'es', dated), theme='atg', section='apps/allthegames/', apps=d['apps'],
         pre_main=atg_nav(Ctx(dated), current), favicon=ATG_ICON)


def build_atg_terms(d: dict) -> None:
    t = d['terms']
    current = 'apps/allthegames/terminos/'
    for here in (current, f'apps/allthegames/terminos/{t["version"]}/'):
        c = Ctx(here)
        priv = f'<a href="{c.to("apps/allthegames/privacidad/")}">nota de privacidad</a>'
        sections = ''.join(
            f'<h2>{esc(h)}</h2>\n  <p>{rich(b, {"privacyLink": priv})}</p>\n  ' for h, b in t['sections']
        )
        main = f'''<div class="wrap narrow sheet legal">
  <h1 class="band-title" style="--fill:{band_fill(PIZARRA)};--lip:{band_lip(PIZARRA)}">{esc(t['title'])}</h1>
  <p class="meta">{esc(t['updated'])}</p>
  <p class="atg-lead">{esc(t['intro'])}</p>
  {sections}
</div>'''
        page(here, title=f'Términos de las compras · AllTheGames', description=t['intro'], main=main,
             theme='atg', section='apps/allthegames/', apps=d['apps'], pre_main=atg_nav(c, current), favicon=ATG_ICON)


# ---------------------------------------------------------------------------


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
    build_home(d)
    build_legal_notice(d)
    build_404(d)
    build_atg_home(d)
    build_atg_support(d)
    build_atg_privacy(d)
    build_atg_terms(d)
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
    print(f'Web generada en docs/ ({len(urls)} páginas).')


if __name__ == '__main__':
    build()
