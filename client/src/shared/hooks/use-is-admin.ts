import { useQuery } from '@tanstack/react-query'

import { getMe } from '../queries/me'

export const useIsAdmin = () => {
  const { data: me } = useQuery(getMe())

  const isAdmin = me?.role.id === 'admin'

  return { isAdmin }
}
