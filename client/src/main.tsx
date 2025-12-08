import { QueryClientProvider } from '@tanstack/react-query'
import type { QueryClient } from '@tanstack/react-query'
import { RouterProvider, createRouter } from '@tanstack/react-router'
import { StrictMode } from 'react'
import ReactDOM from 'react-dom/client'

import reportWebVitals from './reportWebVitals.ts'
import { routeTree } from './routeTree.gen'
import { DefaultError } from './shared/components/default-error.tsx'
import { DefaultLoading } from './shared/components/default-loading.tsx'
import { queryClient } from './shared/lib/client.ts'
import './styles.css'

export interface RouterContext {
  queryClient: QueryClient
}

// Create a new router instance
const router = createRouter({
  routeTree,
  defaultPreload: 'intent',
  context: {} as RouterContext,
})

// Register the router instance for type safety
declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router
  }
}

// Render the app
const rootElement = document.getElementById('app')
if (rootElement && !rootElement.innerHTML) {
  const root = ReactDOM.createRoot(rootElement)
  root.render(
    <StrictMode>
      <QueryClientProvider client={queryClient}>
        <RouterProvider
          defaultPendingComponent={() => <DefaultLoading />}
          defaultErrorComponent={DefaultError}
          router={router}
          context={{ queryClient }}
        />
      </QueryClientProvider>
    </StrictMode>,
  )
}

reportWebVitals()
