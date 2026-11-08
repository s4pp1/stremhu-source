// Static server for the isolated profiling image; no application backend.
const http = require('node:http')
const fs = require('node:fs')
const path = require('node:path')
const root = '/work/dist-g04'
const types = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.svg': 'image/svg+xml', '.png': 'image/png', '.woff2': 'font/woff2' }

http.createServer((request, response) => {
  const url = new URL(request.url, 'http://fixture.invalid')
  if (url.pathname === '/fixture/ready') {
    response.writeHead(200, { 'Content-Type': 'application/json' })
    response.end(JSON.stringify({ ready: fs.existsSync(path.join(root, '__cr_g04__/index.html')) }))
    return
  }
  const target = path.resolve(root, '.' + decodeURIComponent(url.pathname))
  if (!target.startsWith(root + path.sep)) {
    response.writeHead(404).end()
    return
  }
  fs.readFile(target, (error, data) => {
    if (error) {
      response.writeHead(404).end()
      return
    }
    response.writeHead(200, { 'Content-Type': types[path.extname(target)] || 'application/octet-stream', 'Cache-Control': 'no-store' })
    response.end(data)
  })
}).listen(8080, '0.0.0.0')
