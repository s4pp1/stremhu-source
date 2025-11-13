import { useForm } from '@tanstack/react-form'
import { useQueryClient } from '@tanstack/react-query'
import { isEmpty } from 'lodash'
import { toast } from 'sonner'
import * as z from 'zod'

import { parseApiError } from '@/common/utils'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import {
  Field,
  FieldDescription,
  FieldError,
  FieldLabel,
} from '@/components/ui/field'
import {
  InputGroup,
  InputGroupAddon,
  InputGroupInput,
  InputGroupText,
} from '@/components/ui/input-group'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { getSettings, useUpdateSetting } from '@/queries/settings'

const schema = z.object({
  uploadLimit: z.coerce.number<string>().positive().nullable(),
  hitAndRun: z.boolean(),
})

export function WebTorrent() {
  const queryClient = useQueryClient()
  const setting = queryClient.getQueryData(getSettings.queryKey)
  if (!setting) throw new Error(`Nincs "settings" a cache-ben`)

  const { mutateAsync: updateSetting } = useUpdateSetting()

  const form = useForm({
    defaultValues: {
      uploadLimit: setting.uploadLimit,
      hitAndRun: setting.hitAndRun,
    },
    validators: {
      onChange: schema,
    },
    listeners: {
      onChangeDebounceMs: 2000,
      onChange: ({ formApi }) => {
        if (formApi.state.isValid) {
          formApi.handleSubmit()
        }
      },
    },
    onSubmit: async ({ value, formApi }) => {
      try {
        await updateSetting({
          ...value,
          uploadLimit: value.uploadLimit ? Number(value.uploadLimit) : -1,
        })
        toast.success('Módosítások elmentve')
      } catch (error) {
        formApi.reset()
        const message = parseApiError(error)
        toast.error(message)
      }
    },
  })

  return (
    <form name="setting">
      <Card>
        <CardHeader>
          <CardTitle>WebTorrent beállítása</CardTitle>
          <CardDescription>
            Környezetednek megfelelően állítsd be a torrent klienst.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid grid-cols-1 gap-6">
          <form.Field name="uploadLimit">
            {(field) => (
              <Field>
                <FieldLabel htmlFor={field.name}>
                  WebTorrent feltöltési sebesség
                </FieldLabel>
                <FieldDescription>
                  Limitáld a kliens feltöltési sebességét.
                </FieldDescription>
                <InputGroup>
                  <InputGroupInput
                    placeholder="Nincs limitálva"
                    inputMode="numeric"
                    id={field.name}
                    name={field.name}
                    value={field.state.value ?? ''}
                    onBlur={field.handleBlur}
                    onChange={(e) => {
                      const value = e.target.value

                      if (isEmpty(value)) {
                        field.handleChange(null)
                      } else {
                        field.handleChange(e.target.value)
                      }
                    }}
                  />
                  <InputGroupAddon align="inline-end">
                    <InputGroupText>Mbit/s</InputGroupText>
                  </InputGroupAddon>
                </InputGroup>
                {field.state.meta.isTouched && (
                  <FieldError errors={field.state.meta.errors} />
                )}
              </Field>
            )}
          </form.Field>
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
                    Minden nap 04:00-kor ellenőrizzük a torrenteket. A Hit’n’Run
                    feltételt teljesítők automatikusan törlődnek.
                  </p>
                </div>
              </Label>
            )}
          </form.Field>
        </CardContent>
      </Card>
    </form>
  )
}
