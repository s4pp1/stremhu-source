import type { IndexerResponse } from '@/shared/lib/source/source-client'

export type EditIndexerCredentialsOptions = {
  indexer: IndexerResponse
}

export type EditIndexerCredentialsDialog = {
  type: 'EDIT_INDEXER_CREDENTIALS'
  options: EditIndexerCredentialsOptions
}
