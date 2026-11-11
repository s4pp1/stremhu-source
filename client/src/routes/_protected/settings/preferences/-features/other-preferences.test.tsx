// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { UserResponse } from '@/shared/lib/source/source-client'
import type * as MeQueries from '@/shared/queries/me'
import { getMe } from '@/shared/queries/me'

import { OtherPreferences } from './other-preferences'

const { updateMe } = vi.hoisted(() => ({ updateMe: vi.fn() }))

vi.mock('@/shared/queries/me', async (original) => ({
  ...(await original<typeof MeQueries>()),
  useUpdateMe: () => ({ mutateAsync: updateMe }),
}))
vi.mock('@/features/smart-filter/smart-filter-settings', () => ({
  SmartFilterSettings: () => null,
}))
vi.mock('@/features/subtitle-settings/subtitle-settings', () => ({
  SubtitleSettingsCard: () => null,
}))

const SWITCH_NAME = 'Letöltött találatok jelölése és előresorolása'

function me(enableDownloadedMarker: boolean): UserResponse {
  return {
    id: 'fixture-user',
    username: 'fixture',
    role: { id: 'user', name: 'Felhasználó' },
    apiKey: 'fixture-key',
    updatedAt: '2026-11-08T00:00:00Z',
    createdAt: '2026-11-08T00:00:00Z',
    torrentSeed: null,
    enableSmartFilter: false,
    enableStreamDeduplication: true,
    smartFilterGroupingPreferenceId: null,
    smartFilterLimit: 1,
    enableFallbackSubtitles: false,
    enableCatalogSearch: true,
    enableDownloadedMarker,
    maxConcurrentStreams: null,
  }
}

function renderWith(user: UserResponse) {
  const client = new QueryClient({
    defaultOptions: { queries: { staleTime: Infinity, retry: false } },
  })
  client.setQueryData(getMe().queryKey, user)
  render(
    <QueryClientProvider client={client}>
      <OtherPreferences />
    </QueryClientProvider>,
  )
  return screen.getByRole('switch', { name: SWITCH_NAME })
}

afterEach(() => {
  cleanup()
  updateMe.mockReset()
})

describe('Letöltött találatok preferencia', () => {
  it('a mentett beállítást mutatja', () => {
    expect(renderWith(me(true)).getAttribute('aria-checked')).toBe('true')
    cleanup()
    expect(renderWith(me(false)).getAttribute('aria-checked')).toBe('false')
  })

  it('kikapcsoláskor elmenti a preferenciát a többi beállítás változatlanul hagyásával', async () => {
    updateMe.mockResolvedValue(me(false))
    const toggle = renderWith(me(true))

    fireEvent.click(toggle)

    await waitFor(() => expect(updateMe).toHaveBeenCalledTimes(1), {
      timeout: 3000,
    })
    expect(updateMe).toHaveBeenCalledWith({
      torrentSeed: null,
      enableSmartFilter: false,
      enableStreamDeduplication: true,
      smartFilterGroupingPreferenceId: null,
      smartFilterLimit: 1,
      enableCatalogSearch: true,
      enableDownloadedMarker: false,
    })
  })
})
