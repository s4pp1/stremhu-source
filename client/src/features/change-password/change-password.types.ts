import type { UserDto } from '@/shared/lib/source-client'

export type ChangePasswordOptions = {
  user?: UserDto
}

export type ChangePasswordDialog = {
  type: 'CHANGE_PASSWORD'
  options: ChangePasswordOptions
}
