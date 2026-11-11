// Only synthetic sites in the task-owned, Docker --internal network.
const { chromium, request } = require('/fixture/node_modules/playwright')
let stage = 'initialization'

async function main() {
  const profile = process.env.CR_BROWSER_PROFILE
  const base = profile === 'proxy' ? 'https://proxy.fixture.invalid' : 'https://local.fixture.invalid:8443'
  const foreign = 'https://foreign.fixture.invalid:8443'
  const api = await request.newContext({ ignoreHTTPSErrors: true })
  const deadline = Date.now() + 60000
  stage = 'readiness'
  while (true) {
    try {
      if ((await api.get(base + '/fixture/ready')).status() === 200) break
    } catch {}
    if (Date.now() > deadline) throw new Error('Synthetic backend readiness timeout')
    await new Promise((resolve) => setTimeout(resolve, 100))
  }
  stage = 'browser-launch'
  const browser = await chromium.launch({ headless: true })
  const results = []
  try {
    for (let repeat = 0; repeat < 5; repeat++) {
      await api.post(base + '/fixture/next')
      const context = await browser.newContext({ ignoreHTTPSErrors: true })
      const page = await context.newPage()
      stage = 'same-origin-page'
      await page.goto(base + '/fixture/page')
      stage = 'login'
      const login = await page.evaluate(async () => (await fetch('/api/auth/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username: 'fixture', password: 'synthetic-browser-password' }) })).status)
      const cookies = await context.cookies(base)
      const session = cookies.find((cookie) => cookie.name === 'stremhu.source')
      const flags = session ? { secure: session.secure, httpOnly: session.httpOnly, sameSite: session.sameSite } : null
      const update = await page.evaluate(async () => (await fetch('/api/me/', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ torrentSeed: 7 }) })).status)
      stage = 'foreign-page'
      await page.goto(foreign + '/fixture/page')
      stage = 'foreign-form'
      const response = page.waitForResponse((value) => value.url() === base + '/api/auth/logout' && value.request().method() === 'POST')
      await page.evaluate((action) => {
        const form = document.createElement('form')
        form.method = 'POST'
        form.action = action
        document.body.appendChild(form)
        form.submit()
      }, base + '/api/auth/logout')
      const foreignPost = (await response).status()
      stage = 'native-requests'
      const native = await api.post(base + '/api/auth/login', { data: { username: 'fixture', password: 'synthetic-browser-password' } })
      const spoofed = await api.post(base + '/api/auth/logout', { headers: { Origin: foreign, 'X-Forwarded-Host': 'foreign.fixture.invalid' } })
      const nullOrigin = await api.post(base + '/api/auth/logout', { headers: { Origin: 'null' } })
      let explicitAlternate = null
      if (process.env.CR_BROWSER_CANDIDATE === 'true' || process.env.CR_BROWSER_PRODUCTION === 'true') {
        stage = 'explicit-alternate'
        await page.goto('https://alternate.fixture.invalid:8443/fixture/page')
        explicitAlternate = await page.evaluate(async () => (await fetch('/api/auth/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username: 'fixture', password: 'synthetic-browser-password' }) })).status)
      }
      await page.goto(foreign + '/fixture/page')
      stage = 'public-cors'
      const publicCors = await page.evaluate(async (target) => {
        const manifest = await fetch(target + '/api/synthetic-browser-key/stremio/manifest.json', { credentials: 'omit' })
        const pair = await fetch(target + '/api/auth/pair/init', { method: 'POST', credentials: 'omit' })
        return { manifest: manifest.status, pair: pair.status }
      }, base)
      results.push({ repeat, login, cookie: flags, sameOriginUpdate: update, foreignPost, nativeLogin: native.status(), spoofedOrigin: spoofed.status(), nullOrigin: nullOrigin.status(), explicitAlternate, publicCors })
      await context.close()
    }
    console.log(JSON.stringify({ fixture: 'real-chromium-https-and-http-backend-proxy-v2-explicit-alternate-logical-clock', profile, browserVersion: browser.version(), tlsTrustOverride: 'synthetic test certificate only; not G06', results }))
  } finally {
    await browser.close()
    await api.dispose()
  }
}
main().catch((error) => { console.error(`Synthetic browser policy probe failed: stage=${stage} kind=${error.name}`); process.exitCode = 1 })
