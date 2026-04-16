import { createFileRoute } from '@tanstack/react-router'
import type { SubmitEventHandler } from 'react'
import { toast } from 'sonner'
import * as z from 'zod'

import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/shared/components/ui/card'
import {
  InputOTP,
  InputOTPGroup,
  InputOTPSlot,
} from '@/shared/components/ui/input-otp'
import { useAppForm } from '@/shared/contexts/form-context'
import { parseApiError } from '@/shared/lib/utils'
import { usePairVerify } from '@/shared/queries/auth'

export const Route = createFileRoute('/_protected/activate/')({
  component: RouteComponent,
})

const schema = z.object({
  userCode: z.string().trim().length(4),
})

function RouteComponent() {
  const { mutateAsync: pairVerify } = usePairVerify()

  const form = useAppForm({
    defaultValues: {
      userCode: '',
    },
    validators: {
      onChange: schema,
    },
    onSubmit: async ({ value, formApi }) => {
      try {
        await pairVerify(value)
        toast.success('A bejelentkezés sikeresen megerősítve!')
        formApi.reset()
      } catch (error) {
        const message = parseApiError(error)
        toast.error(message)
      }
    },
  })

  const onSubmit: SubmitEventHandler<HTMLFormElement> = async (e) => {
    e.preventDefault()
    e.stopPropagation()
    await form.handleSubmit()
  }

  return (
    <form.AppForm>
      <form
        name="login"
        className="flex flex-col items-center py-10"
        onSubmit={onSubmit}
      >
        <Card className="w-sm">
          <CardHeader>
            <CardTitle>Bejelentkezés megerősítése</CardTitle>
            <CardDescription>
              A kliensben megjelenő 4-jegyű kódot add meg a bejelentkezés
              megerősítéséhez.
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4 justify-center">
            <form.AppField
              name="userCode"
              children={(field) => {
                const hasError =
                  field.state.meta.errors.length > 0 &&
                  field.form.state.submissionAttempts > 0
                return (
                  <InputOTP
                    maxLength={4}
                    value={field.state.value}
                    onChange={field.handleChange}
                  >
                    <InputOTPGroup>
                      <InputOTPSlot index={0} aria-invalid={hasError} />
                      <InputOTPSlot index={1} aria-invalid={hasError} />
                      <InputOTPSlot index={2} aria-invalid={hasError} />
                      <InputOTPSlot index={3} aria-invalid={hasError} />
                    </InputOTPGroup>
                  </InputOTP>
                )
              }}
            />
          </CardContent>
          <CardFooter className="grid gap-4">
            <form.SubscribeButton type="submit">
              Megerősítés
            </form.SubscribeButton>
          </CardFooter>
        </Card>
      </form>
    </form.AppForm>
  )
}
