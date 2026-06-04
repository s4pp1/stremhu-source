export type AddIndexerOptions = {
  activeIndexerIds: string[]
}

export type AddIndexerDialog = {
  type: 'ADD_INDEXER'
  options: AddIndexerOptions
}
