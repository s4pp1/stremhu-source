import { QueryClientProvider } from '@tanstack/react-query'
import { Profiler, Suspense } from 'react'
import { createRoot } from 'react-dom/client'

import { Route } from '@/routes/_protected/relay/torrents/index'
import { queryClient } from '@/shared/lib/client'
import '@/styles.css'

declare global {
  var __crG04: {
    routeRenders: number
    rowRenders: Record<string, number>
    commits: Array<{ phase: string; actualDuration: number; commitTime: number }>
    mount: () => void
    unmount: () => void
    queryCount: () => number
    queryReady: () => boolean
  }
}

const RouteComponent = Route.options.component!
globalThis.__crG04 = {
  routeRenders: 0,
  rowRenders: {},
  commits: [],
  mount: () => root.render(
    <QueryClientProvider client={queryClient}>
      <Profiler id="route" onRender={(_, phase, actualDuration, __, ___, commitTime) => {
        globalThis.__crG04.commits.push({ phase, actualDuration, commitTime })
      }}>
        <Suspense fallback={<p>Fixture betöltése</p>}><RouteComponent /></Suspense>
      </Profiler>
    </QueryClientProvider>,
  ),
  unmount: () => root.render(null),
  queryCount: () => queryClient.getQueryCache().getAll().length,
  queryReady: () => {
    const queries = queryClient.getQueryCache().getAll()
    return queries.length === 1 && queries.every((query) => query.state.status === 'success')
  },
}
const root = createRoot(document.getElementById('fixture')!)
globalThis.__crG04.mount()
