// Sirve la copia local de la web (docs-local/) en http://localhost:8080.
// Uso: node herramientas/servidor-local.js   (o doble clic en ver-web-local.bat)
const http = require('http');
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..', 'docs-local');
const PORT = Number(process.env.PORT) || 8080;
const TYPES = {
  '.html': 'text/html; charset=utf-8', '.css': 'text/css; charset=utf-8', '.js': 'text/javascript; charset=utf-8',
  '.json': 'application/json', '.svg': 'image/svg+xml', '.png': 'image/png', '.jpg': 'image/jpeg',
  '.webp': 'image/webp', '.ttf': 'font/ttf', '.woff2': 'font/woff2', '.txt': 'text/plain; charset=utf-8',
  '.xml': 'application/xml', '.ico': 'image/x-icon',
};

http.createServer((req, res) => {
  let p = decodeURIComponent(new URL(req.url, 'http://x').pathname);
  let file = path.join(ROOT, p);
  if (!file.startsWith(ROOT)) { res.writeHead(403); return res.end(); }
  if (fs.existsSync(file) && fs.statSync(file).isDirectory()) {
    if (!p.endsWith('/')) { res.writeHead(301, { Location: p + '/' }); return res.end(); }
    file = path.join(file, 'index.html');
  }
  if (!fs.existsSync(file)) {
    res.writeHead(404, { 'Content-Type': TYPES['.html'] });
    return fs.createReadStream(path.join(ROOT, '404.html')).pipe(res);
  }
  res.writeHead(200, { 'Content-Type': TYPES[path.extname(file).toLowerCase()] || 'application/octet-stream', 'Cache-Control': 'no-store' });
  fs.createReadStream(file).pipe(res);
}).listen(PORT, '127.0.0.1', () => console.log(`Copia local de la web en http://localhost:${PORT}  (Ctrl+C para parar)`));
