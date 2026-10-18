# Web de Brais López Arias

Web profesional con las apps que publico. Cada app tiene su ficha, su página de
soporte, su nota de privacidad y sus términos.

```
docs/                     ← lo que publica GitHub Pages (se genera, no se edita a mano)
content/site.json         ← nombre, correo, dirección de la web, AdMob
content/apps/allthegames/ ← textos de AllTheGames (ficha, juegos, soporte, legal)
static/                   ← estilos, fuentes e imágenes
build.py                  ← genera docs/ a partir de content/ y static/
tools/export-privacy.ts   ← copia la nota de privacidad desde la app
```

## Publicar por primera vez

1. En GitHub, crea un repositorio público llamado exactamente
   `TU_USUARIO.github.io` (con tu nombre de usuario de GitHub).
2. En `content/site.json`, cambia `baseUrl` a `https://TU_USUARIO.github.io` y
   ejecuta `python3 build.py`.
3. Sube este proyecto a ese repositorio (rama `main`).
4. En el repositorio: **Settings › Pages › Build and deployment**, elige
   **Deploy from a branch**, rama `main` y carpeta `/docs`. Guarda.
5. En un par de minutos la web está en `https://TU_USUARIO.github.io`.

## Después de publicar

- **Play Console** (ficha de AllTheGames): sitio web
  `https://TU_USUARIO.github.io` y política de privacidad
  `https://TU_USUARIO.github.io/apps/allthegames/privacidad/`.
- **AdMob**: el archivo `app-ads.txt` ya está en la raíz. AdMob lo comprueba
  solo en unas 24 horas desde que el sitio web de la ficha apunta aquí.
- **Google Sites**: deja la página antigua unas semanas con un enlace a la web
  nueva.

## Cambiar algo

1. Edita el texto en `content/` (son archivos JSON sencillos).
2. Ejecuta `python3 build.py`.
3. Sube los cambios. GitHub Pages publica solo.

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

Las fuentes Nunito Sans y la rotulación de AllTheGames llevan licencia SIL Open
Font License (`static/fonts/*-OFL.txt`).
