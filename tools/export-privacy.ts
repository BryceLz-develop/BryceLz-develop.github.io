/**
 * Copia la nota de privacidad de la app (los 6 idiomas) a la web, para que
 * la app y la web digan siempre lo mismo.
 *
 *   npx tsx tools/export-privacy.ts RUTA/A/AllTheGames/mobile > content/apps/allthegames/privacy.json
 */
import path from 'node:path';

const appDir = process.argv[2];
if (!appDir) {
  console.error('Uso: npx tsx tools/export-privacy.ts RUTA/A/AllTheGames/mobile');
  process.exit(1);
}
async function main(): Promise<void> {
  const messages = await import(path.resolve(appDir, 'src/i18n/messages.ts'));
  const out: Record<string, unknown> = {};
  for (const lang of ['de', 'en', 'es', 'fr', 'it', 'pt']) {
    out[lang] = messages[lang].privacy;
  }
  console.log(JSON.stringify(out, null, 1));
}

void main();
