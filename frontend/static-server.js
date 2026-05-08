// static-server.js — Servidor estático para frontend MetanoSRGAN
// Puerto 3000 expuesto por supervisor y enrutado por ingress hacia el preview URL
const http = require('http');
const fs = require('fs');
const path = require('path');
const url = require('url');

const PORT = parseInt(process.env.PORT || '3000', 10);
const HOST = process.env.HOST || '0.0.0.0';
const ROOT = __dirname;
const BACKEND = process.env.BACKEND_URL || 'http://localhost:8001';

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js':   'application/javascript; charset=utf-8',
  '.css':  'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.png':  'image/png',
  '.jpg':  'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.svg':  'image/svg+xml',
  '.ico':  'image/x-icon',
  '.woff': 'font/woff',
  '.woff2':'font/woff2',
  '.map':  'application/json',
};

function proxyToBackend(req, res) {
  const target = new URL(req.url, BACKEND);
  const opts = {
    hostname: target.hostname,
    port: target.port || 8001,
    path: target.pathname + (target.search || ''),
    method: req.method,
    headers: { ...req.headers, host: `${target.hostname}:${target.port || 8001}` },
  };
  const proxyReq = http.request(opts, (proxyRes) => {
    res.writeHead(proxyRes.statusCode || 502, proxyRes.headers);
    proxyRes.pipe(res, { end: true });
  });
  proxyReq.on('error', (err) => {
    res.writeHead(502, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ error: 'Backend no disponible', detail: err.message }));
  });
  req.pipe(proxyReq, { end: true });
}

function serveFile(res, filePath) {
  fs.readFile(filePath, (err, data) => {
    if (err) {
      res.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' });
      res.end('404 Not Found');
      return;
    }
    const ext = path.extname(filePath).toLowerCase();
    res.writeHead(200, {
      'Content-Type': MIME[ext] || 'application/octet-stream',
      'Cache-Control': 'no-cache',
    });
    res.end(data);
  });
}

const server = http.createServer((req, res) => {
  const parsed = url.parse(req.url);
  let pathname = decodeURIComponent(parsed.pathname || '/');

  // Proxy /api/* y /docs al backend FastAPI
  if (pathname.startsWith('/api/') || pathname === '/api' || pathname.startsWith('/docs') || pathname.startsWith('/redoc') || pathname.startsWith('/openapi')) {
    return proxyToBackend(req, res);
  }

  // Rutas SPA: /admin → admin.html, /login → login.html, /app → app.html
  if (pathname === '/admin' || pathname === '/admin/') {
    return serveFile(res, path.join(ROOT, 'admin.html'));
  }
  if (pathname === '/login' || pathname === '/login/') {
    return serveFile(res, path.join(ROOT, 'login.html'));
  }
  if (pathname === '/app' || pathname === '/app/') {
    const appHtml = path.join(ROOT, 'app.html');
    if (fs.existsSync(appHtml)) return serveFile(res, appHtml);
    return serveFile(res, path.join(ROOT, 'index.html'));
  }
  if (pathname === '/compliance' || pathname === '/compliance/') {
    return serveFile(res, path.join(ROOT, 'compliance.html'));
  }
  if (pathname === '/' || pathname === '') {
    // Auth-first: la raíz redirige a /login (el JS revisa localStorage)
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
    return res.end(
      '<!DOCTYPE html><html><head><meta charset="utf-8"/>' +
      '<title>MetanoSRGAN Elite</title>' +
      '<script>' +
      'const t=localStorage.getItem("msr_token");' +
      'const u=JSON.parse(localStorage.getItem("msr_user")||"{}");' +
      'window.location.replace(t?(u.role==="admin"?"/admin":"/app"):"/login");' +
      '</script></head><body style="background:#0a0e1a"></body></html>'
    );
  }

  // Servir archivo estático si existe
  let filePath = path.join(ROOT, pathname.replace(/^\/+/, ''));
  if (!filePath.startsWith(ROOT)) {
    res.writeHead(403); return res.end('Forbidden');
  }
  fs.stat(filePath, (err, stats) => {
    if (!err && stats.isFile()) return serveFile(res, filePath);
    if (!err && stats.isDirectory()) {
      return serveFile(res, path.join(filePath, 'index.html'));
    }
    // Fallback al index para SPA
    serveFile(res, path.join(ROOT, 'index.html'));
  });
});

server.listen(PORT, HOST, () => {
  console.log(`[static-server] MetanoSRGAN frontend en http://${HOST}:${PORT}`);
  console.log(`[static-server] Backend API: ${BACKEND}`);
});
