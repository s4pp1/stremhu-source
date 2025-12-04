import { DialogDescription, DialogTitle } from '@radix-ui/react-dialog'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import type { MouseEventHandler } from 'react'
import { toast } from 'sonner'
import * as z from 'zod'

import { assertExists } from '@/common/assert'
import { parseApiError } from '@/common/utils'
import { Button } from '@/components/ui/button'
import {
  DialogContent,
  DialogFooter,
  DialogHeader,
} from '@/components/ui/dialog'
import { Field, FieldError } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { useAppForm } from '@/contexts/form-context'
import { getCatalogHealth } from '@/queries/catalog'
import { getSettings, useUpdateSetting } from '@/queries/settings'
import { useDialogsStore } from '@/store/dialogs-store'

const schema = z.object({
  catalogToken: z.string().trim(),
})

export function StremhuCatalogDialog() {
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

        dialogsStore.handleClose()
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
    <DialogContent
      className="sm:max-w-md"
      showCloseButton={false}
      onEscapeKeyDown={dialogsStore.handleClose}
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
            variant="link"
            onClick={dialogsStore.handleClose}
          >
            Mégsem
          </Button>
          <Button onClick={handleSubmit}>Mentés</Button>
        </DialogFooter>
      </form.AppForm>
    </DialogContent>
  )
}
