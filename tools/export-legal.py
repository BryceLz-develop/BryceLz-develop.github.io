#!/usr/bin/env python3
"""
Copia a la web la privacidad y los términos de una app hecha con la plantilla,
tal cual salen de la app (no se reescriben):

    python3 tools/export-legal.py RUTA/A/LaApp allthepartygames

- Privacidad: `mobile/legal/privacy.json` (la que compone `npm run legal:build`
  en los 6 idiomas) → `content/apps/<slug>/privacy.<idioma>.json`.
- Términos: `mobile/legal/terminos*.html` (los de `policy-manifest.json`)
  → `content/apps/<slug>/terms.<idioma>.json`.
- Apunta las versiones en `content/apps/<slug>/app.json` si existe.
"""
import importlib.util
import json
import sys
from pathlib import Path

WEB = Path(__file__).resolve().parent.parent
LANGS = ['es', 'en', 'pt', 'it', 'fr', 'de']
APP_LANG = {'es': 'es', 'en': 'en', 'pt': 'pt-BR', 'it': 'it', 'fr': 'fr', 'de': 'de'}
EMAIL = 'bryce.lz.as@gmail.com'

spec = importlib.util.spec_from_file_location('export_party', WEB / 'tools' / 'export-party.py')
party = importlib.util.module_from_spec(spec)
spec.loader.exec_module(party)


def title_case(s: str) -> str:
    s = s.strip()
    return s[:1] + s[1:].lower() if s.isupper() else s


def main() -> None:
    if len(sys.argv) < 3:
        sys.exit('Uso: python3 tools/export-legal.py RUTA/A/LaApp slug')
    root, slug = Path(sys.argv[1]), sys.argv[2]
    mobile = root / 'mobile'
    out = WEB / 'content' / 'apps' / slug
    out.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((mobile / 'legal' / 'policy-manifest.json').read_text('utf-8'))
    priv = json.loads((mobile / 'legal' / 'privacy.json').read_text('utf-8'))
    for l in LANGS:
        p = priv[l]
        secs = p['sections']
        intro = next((s['body'] for s in secs if s.get('title') is None), '')
        page = {
            'version': priv['version'],
            'updated': p['updated'],
            'title': title_case(p['title']),
            'intro': intro.replace(EMAIL, '{email}'),
            'sections': [[s['title'], s['body'].replace(EMAIL, '{email}')] for s in secs if s.get('title')],
        }
        (out / f'privacy.{l}.json').write_text(json.dumps(page, ensure_ascii=False, indent=2) + '\n', 'utf-8')
        files = {'es': manifest['terms']['publicFile'], **manifest['terms'].get('translations', {})}
        terms = party.legal_page(mobile / files[APP_LANG[l]], manifest['terms']['version'])
        (out / f'terms.{l}.json').write_text(json.dumps(terms, ensure_ascii=False, indent=2) + '\n', 'utf-8')
    info = out / 'app.json'
    if info.exists():
        d = json.loads(info.read_text('utf-8'))
        d['privacyVersion'] = priv['version']
        d['termsVersion'] = manifest['terms']['version']
        info.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n', 'utf-8')
    print(f'{slug}: privacidad {priv["version"]} y términos {manifest["terms"]["version"]} en 6 idiomas.')


if __name__ == '__main__':
    main()
