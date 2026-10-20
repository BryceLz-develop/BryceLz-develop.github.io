#!/usr/bin/env python3
"""
Copia los términos de compra de la app (los 6 idiomas) a la web, para que la
app y la web digan siempre lo mismo.

    python3 tools/export-terms.py RUTA/A/AllTheGames/mobile

Lee legal/policy-manifest.json y legal/terminos*.html y escribe
content/apps/allthegames/terms.<idioma>.json.
"""
import html
import json
import re
import sys
from pathlib import Path

WEB_LANG = {'es': 'es', 'en': 'en', 'pt-BR': 'pt', 'it': 'it', 'fr': 'fr', 'de': 'de'}
OUT = Path(__file__).resolve().parent.parent / 'content' / 'apps' / 'allthegames'


def text(fragment: str, marks: dict) -> str:
    """Quita etiquetas: los enlaces al correo pasan a {email} y el de privacidad a {privacyLink}."""
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
    return re.sub(r'\s+', ' ', html.unescape(s)).strip()


def convert(src: Path, version: str) -> dict:
    body = src.read_text('utf-8')
    main = re.search(r'<main>(.*?)</main>', body, re.S).group(1)
    marks: dict = {}
    updated = text(re.search(r'<p class="meta">(.*?)</p>', main, re.S).group(1), marks)
    title = text(re.search(r'<h1>(.*?)</h1>', main, re.S).group(1), marks)
    after_h1 = main.split('</h1>', 1)[1]
    intro_html, rest = after_h1.split('<h2>', 1)
    intro = text(re.search(r'<p>(.*?)</p>', intro_html, re.S).group(1), marks)
    sections = []
    for h, p in re.findall(r'<h2>(.*?)</h2>\s*<p>(.*?)</p>', '<h2>' + rest, re.S):
        sections.append([text(h, marks), text(p, marks)])
    out = {'version': version, 'updated': updated, 'title': title, 'intro': intro, 'sections': sections}
    out.update(marks)
    return out


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit('Uso: python3 tools/export-terms.py RUTA/A/AllTheGames/mobile')
    app = Path(sys.argv[1])
    manifest = json.loads((app / 'legal' / 'policy-manifest.json').read_text('utf-8'))['terms']
    files = {'es': manifest['publicFile'], **manifest.get('translations', {})}
    for app_lang, rel in files.items():
        data = convert(app / rel, manifest['version'])
        dest = OUT / f'terms.{WEB_LANG[app_lang]}.json'
        dest.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', 'utf-8')
        print(f'{dest.name}: {len(data["sections"])} apartados')


if __name__ == '__main__':
    main()
