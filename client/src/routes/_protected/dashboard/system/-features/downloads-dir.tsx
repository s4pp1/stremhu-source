import { useForm } from '@tanstack/react-form'
import { useSuspenseQueries } from '@tanstack/react-query'
import { FolderDownIcon, FolderOpenIcon, LockIcon } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'
import * as z from 'zod'

import { Badge } from '@/shared/components/ui/badge'
import { Button } from '@/shared/components/ui/button'
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/shared/components/ui/card'
import { Field, FieldError } from '@/shared/components/ui/field'
import {
  InputGroup,
  InputGroupAddon,
  InputGroupInput,
} from '@/shared/components/ui/input-group'
import { parseApiError } from '@/shared/lib/utils'
import {
  getSystemSettings,
  getSystemStatus,
  useSystemSettingsUpdate,
} from '@/shared/queries/system'

import { DirectoryPickerDialog } from '../-components/directory-picker-dialog'

const schema = z.object({
  downloadsDir: z
    .string()
    .trim()
    .min(1, 'A letöltési mappa elérési útjának megadása kötelező.')
    .refine(
      (val) => val.startsWith('/') || /^[a-zA-Z]:[\\/]/.test(val),
      'A letöltési mappának abszolút elérési útvonalnak kell lennie!',
    ),
})

export function DownloadsDir() {
  const [{ data: systemSettings }, { data: systemStatus }] = useSuspenseQueries(
    {
      queries: [getSystemSettings, getSystemStatus],
    },
  )

  const isLocked = systemStatus.isDownloadsDirOverridden
  const { mutateAsync: updateSetting } = useSystemSettingsUpdate()
  const [isPickerOpen, setIsPickerOpen] = useState(false)

  const form = useForm({
    defaultValues: {
      downloadsDir: systemSettings.downloadsDir,
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
      if (value.downloadsDir.trim() === systemSettings.downloadsDir) {
        return
      }

      try {
        await updateSetting({
          downloadsDir: value.downloadsDir.trim(),
        })
        toast.success('A letöltési mappa sikeresen mentve!')
      } catch (error) {
        formApi.reset()
        const message = parseApiError(error)
        toast.error(message)
      }
    },
  })

  const handleDirectorySelected = async (selectedPath: string) => {
    form.setFieldValue('downloadsDir', selectedPath)
    try {
      await updateSetting({
        downloadsDir: selectedPath,
      })
      toast.success('A letöltési mappa sikeresen beállítva!')
    } catch (error) {
      form.reset()
      const message = parseApiError(error)
      toast.error(message)
    }
  }

  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle>Letöltési mappa</CardTitle>
          <CardDescription>
            {isLocked
              ? 'A letöltési mappa környezeti változóban vagy Docker konfigurációban van megadva, így ezen a felületen nem módosítható.'
              : 'A letöltött médiafájlok és ideiglenes adatok tárolási helye a merevlemezen.'}
          </CardDescription>
          {isLocked && (
            <CardAction>
              <Badge variant="secondary" className="gap-1">
                <LockIcon className="size-3" />
                Zárolva
              </Badge>
            </CardAction>
          )}
        </CardHeader>
        <CardContent className="grid gap-6">
          {isLocked ? (
            <Field>
              <InputGroup>
                <InputGroupAddon align="inline-start">
                  <FolderDownIcon className="size-4" />
                </InputGroupAddon>
                <InputGroupInput
                  id="downloadsDir"
                  name="downloadsDir"
                  value={systemStatus.downloadsDir}
                  disabled
                />
              </InputGroup>
            </Field>
          ) : (
            <form
              onSubmit={(e) => {
                e.preventDefault()
                e.stopPropagation()
                form.handleSubmit()
              }}
            >
              <form.Field name="downloadsDir">
                {(field) => (
                  <Field>
                    <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2">
                      <InputGroup className="flex-1">
                        <InputGroupAddon align="inline-start">
                          <FolderDownIcon className="size-4" />
                        </InputGroupAddon>
                        <InputGroupInput
                          id={field.name}
                          name={field.name}
                          value={field.state.value}
                          onBlur={field.handleBlur}
                          onChange={(e) => field.handleChange(e.target.value)}
                          placeholder="/eleresi/ut/a/letoltesekhez"
                        />
                      </InputGroup>
                      <Button
                        type="button"
                        variant="outline"
                        onClick={() => setIsPickerOpen(true)}
                        className="shrink-0"
                      >
                        <FolderOpenIcon className="size-4 mr-1.5" />
                        Mappa kiválasztása
                      </Button>
                    </div>
                    {field.state.meta.isTouched && (
                      <FieldError errors={field.state.meta.errors} />
                    )}
                  </Field>
                )}
              </form.Field>
            </form>
          )}
        </CardContent>
      </Card>

      {!isLocked && (
        <DirectoryPickerDialog
          open={isPickerOpen}
          onOpenChange={setIsPickerOpen}
          initialPath={systemSettings.downloadsDir}
          onSelect={handleDirectorySelected}
        />
      )}
    </>
  )
}
