import type { VariantProps } from 'class-variance-authority'

import { useFormContext } from '@/shared/contexts/form-context'

import { Button } from '../ui/button'
import type { buttonVariants } from '../ui/button'

export function SubscribeButton(
  props: React.ComponentProps<'button'> &
    VariantProps<typeof buttonVariants> & {
      asChild?: boolean
    },
) {
  const { children, disabled, ...rest } = props
  const form = useFormContext()

  return (
    <form.Subscribe selector={(state) => state.isSubmitting}>
      {(isSubmitting) => (
        <Button disabled={isSubmitting || disabled} {...rest}>
          {children}
        </Button>
      )}
    </form.Subscribe>
  )
}
