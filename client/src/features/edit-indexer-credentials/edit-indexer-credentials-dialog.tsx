import type { MouseEventHandler, SubmitEventHandler } from 'react'
import { toast } from 'sonner'
import * as z from 'zod'

import type { OpenedDialog } from '@/routes/-features/dialogs/dialogs-store'
import { useDialogsStore } from '@/routes/-features/dialogs/dialogs-store'
import { Checkbox } from '@/shared/components/ui/checkbox'
import {
  Dialog,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogScrollContent,
  DialogTitle,
} from '@/shared/components/ui/dialog'
import { Field } from '@/shared/components/ui/field'
import { Label } from '@/shared/components/ui/label'
import { useAppForm } from '@/shared/contexts/form-context'
import { parseApiError } from '@/shared/lib/utils'
import { useIndexerUpdateCredentials } from '@/shared/queries/indexers'

import type { EditIndexerCredentialsDialog } from './edit-indexer-credentials.types'

const schema = z
  .object({
    username: z.string().trim().nonempty('A felhasználónév kitöltése kötelező'),
    password: z.string().trim().nonempty('A jelszó kitöltése kötelező'),
    useTotp: z.boolean(),
    totpSecret: z.string(),
  })
  .superRefine((data, ctx) => {
    if (data.useTotp && !data.totpSecret.trim()) {
      ctx.addIssue({
        code: 'custom',
        message: 'A 2FA titkos kulcs kitöltése kötelező',
        path: ['totpSecret'],
      })
    }
  })

export function EditIndexerCredentialsDialog(
  dialog: OpenedDialog & EditIndexerCredentialsDialog,
) {
  const { indexer } = dialog.options
  const { supportsTotp } = indexer.indexerDefinition

  const dialogsStore = useDialogsStore()

  const { mutateAsync: updateCredentials } = useIndexerUpdateCredentials(
    indexer.indexerId,
  )

  const form = useAppForm({
    defaultValues: {
      username: indexer.username,
      password: '',
      useTotp: false,
      totpSecret: '',
    },
    validators: {
      onChange: schema,
    },
    onSubmit: async ({ value }) => {
      try {
        await updateCredentials({
          username: value.username,
          password: value.password,
          totpSecret:
            supportsTotp && value.useTotp && value.totpSecret.trim()
              ? value.totpSecret.trim()
              : null,
        })
        toast.success(
          `A(z) ${indexer.indexerDefinition.name} belépési adatai frissültek.`,
        )
        dialogsStore.closeDialog(dialog.id)
      } catch (error) {
        const message = parseApiError(error)
        toast.error(message)
      }
    },
  })

  const handleSubmit: SubmitEventHandler<HTMLFormElement> = async (e) => {
    e.preventDefault()
    e.stopPropagation()
    await form.handleSubmit()
  }

  const handleClose: MouseEventHandler<HTMLButtonElement> = (e) => {
    e.preventDefault()
    e.stopPropagation()
    dialogsStore.closeDialog(dialog.id)
  }

  return (
    <Dialog open={dialog.open}>
      <DialogScrollContent
        className="md:max-w-md"
        onEscapeKeyDown={() => dialogsStore.closeDialog(dialog.id)}
      >
        <form.AppForm>
          <form
            name="edit-indexer-credentials"
            className="grid gap-4"
            onSubmit={handleSubmit}
          >
            <DialogHeader>
              <DialogTitle>
                {indexer.indexerDefinition.name} belépési adatai
              </DialogTitle>
              <DialogDescription>
                Az új adatokkal újra bejelentkezünk a torrent oldalra, és csak
                sikeres bejelentkezés után mentjük őket. A fiók beállításai és a
                futó torrentek megmaradnak.
              </DialogDescription>
            </DialogHeader>
            <form.AppField
              name="username"
              children={(field) => (
                <field.AppTextField label="Felhasználónév" />
              )}
            />
            <form.AppField
              name="password"
              children={(field) => (
                <field.AppTextField label="Jelszó" type="password" />
              )}
            />
            {supportsTotp && (
              <form.Subscribe selector={(state) => state.values.useTotp}>
                {(useTotp) => (
                  <div className="flex flex-col gap-3">
                    <form.Field name="useTotp">
                      {(field) => (
                        <Field orientation="horizontal">
                          <Checkbox
                            id={field.name}
                            name={field.name}
                            checked={field.state.value}
                            onCheckedChange={(checked) => {
                              field.handleChange(Boolean(checked))
                              if (!checked) {
                                form.setFieldValue('totpSecret', '')
                              }
                            }}
                          />
                          <Label htmlFor={field.name}>
                            Kétlépcsős azonosítás (2FA / TOTP) használata
                          </Label>
                        </Field>
                      )}
                    </form.Field>
                    {useTotp && (
                      <form.AppField
                        name="totpSecret"
                        children={(field) => (
                          <field.AppTextField
                            label="2FA titkos kulcs (TOTP)"
                            description="Ha a fiókodon be van kapcsolva a kétlépcsős azonosítás, a titkos kulcsot újra meg kell adnod."
                          />
                        )}
                      />
                    )}
                  </div>
                )}
              </form.Subscribe>
            )}
            <DialogFooter>
              <form.SubscribeButton
                variant="outline"
                type="button"
                onClick={handleClose}
              >
                Mégsem
              </form.SubscribeButton>
              <form.SubscribeButton type="submit">Mentés</form.SubscribeButton>
            </DialogFooter>
          </form>
        </form.AppForm>
      </DialogScrollContent>
    </Dialog>
  )
}
