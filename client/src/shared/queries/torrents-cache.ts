import { useMutation } from '@tanstack/react-query'

import { torrentsCacheCleanup } from '../lib/source/source-client'

export function useCleanupTorrentsCache() {
  return useMutation({
    mutationFn: async () => {
      await torrentsCacheCleanup()
    },
  })
}
