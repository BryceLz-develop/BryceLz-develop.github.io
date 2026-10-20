# Web de BryceLz

Web de BryceLz, el nombre con el que Brais López Arias publica sus apps.
De momento tiene dos apartados: Inicio (un carrusel con los juegos de
AllTheGames) y AllTheGames, con su ficha,
soporte, nota de privacidad (en 6 idiomas) y términos. Abajo, el aviso legal.

```
docs/                     ← lo que publica GitHub Pages (se genera, no se edita a mano)
content/site.json         ← marca, titular, correo, dirección de la web, AdMob
content/ui.json           ← todos los textos de la web en los 6 idiomas
content/apps/allthegames/ ← AllTheGames: ficha (app.json + app.i18n.json), juegos,
                            nombres traducidos (catalog-i18n.json), FAQ por idioma, legal
static/                   ← estilos, fuentes e imágenes
build.py                  ← genera docs/ a partir de content/ y static/
tools/export-privacy.ts   ← copia la nota de privacidad desde la app
tools/export-catalog.ts   ← copia de la app los nombres de juegos y categorías en 6 idiomas
```

## Idiomas

Español en la raíz y el resto en `/en/`, `/pt/`, `/it/`, `/fr/`, `/de/`. La privacidad mantiene
`/apps/allthegames/privacidad/<idioma>/` y los términos `/apps/allthegames/terminos/<idioma>/`.

Norma: la web no muestra el número de juegos (cambia cada vez que se añade uno) ni los
juegos que la app tiene ocultos (`"hidden": true` en `games.json`).

Cuando cambien los términos de la app:

```
python3 tools/export-terms.py RUTA/A/AllTheGames/mobile
```

Cuando cambien los juegos de la app:

```
npx tsx tools/export-catalog.ts RUTA/A/AllTheGames/mobile > content/apps/allthegames/catalog-i18n.json
```

## Publicar

La web está en `https://brycelz-develop.github.io` (repositorio
`BryceLz-develop/BryceLz-develop.github.io`, GitHub Pages desde la rama `main`,
carpeta raíz). La rama `fuente` guarda este proyecto; `main` solo lleva lo generado en `docs/`.

1. `python3 build.py` y commit de los cambios.
2. Doble clic en `herramientas/publicar-web.bat`: sube el proyecto a `fuente` y `docs/` a `main`.
   El resultado queda en `herramientas/publicar.log`.

## Después de publicar

- **Play Console** (ficha de AllTheGames): sitio web
  `https://BryceLz-develop.github.io` y política de privacidad
  `https://BryceLz-develop.github.io/apps/allthegames/privacidad/`.
- **AdMob**: el archivo `app-ads.txt` ya está en la raíz. AdMob lo comprueba
  solo en unas 24 horas desde que el sitio web de la ficha apunta aquí.
- **Google Sites**: deja la página antigua unas semanas con un enlace a la web
  nueva.

## Cambiar algo

1. Edita el texto en `content/` (son archivos JSON sencillos).
2. Ejecuta `python3 build.py`.
3. Haz commit y ejecuta `herramientas/publicar-web.bat`.

Cuando cambie la privacidad de la app:

```
npx tsx tools/export-privacy.ts RUTA/A/AllTheGames/mobile > content/apps/allthegames/privacy.json
```

y sube `policyVersion` en `content/apps/allthegames/app.json` a la fecha nueva:
la versión anterior queda guardada en `privacidad/AAAA-MM-DD/`.

## Dominio propio (más adelante)

1. Compra el dominio y en su DNS añade los registros de GitHub Pages
   (cuatro registros `A` y un `CNAME` para `www`, según la guía de GitHub).
2. En `content/site.json` añade `"domain": "tudominio.es"` y cambia `baseUrl`.
3. `python3 build.py`, sube los cambios y en Settings › Pages escribe el
   dominio y activa **Enforce HTTPS**.
4. Cambia el sitio web y la URL de privacidad en Play Console.

## Licencias

Las fuentes Bricolage Grotesque, Nunito Sans y la rotulación de AllTheGames
llevan licencia SIL Open Font License (`static/fonts/*-OFL.txt`).
