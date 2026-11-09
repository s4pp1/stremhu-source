import {
  queryOptions,
  useMutation,
  useQueryClient,
} from '@tanstack/react-query'

import type {
  BrowseDirectoriesResponse,
  CreateDirectoryRequest,
  CreateDirectoryResponse,
  DirectoryEntry,
} from '../lib/source/source-client'
import {
  filesystemBrowseDirectories,
  filesystemCreateDirectory,
} from '../lib/source/source-client'

export type {
  BrowseDirectoriesResponse,
  CreateDirectoryRequest,
  CreateDirectoryResponse,
  DirectoryEntry,
}

export const getBrowseDirectories = (path?: string) =>
  queryOptions({
    queryKey: ['filesystem', 'directories', path ?? 'default'],
    queryFn: async () => {
      const response = await filesystemBrowseDirectories(
        path ? { path } : undefined,
      )
      return response
    },
  })

export function useCreateDirectory() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (payload: CreateDirectoryRequest) => {
      const response = await filesystemCreateDirectory(payload)
      return response
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: ['filesystem', 'directories', variables.parentPath],
      })
    },
  })
}
