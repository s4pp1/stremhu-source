import { useForm } from '@tanstack/react-form'
import { useQueryClient } from '@tanstack/react-query'
import { isEmpty } from 'lodash'
import { TriangleAlertIcon } from 'lucide-react'
import { toast } from 'sonner'
import * as z from 'zod'

import {
  Alert,
  AlertDescription,
  AlertTitle,
} from '@/shared/components/ui/alert'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/shared/components/ui/card'
import { Field, FieldError, FieldLabel } from '@/shared/components/ui/field'
import {
  InputGroup,
  InputGroupAddon,
  InputGroupInput,
  InputGroupText,
} from '@/shared/components/ui/input-group'
import { Label } from '@/shared/components/ui/label'
import { Switch } from '@/shared/components/ui/switch'
import { parseApiError } from '@/shared/lib/utils'
import { getSettings, useUpdateSetting } from '@/shared/queries/settings'

const schema = z.object({
  downloadLimit: z.coerce.number<string>().positive().nullable(),
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
      downloadLimit: setting.downloadLimit,
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
          downloadLimit: value.downloadLimit ? Number(value.downloadLimit) : -1,
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
          <form.Field name="downloadLimit">
            {(field) => (
              <Field>
                <FieldLabel htmlFor={field.name}>Letöltési sebesség</FieldLabel>
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
          <form.Field name="uploadLimit">
            {(field) => (
              <Field>
                <FieldLabel htmlFor={field.name}>
                  Feltöltési sebesség
                </FieldLabel>
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
          <Alert>
            <TriangleAlertIcon />
            <AlertTitle>Figyelmeztetés magas CPU használatra!</AlertTitle>
            <AlertDescription>
              A túl magas letöltési vagy feltöltési sebesség jelentősen
              terhelheti a processzort. Javasolt a WebTorrent sebességkorlátokat
              200 Mbit/s alatt tartani.
            </AlertDescription>
          </Alert>
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
        </CardContent>
      </Card>
    </form>
  )
}
