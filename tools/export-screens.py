#!/usr/bin/env python3
"""
Copia las capturas de Google Play de la app (una tanda por idioma) a la web,
convertidas a WebP y más pequeñas, para la galería de la ficha de AllTheGames.

    python3 tools/export-screens.py RUTA/A/AllTheGames/play-store/capturas-1.2

Necesita Pillow (pip install pillow). Cada idioma está en su subcarpeta
(es-ES, en-US, pt-BR, it-IT, fr-FR, de-DE).
Solo copia las capturas (v1.2-NN-nombre.png), no el gráfico de funciones.
"""
import re
import shutil
import sys
from pathlib import Path

from PIL import Image

STORE_DIR = {'es': 'es-ES', 'en': 'en-US', 'pt': 'pt-BR', 'it': 'it-IT', 'fr': 'fr-FR', 'de': 'de-DE'}
WIDTH = 540  # la mitad de 1080: nítidas en la galería y mucho más ligeras
OUT = Path(__file__).resolve().parent.parent / 'static' / 'apps' / 'allthegames' / 'screens'


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit('Uso: python3 tools/export-screens.py RUTA/A/AllTheGames/play-store/capturas-1.2')
    src = Path(sys.argv[1])
    if OUT.exists():
        shutil.rmtree(OUT)
    for lang, sub in STORE_DIR.items():
        dest = OUT / lang
        dest.mkdir(parents=True)
        files = sorted(f for f in (src / sub).glob('*.png') if re.match(r'v[\d.]+-\d\d-[a-z]+\.png$', f.name))
        for f in files:
            name = re.sub(r'^v[\d.]+-', '', f.stem)  # 01-inicio
            im = Image.open(f).convert('RGB')
            im = im.resize((WIDTH, round(im.height * WIDTH / im.width)), Image.LANCZOS)
            im.save(dest / f'{name}.webp', 'WEBP', quality=82, method=6)
        print(f'{lang}: {len(files)} capturas')


if __name__ == '__main__':
    main()
