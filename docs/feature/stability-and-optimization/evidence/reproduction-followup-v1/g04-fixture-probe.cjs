/* Real-time G04 profile. No dev StrictMode or virtual-time substitution. */
const { chromium } = require('playwright')
const fs = require('node:fs')
function resources() {
  const counters = (path) => Object.fromEntries(fs.readFileSync(path, 'utf8').trim().split('\n').map((line) => line.split(/\s+/)))
  const memory = counters('/sys/fs/cgroup/memory.stat')
  const cpu = counters('/sys/fs/cgroup/cpu.stat')
  return { cpu_usec: Number(cpu.usage_usec), anon_bytes: Number(memory.anon), file_bytes: Number(memory.file),
    current_bytes: Number(fs.readFileSync('/sys/fs/cgroup/memory.current', 'utf8')),
    peak_bytes: Number(fs.readFileSync('/sys/fs/cgroup/memory.peak', 'utf8')) }
}

const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms))
const base = process.env.TEST_BASE_URL
if (!base) throw new Error('TEST_BASE_URL required')
const heapMode = process.argv.includes('--heap')
const smoke = process.argv.includes('--fixture-smoke')
if (heapMode && smoke) throw new Error('Heap smoke is not a measurement mode')

function fixture(count, tick, pattern) {
  return Array.from({ length: count }, (_, i) => ({
    infoHash: (i + 1).toString(16).padStart(40, '0'),
    indexerDefinition: {
      id: 'fixture', name: 'Synthetic', url: 'https://fixture.invalid',
      detailsPath: '/details/{torrent_id}', requiresFullDownload: false, supportsTotp: false,
    },
    torrentId: String(i), name: `Synthetic torrent ${i}`,
    downloadSpeed: pattern === 'stalled' ? 0 : pattern === 'all' || (pattern === 'one' && i === 0) ? tick * 1024 : 0,
    uploadSpeed: 0,
    downloaded: pattern === 'stalled' ? 1024 : pattern === 'all' || (pattern === 'one' && i === 0) ? 1024 + tick : 1024,
    uploaded: 0, total: pattern === 'stalled' || pattern === 'all' || pattern === 'one' ? 1048576 : 1024,
    isPersisted: true, fullDownload: null,
    updatedAt: '2026-01-01T00:00:00Z', createdAt: '2026-01-01T00:00:00Z',
  }))
}

;(async () => {
  const browser = await chromium.launch({ headless: true, args: ['--js-flags=--expose-gc'] })
  const rows = []
  try {
    for (const count of smoke ? [20] : heapMode ? [500] : [0, 20, 100, 500]) {
      for (const pattern of smoke || heapMode ? ['one'] : ['stable', 'one', 'all', 'stalled']) {
        const context = await browser.newContext()
        const page = await context.newPage()
        const errors = []
        page.on('pageerror', (e) => errors.push(e.name))
        let requests = 0
        const requestTimes = []
        await page.route((url) => /^\/api\/torrents\/?$/.test(url.pathname), async (route) => {
          requests++
          requestTimes.push(performance.now())
          await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(fixture(count, requests, pattern)) })
        })
        const coldStarted = performance.now()
        await page.goto(base)
        await page.waitForFunction(() => globalThis.__crG04?.queryReady())
        const cold = { wall_ms: performance.now()-coldStarted, requests,
          ...await page.evaluate(() => ({ routeRenders: __crG04.routeRenders, rowRenders: __crG04.rowRenders, commits: __crG04.commits.slice() })),
        }
        // Three successful polls establish the actual adaptive interval before
        // counters are reset. Warmup is excluded from the real5min sample.
        const warmupStarted = performance.now()
        while (requests < 3) {
          if (performance.now()-warmupStarted > 30_000) throw new Error('WarmupPollingTimeout')
          await wait(100)
        }
        await page.waitForFunction(() => globalThis.__crG04?.queryReady())
        const warmupRequests = requests
        await page.evaluate(() => {
          __crG04.commits.splice(0)
          __crG04.routeRenders = 0
          __crG04.rowRenders = {}
        })
        const measuredRequestStart = requestTimes.length
        const cdp = await context.newCDPSession(page)
        const samples = []
        // Keep instrumentation history outside the measured browser heap.
        // Otherwise the profiler's own unbounded array resembles a leak.
        const capturedCommits = []
        const resourceBefore = resources()
        const started = performance.now()
        console.error(JSON.stringify({ event: 'cell-start', count, pattern, heapMode, smoke }))
        // The extra15s guarantees a full gcTime after the actual unmount
        // dispatch, which can occur just after the20-minute threshold.
        const duration = smoke ? 30_000 : heapMode ? 30 * 60_000 + 15_000 : 5 * 60_000
        let navigations = 0
        let nextHeap = started
        let unmounted = false
        while (performance.now() - started < duration) {
          const elapsed = performance.now() - started
          if (heapMode && navigations < 50 && elapsed >= navigations * 20_000) {
            await page.evaluate(() => globalThis.__crG04.unmount())
            await wait(100)
            await page.evaluate(() => globalThis.__crG04.mount())
            navigations++
          }
          // Fifty navigations finish before20min. The final10min is a real
          // unmounted wait, exceeding the production query gcTime.
          if (heapMode && elapsed >= 20 * 60_000 && !unmounted) {
            await page.evaluate(() => globalThis.__crG04.unmount())
            unmounted = true
          }
          if (heapMode && performance.now() >= nextHeap) {
            capturedCommits.push(...await page.evaluate(() => __crG04.commits.splice(0)))
            await cdp.send('HeapProfiler.collectGarbage')
            const usage = await cdp.send('Runtime.getHeapUsage')
            samples.push({ elapsed_ms: elapsed, ...usage, queries: await page.evaluate(() => globalThis.__crG04.queryCount()) })
            nextHeap += 60_000
          }
          await wait(1000)
        }
        if (heapMode) {
          capturedCommits.push(...await page.evaluate(() => __crG04.commits.splice(0)))
          await cdp.send('HeapProfiler.collectGarbage')
          samples.push({ elapsed_ms: performance.now()-started, ...await cdp.send('Runtime.getHeapUsage'), queries: await page.evaluate(() => globalThis.__crG04.queryCount()) })
          const session = await context.newCDPSession(page)
          const chunks = []
          session.on('HeapProfiler.addHeapSnapshotChunk', ({ chunk }) => chunks.push(chunk))
          await session.send('HeapProfiler.takeHeapSnapshot', { reportProgress: false })
          require('node:fs').writeFileSync('/fixture-output/g04-final.heapsnapshot', chunks.join(''))
        }
        rows.push({ count, pattern, resource_before: resourceBefore, resource_after: resources(), requests: requests-warmupRequests, cold, warmupRequests, request_times_ms: requestTimes.slice(measuredRequestStart).map((stamp) => stamp-started), navigations, elapsed_ms: performance.now()-started,
          ...await page.evaluate(() => ({ routeRenders: __crG04.routeRenders, rowRenders: __crG04.rowRenders, commits: __crG04.commits })),
          ...(heapMode ? { commits: capturedCommits } : {}),
          heap: samples, errors,
        })
        console.error(JSON.stringify({ event: 'cell-complete', count, pattern, seconds: (performance.now()-started)/1000, requests: requests-warmupRequests, errors: errors.length }))
        await context.close()
      }
    }
    process.stdout.write(JSON.stringify({ fixture: smoke ? 'g04-fixture-smoke-not-measurement-v3' : 'g04-production-profiling-fixed-api-v3', is_measurement: !smoke, browser: browser.version(), heapMode, rows }))
  } finally { await browser.close() }
})().catch((e) => { console.error(e.name); process.exitCode = 1 })
