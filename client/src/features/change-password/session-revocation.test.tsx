import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import {
  act,
  cleanup,
  fireEvent,
  render,
  renderHook,
  screen,
  waitFor,
} from '@testing-library/react'
import type { PropsWithChildren } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { useDialogsStore } from '@/routes/-features/dialogs/dialogs-store'
import type { UserResponse } from '@/shared/lib/source/source-client'
import { meUpdate, usersUpdate } from '@/shared/lib/source/source-client'
import { useUpdateMe } from '@/shared/queries/me'
import { useUserUpdate } from '@/shared/queries/users'

import { ChangePasswordDialog } from './change-password-dialog'

const { navigate } = vi.hoisted(() => ({ navigate: vi.fn() }))

vi.mock('@tanstack/react-router', () => ({ useNavigate: () => navigate }))
vi.mock('@/shared/lib/source/source-client', async (original) => ({
  ...(await original<object>()),
  meUpdate: vi.fn(),
  usersUpdate: vi.fn(),
}))

const me: UserResponse = {
  id: 'one',
  username: 'fixture',
  role: { id: 'admin', name: 'Fixture admin' },
  apiKey: 'synthetic-key',
  createdAt: '2026-01-01',
  updatedAt: '2026-01-01',
  torrentSeed: null,
  enableSmartFilter: false,
  enableStreamDeduplication: true,
  smartFilterGroupingPreferenceId: null,
  smartFilterLimit: 1,
  enableFallbackSubtitles: false,
  enableCatalogSearch: true,
  maxConcurrentStreams: null,
}

function setup() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  client.setQueryData(['me'], me)
  client.setQueryData(['users'], [me])
  client.setQueryData(['playbacks'], ['synthetic private data'])
  function Wrapper({ children }: PropsWithChildren) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>
  }
  return { client, wrapper: Wrapper }
}

beforeEach(() => {
  vi.mocked(meUpdate).mockResolvedValue(me)
  vi.mocked(usersUpdate).mockResolvedValue(me)
  navigate.mockReset()
})

afterEach(() => {
  cleanup()
  useDialogsStore.setState({ dialogs: [] })
  vi.clearAllMocks()
})

describe('session query state after password changes', () => {
  it.each(['synthetic-new-password', null])(
    'clears all private queries after an explicit password operation',
    async (password) => {
      const { client, wrapper } = setup()
      const { result } = renderHook(() => useUpdateMe(), { wrapper })
      await act(() => result.current.mutateAsync({ password }))
      expect(client.getQueryCache().getAll()).toHaveLength(0)
    },
  )

  it('keeps profile data and invalidates users for an ordinary profile change', async () => {
    const { client, wrapper } = setup()
    const { result } = renderHook(() => useUpdateMe(), { wrapper })
    await act(() => result.current.mutateAsync({ torrentSeed: 7 }))
    expect(client.getQueryData(['me'])).toEqual(me)
    expect(client.getQueryData(['playbacks'])).toEqual([
      'synthetic private data',
    ])
    expect(client.getQueryState(['users'])?.isInvalidated).toBe(true)
  })

  it('retains the authenticated cache when the password request fails', async () => {
    vi.mocked(meUpdate).mockRejectedValueOnce(new Error('synthetic failure'))
    const { client, wrapper } = setup()
    const { result } = renderHook(() => useUpdateMe(), { wrapper })
    await act(async () => {
      await expect(
        result.current.mutateAsync({ password: null }),
      ).rejects.toThrow()
    })
    expect(client.getQueryData(['me'])).toEqual(me)
  })

  it.each(['one', 'other'])(
    'scopes admin password changes to the target %s',
    async (userId) => {
      const { client, wrapper } = setup()
      vi.mocked(usersUpdate).mockResolvedValueOnce({ ...me, id: userId })
      const { result } = renderHook(() => useUserUpdate(), { wrapper })
      await act(() =>
        result.current.mutateAsync({ userId, payload: { password: null } }),
      )
      expect(client.getQueryData(['me'])).toEqual(
        userId === 'one' ? undefined : me,
      )
    },
  )
})

describe('password form navigation', () => {
  it.each(['self', 'admin-self', 'other'])(
    'closes a successful %s dialog and only sends a revoked session to login',
    async (target) => {
      const { wrapper } = setup()
      const user =
        target === 'self'
          ? undefined
          : { ...me, id: target === 'other' ? 'other' : 'one' }
      const id = useDialogsStore
        .getState()
        .openDialog({ type: 'CHANGE_PASSWORD', options: { user } })
      const dialog = useDialogsStore
        .getState()
        .dialogs.find((item) => item.id === id)
      if (!dialog || dialog.type !== 'CHANGE_PASSWORD')
        throw new Error('Missing fixture dialog')
      render(<ChangePasswordDialog {...dialog} />, { wrapper })
      fireEvent.change(screen.getByLabelText('Új jelszó'), {
        target: { value: 'synthetic-new-password' },
      })
      fireEvent.click(screen.getByRole('button', { name: 'Módosítás' }))
      await waitFor(() =>
        expect(
          useDialogsStore.getState().dialogs.find((item) => item.id === id)
            ?.open,
        ).toBe(false),
      )
      if (target === 'other') expect(navigate).not.toHaveBeenCalled()
      else
        expect(navigate).toHaveBeenCalledWith({ to: '/login', replace: true })
    },
  )

  it('keeps the dialog open when saving fails', async () => {
    vi.mocked(meUpdate).mockRejectedValueOnce(new Error('synthetic failure'))
    const { wrapper } = setup()
    const id = useDialogsStore
      .getState()
      .openDialog({ type: 'CHANGE_PASSWORD', options: {} })
    render(
      <ChangePasswordDialog id={id} open type="CHANGE_PASSWORD" options={{}} />,
      { wrapper },
    )
    fireEvent.change(screen.getByLabelText('Új jelszó'), {
      target: { value: 'synthetic-new-password' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Módosítás' }))
    await waitFor(() => expect(meUpdate).toHaveBeenCalled())
    expect(navigate).not.toHaveBeenCalled()
    expect(
      useDialogsStore.getState().dialogs.find((item) => item.id === id)?.open,
    ).toBe(true)
  })
})
