import { useForm } from '@tanstack/react-form'
import { useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import * as z from 'zod'

import { Label } from '@/shared/components/ui/label'
import { Switch } from '@/shared/components/ui/switch'
import { assertExists, parseApiError } from '@/shared/lib/utils'
import { getSettings, useUpdateSetting } from '@/shared/queries/settings'

const schema = z.object({
  hitAndRun: z.boolean(),
})

export function HitAndRun() {
  const queryClient = useQueryClient()

  const setting = queryClient.getQueryData(getSettings.queryKey)
  assertExists(setting)

  const { mutateAsync: updateSetting } = useUpdateSetting()

  const form = useForm({
    defaultValues: {
      hitAndRun: setting.hitAndRun,
    },
    validators: {
      onChange: schema,
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
        await updateSetting(value)
      } catch (error) {
        formApi.reset()
        const message = parseApiError(error)
        toast.error(message)
      }
    },
  })

  return (
    <form.Field name="hitAndRun">
      {(field) => (
        <Label htmlFor={field.name} className="flex items-start gap-3">
          <Switch
            id={field.name}
            checked={field.state.value}
            onCheckedChange={field.handleChange}
          />
          <div className="flex-1 grid gap-2 font-normal">
            <p className="text-sm leading-none font-medium">
              Hit'n'Run ellenőrzés
            </p>
            <p className="text-muted-foreground text-sm">
              Minden nap 04:00-kor ellenőrizzük a torrenteket. A Hit'n'Run
              feltételt teljesítők automatikusan törlődnek.
            </p>
          </div>
        </Label>
      )}
    </form.Field>
  )
}
