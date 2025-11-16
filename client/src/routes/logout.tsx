import { createFileRoute, redirect, useNavigate } from '@tanstack/react-router'
import { useEffect } from 'react'

import { Item, ItemContent, ItemMedia, ItemTitle } from '@/components/ui/item'
import { Spinner } from '@/components/ui/spinner'
import { useLogout } from '@/queries/auth'
import { getMe } from '@/queries/me'

export const Route = createFileRoute('/logout')({
  beforeLoad: async ({ context }) => {
    const queryClient = context.queryClient

    const me = await queryClient.ensureQueryData(getMe)

    if (me === null) {
      throw redirect({ to: '/login' })
    }
  },
  component: LogoutRoute,
})

function LogoutRoute() {
  const navigate = useNavigate()
  const { mutateAsync: logout } = useLogout()

  const handleLogout = async () => {
    await logout()
    setTimeout(() => {
      navigate({ to: '/login' })
    }, 1000)
  }

  useEffect(() => {
    handleLogout()
  }, [])

  return (
    <div className="flex justify-center py-4">
      <Item variant="muted" className="rounded-4xl">
        <ItemMedia>
          <Spinner />
        </ItemMedia>
        <ItemContent>
          <ItemTitle className="line-clamp-1 pr-2">Kijelentkezés...</ItemTitle>
        </ItemContent>
      </Item>
    </div>
  )
}
