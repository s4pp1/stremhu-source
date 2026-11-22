import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, cleanup, render, screen } from '@testing-library/react'
import type { PropsWithChildren } from 'react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type * as ItemModule from '@/shared/components/ui/item'
import type { TorrentResponse } from '@/shared/lib/source/source-client'
import { getTorrents } from '@/shared/queries/torrents'

import { Torrents } from './torrents'

const { titleRenders } = vi.hoisted(() => ({
  titleRenders: new Map<string, number>(),
}))

vi.mock('@/shared/components/ui/item', async (original) => {
  const actual = await original<typeof ItemModule>()
  return {
    ...actual,
    ItemTitle: (props: PropsWithChildren<{ className?: string }>) => {
      const children = props.children
      const name = Array.isArray(children)
        ? children.join('')
        : String(children)
      titleRenders.set(name, (titleRenders.get(name) ?? 0) + 1)
      return <actual.ItemTitle {...props} />
    },
  }
})

function torrent(index: number, downloaded: number): TorrentResponse {
  return {
    infoHash: `hash-${index}`,
    indexerDefinition: {
      id: 'fixture',
      name: 'Fixture',
      url: 'https://fixture.invalid',
      detailsPath: '/details',
      requiresFullDownload: false,
      supportsTotp: false,
    },
    torrentId: `torrent-${index}`,
    name: `fixture-${index}`,
    downloadSpeed: 0,
    uploadSpeed: 0,
    downloaded,
    uploaded: 0,
    total: 100,
    isPersisted: false,
    fullDownload: null,
    updatedAt: '2026-01-01T00:00:00Z',
    createdAt: '2026-01-01T00:00:00Z',
  }
}

afterEach(() => {
  cleanup()
  titleRenders.clear()
})

describe('Torrents list', () => {
  it('re-renders only the row whose data changed', async () => {
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false, staleTime: Infinity } },
    })
    client.setQueryData(getTorrents.queryKey, [
      torrent(0, 10),
      torrent(1, 10),
      torrent(2, 10),
    ])
    render(
      <QueryClientProvider client={client}>
        <Torrents />
      </QueryClientProvider>,
    )
    expect([...titleRenders.values()]).toEqual([1, 1, 1])

    await act(async () => {
      client.setQueryData(getTorrents.queryKey, [
        torrent(0, 10),
        torrent(1, 50),
        torrent(2, 10),
      ])
      await new Promise((resolve) => setTimeout(resolve, 0))
    })

    expect(titleRenders.get('[Fixture] fixture-0')).toBe(1)
    expect(titleRenders.get('[Fixture] fixture-1')).toBe(2)
    expect(titleRenders.get('[Fixture] fixture-2')).toBe(1)
    expect(screen.getByText(/fixture-1/)).toBeTruthy()
  })
})
