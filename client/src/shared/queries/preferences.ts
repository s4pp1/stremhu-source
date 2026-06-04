import { queryOptions } from '@tanstack/react-query'

import { preferencesGetAll } from '../lib/source/source-client'

export const getPreferences = queryOptions({
  queryKey: ['preferences'],
  queryFn: async () => {
    const response = await preferencesGetAll()

    return response
  },
})
