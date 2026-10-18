#!/usr/bin/env python3
"""
Genera la web en docs/ a partir de content/ y static/.

    python3 build.py

GitHub Pages publica la carpeta docs/ de la rama main. No hace falta instalar
nada: solo Python 3.
"""
import html
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONTENT = ROOT / 'content'
STATIC = ROOT / 'static'
OUT = ROOT / 'docs'

SITE = json.loads((CONTENT / 'site.json').read_text('utf-8'))
EMAIL = SITE['email']
OWNER = SITE['owner']

LANGS = ['es', 'en', 'fr', 'de', 'it', 'pt']
LANG_NAMES = {
    'es': 'Español', 'en': 'English', 'fr': 'Français',
    'de': 'Deutsch', 'it': 'Italiano', 'pt': 'Português',
}
# Texto de la web alrededor de la nota de privacidad, en cada idioma.
PRIVACY_CHROME = {
    'es': {'terms': 'Términos de las compras', 'langs': 'Otros idiomas', 'back': 'Volver a AllTheGames'},
    'en': {'terms': 'Purchase terms (in Spanish)', 'langs': 'Other languages', 'back': 'Back to AllTheGames'},
    'fr': {'terms': 'Conditions d’achat (en espagnol)', 'langs': 'Autres langues', 'back': 'Retour à AllTheGames'},
    'de': {'terms': 'Kaufbedingungen (auf Spanisch)', 'langs': 'Andere Sprachen', 'back': 'Zurück zu AllTheGames'},
    'it': {'terms': 'Termini di acquisto (in spagnolo)', 'langs': 'Altre lingue', 'back': 'Torna ad AllTheGames'},
    'pt': {'terms': 'Termos de compra (em espanhol)', 'langs': 'Outros idiomas', 'back': 'Voltar ao AllTheGames'},
}

# Enlaces dentro de los textos legales (solo nombres exactos).
AUTO_LINKS = {
    'rae-api.com': 'https://rae-api.com',
    'flagcdn.com': 'https://flagcdn.com',
    'aepd.es': 'https://www.aepd.es',
}

BAND_INK = '#2B2118'


def mix(a: str, b: str, t: float) -> str:
    pa, pb = int(a[1:], 16), int(b[1:], 16)
    ch = lambda n, s: (n >> s) & 255
    return '#' + ''.join(
        f'{round(ch(pa, s) + (ch(pb, s) - ch(pa, s)) * t):02X}' for s in (16, 8, 0)
    )


def band_fill(accent: str) -> str:
    """Igual que bandFill() de la app: el color hundido hacia la tinta."""
    return mix(accent, BAND_INK, 0.34)


def band_lip(accent: str) -> str:
    return mix(accent, BAND_INK, 0.58)


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


def rel(from_dir: str, to: str) -> str:
    """Ruta relativa entre dos rutas del sitio (funciona con o sin dominio)."""
    a = [p for p in from_dir.strip('/').split('/') if p]
    b = [p for p in to.strip('/').split('/') if p]
    i = 0
    while i < min(len(a), len(b)) and a[i] == b[i]:
        i += 1
    parts = ['..'] * (len(a) - i) + b[i:]
    path = '/'.join(parts)
    if to.endswith('/') and path:
        path += '/'
    return path or './'


def page(
    path: str,
    *,
    title: str,
    description: str,
    body: str,
    theme: str,
    lang: str = 'es',
    favicon: str = 'static/brais-favicon.png',
    alternates: dict | None = None,
) -> None:
    if path.endswith('/') or path == '':
        here = path
    else:
        here = path.rsplit('/', 1)[0] + '/' if '/' in path else ''
    css = rel(here, 'static/site.css')
    icon = rel(here, favicon)
    base = SITE['baseUrl'].rstrip('/')
    canonical = base + '/' + path.lstrip('/')
    alt = ''
    if alternates:
        alt = ''.join(
            f'\n  <link rel="alternate" hreflang="{l}" href="{base}/{p}">'
            for l, p in alternates.items()
        )
    doc = f'''<!doctype html>
<html lang="{lang}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(title)}</title>
  <meta name="description" content="{esc(description)}">
  <link rel="canonical" href="{canonical}">{alt}
  <link rel="icon" href="{icon}">
  <link rel="stylesheet" href="{css}">
</head>
<body class="theme-{theme}">
<a class="skip" href="#contenido">Saltar al contenido</a>
{body}
</body>
</html>
'''
    target = OUT / (path + 'index.html' if path == '' or path.endswith('/') else path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(doc, 'utf-8')


def shell_footer(here: str) -> str:
    return f'''<footer class="foot">
  <div class="wrap foot-row">
    <a href="{rel(here, '')}">{esc(OWNER)}</a>
    <a href="{rel(here, 'aviso-legal/')}">Aviso legal</a>
    {mail_link()}
  </div>
</footer>'''


# ---------------------------------------------------------------------------
# AllTheGames


def atg_load() -> dict:
    base = CONTENT / 'apps' / 'allthegames'
    return {
        'app': json.loads((base / 'app.json').read_text('utf-8')),
        'games': json.loads((base / 'games.json').read_text('utf-8')),
        'privacy': json.loads((base / 'privacy.json').read_text('utf-8')),
        'terms': json.loads((base / 'terms.es.json').read_text('utf-8')),
        'faq': json.loads((base / 'faq.es.json').read_text('utf-8')),
    }


def atg_top(here: str) -> str:
    return f'''<header class="atg-top">
  <div class="wrap atg-top-row">
    <a class="atg-brand" href="{rel(here, 'apps/allthegames/')}">
      <img src="{rel(here, 'static/apps/allthegames/icon.webp')}" alt="" width="36" height="36">
      <span>AllTheGames</span>
    </a>
    <a class="atg-owner" href="{rel(here, '')}">{esc(OWNER)}</a>
  </div>
</header>'''


def atg_store(app: dict) -> str:
    if app.get('storePublished'):
        return (
            f'<a class="sticker" href="{esc(app["storeUrl"])}">Descargar en Google Play</a>'
        )
    return '<p class="soon">Muy pronto en Google Play</p>'


def build_atg_home(d: dict) -> None:
    app, games = d['app'], d['games']
    here = 'apps/allthegames/'
    s = lambda p: rel(here, 'static/apps/allthegames/' + p)
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
        fill, lip = band_fill(cat['accent']), band_lip(cat['accent'])
        cats.append(f'''<section class="cat" aria-labelledby="cat-{cat['id']}">
    <h3 class="cat-band" id="cat-{cat['id']}" style="--fill:{fill};--lip:{lip}">
      <img src="{s('categories/' + cat['id'] + '.webp')}" alt="" width="44" height="44">
      <span class="cat-name">{esc(cat['label'])}</span>
      <span class="cat-count">{len(mine)} juegos</span>
    </h3>
    <ul class="games">
      {tiles}
    </ul>
  </section>''')
    body = f'''{atg_top(here)}
<main id="contenido">
  <section class="wrap atg-hero">
    <img class="atg-logo" src="{s('logo.webp')}" alt="AllTheGames" width="743" height="500">
    <div class="atg-hero-copy">
      <h1 class="visually-hidden">AllTheGames</h1>
      <p class="lead">{esc(app['lead'])}</p>
      {atg_store(app)}
      <ul class="facts">{facts}</ul>
    </div>
  </section>
  <section class="wrap catalog" aria-labelledby="los-juegos">
    <h2 id="los-juegos" class="atg-h2">Los {len(games)} juegos</h2>
    {''.join(cats)}
  </section>
  <section class="wrap help" aria-labelledby="ayuda">
    <h2 id="ayuda" class="atg-h2">Ayuda y textos legales</h2>
    <div class="help-row">
      <a class="sticker" href="soporte/">Soporte</a>
      <a class="sticker sticker-soft" href="privacidad/">Privacidad</a>
      <a class="sticker sticker-soft" href="terminos/">Términos de las compras</a>
    </div>
  </section>
</main>
{shell_footer(here)}'''
    page(
        here,
        title='AllTheGames: 60 juegos de siempre en una app',
        description=app['lead'],
        body=body,
        theme='atg',
        favicon='static/apps/allthegames/favicon.png',
    )


def build_atg_support(d: dict) -> None:
    here = 'apps/allthegames/soporte/'
    items = ''.join(
        f'''<details class="faq">
      <summary>{esc(q)}</summary>
      <p>{rich(a)}</p>
    </details>'''
        for q, a in d['faq']
    )
    body = f'''{atg_top(here)}
<main id="contenido" class="wrap narrow">
  <h1 class="band-title" style="--fill:{band_fill('#C9692E')};--lip:{band_lip('#C9692E')}">Soporte</h1>
  <p class="lead">Respuestas a lo que más se pregunta. Si no encuentras la tuya, escríbeme y te contesto.</p>
  {items}
  <section class="contact">
    <h2>Escribir a soporte</h2>
    <p>Cuéntame qué pasa, qué móvil usas y, si es un cobro, la fecha. Respondo desde {mail_link()}.</p>
    <a class="sticker" href="mailto:{esc(EMAIL)}?subject=AllTheGames%20%C2%B7%20Soporte">Escribir un correo</a>
  </section>
</main>
{shell_footer(here)}'''
    page(
        here,
        title='Soporte · AllTheGames',
        description='Respuestas a las preguntas frecuentes de AllTheGames y contacto.',
        body=body,
        theme='atg',
        favicon='static/apps/allthegames/favicon.png',
    )


PIZARRA = '#4A6076'


def privacy_paths() -> dict:
    return {l: 'apps/allthegames/privacidad/' + ('' if l == 'es' else l + '/') for l in LANGS}


def privacy_body(d: dict, lang: str, here: str) -> str:
    p = d['privacy'][lang]
    chrome = PRIVACY_CHROME[lang]
    paths = privacy_paths()
    sections = ''.join(
        f'<h2>{esc(p[f"s{i}Title"])}</h2>\n  <p>{rich(p[f"s{i}Body"])}</p>\n  '
        for i in range(1, 11)
    )
    chips = []
    for l in LANGS:
        on = l == lang and here == paths[lang]
        cls = 'chip chip-on' if on else 'chip'
        current = ' aria-current="page"' if on else ''
        chips.append(
            f'<a class="{cls}" href="{rel(here, paths[l])}" hreflang="{l}" lang="{l}"{current}>{LANG_NAMES[l]}</a>'
        )
    title = p['title'][:1] + p['title'][1:].lower()
    return f'''{atg_top(here)}
<main id="contenido" class="wrap narrow legal">
  <h1 class="band-title" style="--fill:{band_fill(PIZARRA)};--lip:{band_lip(PIZARRA)}">{esc(title)}</h1>
  <p class="meta">{esc(p['updated'].replace('{date}', p['date']))}</p>
  <nav class="langs" aria-label="{esc(chrome['langs'])}">{''.join(chips)}</nav>
  <p class="lead">{rich(p['intro'])}</p>
  {sections}
  <p class="legal-links"><a href="{rel(here, 'apps/allthegames/terminos/')}">{esc(chrome['terms'])}</a></p>
</main>
{shell_footer(here)}'''


def build_atg_privacy(d: dict) -> None:
    version = d['app']['policyVersion']
    paths = privacy_paths()
    for lang in LANGS:
        p = d['privacy'][lang]
        title = p['title'][:1] + p['title'][1:].lower()
        page(
            paths[lang],
            title=f'{title} · AllTheGames',
            description=p['intro'],
            body=privacy_body(d, lang, paths[lang]),
            theme='atg',
            lang=lang,
            favicon='static/apps/allthegames/favicon.png',
            alternates=paths,
        )
    # Copia fechada: lo que decía la nota en cada versión.
    dated = f'apps/allthegames/privacidad/{version}/'
    page(
        dated,
        title=f'Privacidad ({version}) · AllTheGames',
        description=d['privacy']['es']['intro'],
        body=privacy_body(d, 'es', dated),
        theme='atg',
        favicon='static/apps/allthegames/favicon.png',
    )


def terms_body(d: dict, here: str) -> str:
    t = d['terms']
    priv = f'<a href="{rel(here, "apps/allthegames/privacidad/")}">nota de privacidad</a>'
    sections = ''.join(
        f'<h2>{esc(h)}</h2>\n  <p>{rich(b, {"privacyLink": priv})}</p>\n  '
        for h, b in t['sections']
    )
    return f'''{atg_top(here)}
<main id="contenido" class="wrap narrow legal">
  <h1 class="band-title" style="--fill:{band_fill(PIZARRA)};--lip:{band_lip(PIZARRA)}">{esc(t['title'])}</h1>
  <p class="meta">{esc(t['updated'])}</p>
  <p class="lead">{esc(t['intro'])}</p>
  {sections}
</main>
{shell_footer(here)}'''


def build_atg_terms(d: dict) -> None:
    t = d['terms']
    for path in ('apps/allthegames/terminos/', f'apps/allthegames/terminos/{t["version"]}/'):
        page(
            path,
            title='Términos de las compras · AllTheGames',
            description=t['intro'],
            body=terms_body(d, path),
            theme='atg',
            favicon='static/apps/allthegames/favicon.png',
        )


# ---------------------------------------------------------------------------
# Páginas propias


def build_home(d: dict) -> None:
    app = d['app']
    here = ''
    s = lambda p: 'static/apps/allthegames/' + p
    body = f'''<main id="contenido">
  <section class="wrap intro">
    <h1 class="name">{esc(OWNER)}</h1>
    <p class="intro-text">{esc(SITE['intro'])}</p>
    <p class="intro-mail">{mail_link()}</p>
  </section>
  <section class="wrap apps" aria-labelledby="apps">
    <h2 id="apps" class="shell-h2">Mis apps</h2>
    <article class="appcard">
      <a class="appcard-art" href="apps/allthegames/" tabindex="-1" aria-hidden="true">
        <img src="{s('logo.webp')}" alt="" width="743" height="500">
      </a>
      <div class="appcard-copy">
        <h3><a href="apps/allthegames/">AllTheGames</a></h3>
        <p>{esc(app['lead'])}</p>
        <p class="appcard-meta">Para Android. {'Ya está en Google Play.' if app.get('storePublished') else 'Muy pronto en Google Play.'}</p>
        <div class="appcard-links">
          <a class="sticker" href="apps/allthegames/">Ver la app</a>
          <a class="sticker sticker-soft" href="apps/allthegames/soporte/">Soporte</a>
          <a class="sticker sticker-soft" href="apps/allthegames/privacidad/">Privacidad</a>
        </div>
      </div>
    </article>
  </section>
</main>
{shell_footer(here)}'''
    page(
        '',
        title=f'{OWNER} · Apps para Android',
        description=SITE['intro'],
        body=body,
        theme='shell',
    )


def build_legal_notice() -> None:
    here = 'aviso-legal/'
    body = f'''<header class="shell-top"><div class="wrap"><a href="../">{esc(OWNER)}</a></div></header>
<main id="contenido" class="wrap narrow">
  <h1 class="shell-h1">Aviso legal</h1>
  <h2>Titular</h2>
  <p>Esta web y las apps que aparecen en ella son de {esc(OWNER)} ({esc(SITE['ownerNote'])}). Contacto: {mail_link()}.</p>
  <h2>Qué es esta web</h2>
  <p>Presenta las apps que publico y recoge su ayuda, su nota de privacidad y sus términos. Cada app tiene los suyos en su propia sección.</p>
  <h2>Datos y cookies</h2>
  <p>Esta web no usa cookies, ni analítica, ni formularios, y no carga nada de otros sitios. La aloja GitHub Pages: GitHub registra la dirección IP de las visitas por motivos de seguridad, según <a href="https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages">explica en su documentación</a>. Si me escribes, uso tu correo solo para contestarte.</p>
</main>
{shell_footer(here)}'''
    page(here, title=f'Aviso legal · {OWNER}', description='Titular y datos de esta web.', body=body, theme='shell')


def build_404() -> None:
    body = f'''<main id="contenido" class="wrap narrow notfound">
  <h1 class="shell-h1">Esta página no existe</h1>
  <p>Puede que la dirección esté mal escrita o que la página haya cambiado de sitio.</p>
  <p><a href="/">Ir al inicio</a></p>
</main>'''
    # 404 se sirve desde cualquier ruta: rutas absolutas.
    doc_path = OUT / '404.html'
    page('404.html', title='Página no encontrada', description='Página no encontrada.', body=body, theme='shell')
    text = doc_path.read_text('utf-8')
    text = text.replace('href="static/site.css"', 'href="/static/site.css"').replace(
        'href="static/brais-favicon.png"', 'href="/static/brais-favicon.png"'
    )
    doc_path.write_text(text, 'utf-8')


def build() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    shutil.copytree(STATIC, OUT / 'static')
    (OUT / '.nojekyll').write_text('', 'utf-8')
    (OUT / 'app-ads.txt').write_text(
        f'google.com, {SITE["admobPublisher"]}, DIRECT, f08c47fec0942fa0\n', 'utf-8'
    )
    (OUT / 'robots.txt').write_text('User-agent: *\nAllow: /\n', 'utf-8')
    if SITE.get('domain'):
        (OUT / 'CNAME').write_text(SITE['domain'] + '\n', 'utf-8')
    d = atg_load()
    build_home(d)
    build_legal_notice()
    build_404()
    build_atg_home(d)
    build_atg_support(d)
    build_atg_privacy(d)
    build_atg_terms(d)
    count = sum(1 for _ in OUT.rglob('index.html'))
    print(f'Web generada en docs/ ({count} páginas).')


if __name__ == '__main__':
    build()
