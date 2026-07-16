import { i18n } from '@lingui/core'
import { I18nProvider } from '@lingui/react'
import type { QueryClient } from '@tanstack/react-query'
import { QueryClientProvider } from '@tanstack/react-query'
import { RouterProvider, createRouter } from '@tanstack/react-router'
import { setDefaultOptions } from 'date-fns'
import { hu as dateFnsHu } from 'date-fns/locale'
import { StrictMode } from 'react'
import ReactDOM from 'react-dom/client'
import * as z from 'zod'
import { hu as zodHu } from 'zod/locales'

import reportWebVitals from './reportWebVitals.ts'
import { routeTree } from './routeTree.gen'
import { DefaultError } from './shared/components/default-error.tsx'
import { DefaultLoading } from './shared/components/default-loading.tsx'
import { useLanguageStore } from './shared/hooks/useLanguageStore.ts'
import { dynamicActivate } from './shared/i18n/index.ts'
import { queryClient } from './shared/lib/client.ts'
import './styles.css'

z.config(zodHu())
setDefaultOptions({ locale: dateFnsHu })

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

  const init = async () => {
    // Initial nyelv betöltése mielőtt a React fa kirajzolódna
    const locale = useLanguageStore.getState().locale
    await dynamicActivate(locale)

    root.render(
      <StrictMode>
        <I18nProvider i18n={i18n}>
          <QueryClientProvider client={queryClient}>
            <RouterProvider
              defaultPendingComponent={() => <DefaultLoading />}
              defaultErrorComponent={DefaultError}
              router={router}
              context={{ queryClient }}
            />
          </QueryClientProvider>
        </I18nProvider>
      </StrictMode>,
    )
  }

  init()
}

reportWebVitals()
