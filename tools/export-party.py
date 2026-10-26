#!/usr/bin/env python3
"""
Copia de AllThePartyGames a la web todo lo que usa su sección, tal cual sale
de la app: presentación y preguntas frecuentes, juegos y categorías con sus
nombres traducidos, aviso de edad, privacidad y términos (6 idiomas), imágenes
y fuentes de la piel After Dark.

    python3 tools/export-party.py RUTA/A/AllThePartyGames

Necesita Pillow (pip install pillow). Fuentes de cada dato: play-store/PARA-LA-WEB.md
del repositorio de la app.
"""
import html
import json
import re
import shutil
import sys
from pathlib import Path

from PIL import Image

WEB = Path(__file__).resolve().parent.parent
CONTENT = WEB / 'content' / 'apps' / 'allthepartygames'
STATIC = WEB / 'static' / 'apps' / 'allthepartygames'
FONTS = WEB / 'static' / 'fonts'
LANGS = ['es', 'en', 'pt', 'it', 'fr', 'de']
APP_LANG = {'es': 'es', 'en': 'en', 'pt': 'pt-BR', 'it': 'it', 'fr': 'fr', 'de': 'de'}
TS_LANG = {'es': 'Es', 'en': 'En', 'pt': 'Pt', 'it': 'It', 'fr': 'Fr', 'de': 'De'}
CATS = ['preguntas', 'retos', 'adivinar', 'cartas']  # Favoritos y En equipos son carpetas de la app, no categorías


def ts_object(text: str) -> dict:
    """Un objeto literal de TypeScript con claves y textos entre comillas dobles → dict."""
    body = text[text.index('= {') + 2:]
    body = body[:body.rindex('}') + 1]
    return json.loads(re.sub(r',(\s*[}\]])', r'\1', body))


def ts_string(block: str, key: str) -> str:
    m = re.search(rf"\b{key}:\s*(['\"])(.*?)(?<!\\)\1", block, re.S)
    return m.group(2).replace("\\'", "'") if m else ''


# --- Legales (mismo formato que tools/export-terms.py) ----------------------

def legal_text(fragment: str, marks: dict) -> str:
    def link(m):
        href, inner = m.group(1), re.sub(r'<[^>]+>', '', m.group(2)).strip()
        if href.startswith('mailto:'):
            return '{email}'
        if 'privacidad' in href:
            marks['privacyLinkText'] = html.unescape(inner)
            return '{privacyLink}'
        return inner
    s = re.sub(r'<a\s+[^>]*href="([^"]+)"[^>]*>(.*?)</a>', link, fragment, flags=re.S)
    s = re.sub(r'<[^>]+>', '', s)
    return re.sub(r'[ \t\r\n]+', ' ', html.unescape(s)).strip(' \t\r\n')


def legal_page(src: Path, version: str) -> dict:
    main = re.search(r'<main>(.*?)</main>', src.read_text('utf-8'), re.S).group(1)
    marks: dict = {}
    updated = legal_text(re.search(r'<p class="meta">(.*?)</p>', main, re.S).group(1), marks)
    title = legal_text(re.search(r'<h1>(.*?)</h1>', main, re.S).group(1), marks)
    intro_html, rest = main.split('</h1>', 1)[1].split('<h2>', 1)
    intro = legal_text(re.search(r'<p>(.*?)</p>', intro_html, re.S).group(1), marks)
    sections = [[legal_text(h, marks), legal_text(p, marks)]
                for h, p in re.findall(r'<h2>(.*?)</h2>\s*<p>(.*?)</p>', '<h2>' + rest, re.S)]
    out = {'version': version, 'updated': updated, 'title': title, 'intro': intro, 'sections': sections}
    out.update(marks)
    return out


def webp(src: Path, dest: Path, width: int, quality: int = 85) -> None:
    im = Image.open(src).convert('RGBA')
    if im.width > width:
        im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
    dest.parent.mkdir(parents=True, exist_ok=True)
    im.save(dest, 'WEBP', quality=quality, method=6)


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit('Uso: python3 tools/export-party.py RUTA/A/AllThePartyGames')
    root = Path(sys.argv[1])
    mobile = root / 'mobile'
    CONTENT.mkdir(parents=True, exist_ok=True)

    # Juegos y categorías
    client = (mobile / 'src' / 'api' / 'client.ts').read_text('utf-8')
    block = client[client.index('const LOCAL_CATALOG'):]
    games = []
    for m in re.finditer(r"name:\s*'([^']+)',\s*slug:\s*'([^']+)'.*?gameType:\s*'([^']+)'(.*?)\n  \}", block, re.S):
        if 'hidden: true' in m.group(4):
            continue
        body = m.group(0)
        short = re.search(r"shortDescription:\s*'([^']*)'", body)
        long_ = re.search(r"longDescription:\s*'([^']*)'", body)
        games.append({'slug': m.group(2), 'name': m.group(1), 'folder': m.group(3),
                      'short': short.group(1) if short else '',
                      'long': long_.group(1) if long_ else (short.group(1) if short else '')})
    folders = (mobile / 'src' / 'games' / 'catalogFolders.ts').read_text('utf-8')
    cats = []
    for m in re.finditer(r"\{ id: '([a-z]+)', label: '([^']+)', accent: '(#[0-9A-Fa-f]{6})' \}", folders):
        if m.group(1) in CATS:
            cats.append({'id': m.group(1), 'label': m.group(2), 'accent': m.group(3)})
    phrases = ts_object((mobile / 'src' / 'i18n' / 'partyCatalogPhrases.ts').read_text('utf-8'))
    datos = json.loads((root / 'play-store' / 'web' / 'web-datos.json').read_text('utf-8'))
    manifest = json.loads((mobile / 'legal' / 'policy-manifest.json').read_text('utf-8'))

    app = json.loads((mobile / 'app.json').read_text('utf-8'))['expo']
    info = {
        'slug': 'allthepartygames', 'name': app['name'], 'package': app['android']['package'],
        'version': app['version'], 'storePublished': False,
        'storeUrl': f"https://play.google.com/store/apps/details?id={app['android']['package']}",
        'privacyVersion': manifest['privacy']['version'], 'termsVersion': manifest['terms']['version'],
        'categories': cats, 'games': [{k: g[k] for k in ('slug', 'name', 'folder')} for g in games],
    }
    old = CONTENT / 'app.json'
    if old.exists():  # lo que se decide en la web (publicada o no) no se pisa
        info['storePublished'] = json.loads(old.read_text('utf-8')).get('storePublished', False)
    old.write_text(json.dumps(info, ensure_ascii=False, indent=2) + '\n', 'utf-8')

    i18n = {}
    for l in LANGS:
        d = datos[APP_LANG[l]]
        ts = (mobile / 'src' / 'i18n' / f'party{TS_LANG[l]}.ts').read_text('utf-8')
        gate = ts[ts.index('ageGate'):]
        gate = gate[:gate.index('}')]
        tr = (lambda s: s) if l == 'es' else (lambda s, t=phrases[l]: t.get(s, s))
        i18n[l] = {
            'tagline': d['tagline'], 'perks': d['perks'],
            'faq': [[q['q'], q['a']] for q in d['faq']],
            'ageGate': {k: ts_string(gate, k) for k in ('title', 'body', 'drinkResponsibly')},
            'games': {g['slug']: tr(g['name']) for g in games},
            # Descripciones de cada juego (las de la app), para su ficha en la web.
            'gameText': {g['slug']: {'short': tr(g['short']), 'long': tr(g['long'])} for g in games},
            'categories': {c['id']: tr(c['label']) for c in cats},
        }
        for kind in ('privacy', 'terms'):
            files = {'es': manifest[kind]['publicFile'], **manifest[kind].get('translations', {})}
            page = legal_page(mobile / files[APP_LANG[l]], manifest[kind]['version'])
            (CONTENT / f'{kind}.{l}.json').write_text(json.dumps(page, ensure_ascii=False, indent=2) + '\n', 'utf-8')
    (CONTENT / 'i18n.json').write_text(json.dumps(i18n, ensure_ascii=False, indent=1) + '\n', 'utf-8')

    # Imágenes
    if STATIC.exists():
        shutil.rmtree(STATIC)
    a = mobile / 'assets' / 'party'
    for g in games:
        webp(a / 'games' / g['slug'] / 'icon.png', STATIC / 'games' / f"{g['slug']}.webp", 192)
    for c in cats:
        webp(a / 'categories' / f"icon-{c['id']}.webp", STATIC / 'categories' / f"{c['id']}.webp", 96)
    webp(a / 'brand' / 'logo.png', STATIC / 'logo.webp', 760)
    webp(a / 'brand' / 'icon.png', STATIC / 'icon.webp', 384)
    icon = Image.open(a / 'brand' / 'icon.png').convert('RGB')
    icon.resize((64, 64), Image.LANCZOS).save(STATIC / 'favicon.png')
    icon.resize((180, 180), Image.LANCZOS).save(STATIC / 'apple-touch-icon.png')

    # Fuentes de After Dark (SIL OFL 1.1)
    gf = mobile / 'node_modules' / '@expo-google-fonts'
    FONTS.mkdir(parents=True, exist_ok=True)
    shutil.copy(gf / 'lilita-one' / '400Regular' / 'LilitaOne_400Regular.ttf', FONTS / 'lilita-one.ttf')
    shutil.copy(gf / 'lilita-one' / 'LICENSE_FONT', FONTS / 'LilitaOne-OFL.txt')
    for w in ('400Regular', '800ExtraBold'):
        shutil.copy(gf / 'nunito' / w / f'Nunito_{w}.ttf', FONTS / f'nunito-{w}.ttf')
    lic = gf / 'nunito' / 'LICENSE_FONT'
    if lic.exists():
        shutil.copy(lic, FONTS / 'Nunito-OFL.txt')

    print(f'{len(games)} juegos, {len(cats)} categorías, legales y imágenes copiados.')


if __name__ == '__main__':
    main()
