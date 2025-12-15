import { useQuery, useQueryClient } from '@tanstack/react-query'
import type { MouseEventHandler } from 'react'
import { toast } from 'sonner'
import * as z from 'zod'

import { useDialogsStore } from '@/routes/-features/dialogs/dialogs-store'
import type { OpenedDialog } from '@/routes/-features/dialogs/dialogs-store'
import { Button } from '@/shared/components/ui/button'
import {
  Dialog,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogScrollContent,
  DialogTitle,
} from '@/shared/components/ui/dialog'
import { Field, FieldError } from '@/shared/components/ui/field'
import { Input } from '@/shared/components/ui/input'
import { useAppForm } from '@/shared/contexts/form-context'
import { assertExists, parseApiError } from '@/shared/lib/utils'
import { getCatalogHealth } from '@/shared/queries/catalog'
import { getSettings, useUpdateSetting } from '@/shared/queries/settings'

import type { StremhuCatalogDialog } from './types'

const schema = z.object({
  catalogToken: z.string().trim(),
})

export function StremhuCatalogDialog(
  dialog: OpenedDialog & StremhuCatalogDialog,
) {
  const dialogsStore = useDialogsStore()

  const { data: setting } = useQuery(getSettings)
  assertExists(setting)

  const queryClient = useQueryClient()
  const { mutateAsync: updateSetting } = useUpdateSetting()

  const form = useAppForm({
    defaultValues: {
      catalogToken: setting.catalogToken || '',
    },
    validators: {
      onChange: schema,
    },
    onSubmit: async ({ value }) => {
      try {
        await updateSetting({ catalogToken: value.catalogToken || null })

        if (value.catalogToken) {
          await queryClient.fetchQuery(getCatalogHealth)
        } else {
          await queryClient.resetQueries(getCatalogHealth)
        }

        dialogsStore.closeDialog(dialog.id)
      } catch (error) {
        const message = parseApiError(error)
        toast.error(message)
      }
    },
  })

  const handleSubmit: MouseEventHandler<HTMLButtonElement> = async (e) => {
    e.preventDefault()
    e.stopPropagation()
    await form.handleSubmit()
  }

  return (
    <Dialog open={dialog.open}>
      <DialogScrollContent
        className="md:max-w-md"
        onEscapeKeyDown={() => dialogsStore.closeDialog(dialog.id)}
      >
        <form.AppForm>
          <DialogHeader>
            <DialogTitle>StremHU | Catalog integráció</DialogTitle>
            <DialogDescription>
              A StremHU | Catalog integráció lehetővé teszi, hogy a sorozatok
              speciális epizódjait is listázza a torrentek közzött.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-2">
            <form.Field name="catalogToken">
              {(field) => (
                <Field>
                  <Input
                    name={field.name}
                    value={field.state.value}
                    onBlur={field.handleBlur}
                    onChange={(e) => {
                      field.handleChange(e.target.value)
                    }}
                  />
                  {field.state.meta.isTouched && (
                    <FieldError errors={field.state.meta.errors} />
                  )}
                </Field>
              )}
            </form.Field>
          </div>
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => dialogsStore.closeDialog(dialog.id)}
            >
              Mégsem
            </Button>
            <Button onClick={handleSubmit}>Mentés</Button>
          </DialogFooter>
        </form.AppForm>
      </DialogScrollContent>
    </Dialog>
  )
}
