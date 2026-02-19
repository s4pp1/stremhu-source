import { useQuery } from '@tanstack/react-query'

import { UserRoleEnum } from '../lib/source-client'
import { getMe } from '../queries/me'

export const useIsAdmin = () => {
  const { data: me } = useQuery(getMe)

  const isAdmin = me?.userRole === UserRoleEnum.ADMIN

  return { isAdmin }
}
