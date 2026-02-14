import { queryOptions } from '@tanstack/react-query'

import { appClient } from '../lib/client'

export const getMePreferences = queryOptions({
  queryKey: ['me', 'preferences'],
  queryFn: async () => {
    const response = await appClient.me.mePreferences()
    return response
  },
})
