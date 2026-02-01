import type { RelaySettingsDto } from '@/shared/lib/source-client'

export type EditRelayOptions = {
  relay: RelaySettingsDto
}

export type EditRelayDialog = {
  type: 'EDIT_RELAY'
  options: EditRelayOptions
}
