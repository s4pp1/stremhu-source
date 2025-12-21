import { useMutation } from '@tanstack/react-query'

import { appClient } from '../lib/client'

export function useCleanupTorrentsCache() {
  return useMutation({
    mutationFn: async () => {
      await appClient.torrentsCache.cleanup()
    },
  })
}
