import { toast } from 'sonner'
import * as z from 'zod'

import { SmartFilterSettings } from '@/features/smart-filter/smart-filter-settings'
import { useAppForm } from '@/shared/contexts/form-context'
import type { UserResponse } from '@/shared/lib/source/source-client'
import { parseApiError } from '@/shared/lib/utils'
import { useUserUpdate } from '@/shared/queries/users'
import {
  enableSmartFilterSchema,
  smartFilterGroupingPreferenceIdSchema,
  smartFilterLimitSchema,
} from '@/shared/schemas'

const validatorSchema = z.object({
  enableSmartFilter: enableSmartFilterSchema,
  smartFilterGroupingPreferenceId: smartFilterGroupingPreferenceIdSchema,
  smartFilterLimit: smartFilterLimitSchema,
})

type OnlyBestTorrent = {
  user: UserResponse
}

export function OnlyBestTorrent(props: OnlyBestTorrent) {
  const { user } = props

  const { mutateAsync: updateUser } = useUserUpdate()

  const form = useAppForm({
    defaultValues: {
      enableSmartFilter: user.enableSmartFilter,
      smartFilterGroupingPreferenceId: user.smartFilterGroupingPreferenceId,
      smartFilterLimit: user.smartFilterLimit,
    },
    validators: {
      onChange: validatorSchema,
    },
    listeners: {
      onChangeDebounceMs: 1000,
      onChange: ({ formApi }) => {
        if (formApi.state.isValid) {
          formApi.handleSubmit()
        }
      },
    },
    onSubmit: async ({ value, formApi }) => {
      try {
        await updateUser({ userId: user.id, payload: value })
      } catch (error) {
        formApi.reset()
        const message = parseApiError(error)
        toast.error(message)
      }
    },
  })

  return (
    <SmartFilterSettings
      form={form}
      fields={{
        enableSmartFilter: 'enableSmartFilter',
        smartFilterLimit: 'smartFilterLimit',
        smartFilterGroupingPreferenceId: 'smartFilterGroupingPreferenceId',
      }}
    />
  )
}
