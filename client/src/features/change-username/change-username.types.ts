import type { UserDto } from '@/shared/lib/source/source-client'

export type ChangeUsernameOptions = {
  user?: UserDto
}

export type ChangeUsernameDialog = {
  type: 'CHANGE_USERNAME'
  options: ChangeUsernameOptions
}
