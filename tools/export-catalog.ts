/**
 * Copia de la app los nombres y descripciones de los juegos y las categorías
 * en los 6 idiomas, para que la web use exactamente los textos de la app.
 *
 *   npx tsx tools/export-catalog.ts RUTA/A/AllTheGames/mobile > content/apps/allthegames/catalog-i18n.json
 */
import fs from 'node:fs';
import path from 'node:path';

const appDir = process.argv[2];
if (!appDir) {
  console.error('Uso: npx tsx tools/export-catalog.ts RUTA/A/AllTheGames/mobile');
  process.exit(1);
}
async function main(): Promise<void> {
  const { tx } = await import(path.resolve(appDir, 'src/i18n/tx.ts'));
  const messages = await import(path.resolve(appDir, 'src/i18n/messages.ts'));
  const games = JSON.parse(
    fs.readFileSync(path.resolve(__dirname, '../content/apps/allthegames/games.json'), 'utf-8'),
  );
  const out: Record<string, unknown> = {};
  for (const lang of ['en', 'pt', 'it', 'fr', 'de']) {
    const g: Record<string, { name: string; short: string }> = {};
    for (const game of games) g[game.slug] = { name: tx(lang, game.name), short: tx(lang, game.short) };
    out[lang] = { folders: messages[lang].folders, games: g };
  }
  console.log(JSON.stringify(out, null, 1));
}

void main();
