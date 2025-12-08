import { createFormHook, createFormHookContexts } from '@tanstack/react-form'

import { AppTextField } from '@/shared/components/form/app-text-field'
import { SubscribeButton } from '@/shared/components/form/subscribe-button'

export const { fieldContext, formContext, useFieldContext, useFormContext } =
  createFormHookContexts()

export const { useAppForm, withForm } = createFormHook({
  fieldContext,
  formContext,
  fieldComponents: { AppTextField },
  formComponents: { SubscribeButton },
})
