/**
 * Copia de la app el nombre y las descripciones (corta y larga) de cada juego
 * de AllTheGames en los 6 idiomas, para su ficha en la web.
 *
 *   npx tsx tools/export-games.mts RUTA/A/AllTheGames/mobile content/apps/allthegames/games.json > content/apps/allthegames/games-text.json
 *
 * Solo necesita src/api/client.ts y los archivos de src/i18n/ de la app.
 */
import fs from 'node:fs';
import path from 'node:path';

const [appDir, gamesJson] = process.argv.slice(2);
if (!appDir || !gamesJson) {
  console.error('Uso: npx tsx tools/export-games.mts RUTA/A/AllTheGames/mobile content/apps/allthegames/games.json');
  process.exit(1);
}
const client = await import(path.resolve(appDir, 'src/api/client.ts'));
const { tx } = await import(path.resolve(appDir, 'src/i18n/tx.ts'));
const games = JSON.parse(fs.readFileSync(gamesJson, 'utf-8'));
const out: Record<string, Record<string, { name: string; short: string; long: string }>> = {};
const missing: string[] = [];
for (const lang of ['es', 'en', 'pt', 'it', 'fr', 'de']) {
  out[lang] = {};
  for (const g of games) {
    const s = client.catalogGameBySlug(g.slug);
    if (!s) {
      if (lang === 'es') missing.push(g.slug);
      continue;
    }
    out[lang][g.slug] = {
      name: tx(lang, s.name),
      short: tx(lang, s.shortDescription),
      long: tx(lang, s.longDescription ?? s.shortDescription),
    };
  }
}
const all = (await client.fetchGames()).filter((x: { hidden?: boolean }) => !x.hidden).map((x: { slug: string }) => x.slug);
console.error('En la web y no en la app:', missing, '| En la app y no en la web:', all.filter((s: string) => !games.some((g: { slug: string }) => g.slug === s)));
console.log(JSON.stringify(out, null, 1));
