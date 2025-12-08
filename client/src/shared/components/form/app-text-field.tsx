import { useStore } from '@tanstack/react-form'
import type { HTMLInputTypeAttribute } from 'react'

import { useFieldContext, useFormContext } from '@/shared/contexts/form-context'

import { Field, FieldError, FieldLabel } from '../ui/field'
import { Input } from '../ui/input'

type AppTextField = {
  label?: string
  type?: HTMLInputTypeAttribute
}

export function AppTextField(props: AppTextField) {
  const { label, type } = props

  const form = useFormContext()
  const { name, state, handleBlur, handleChange } = useFieldContext<string>()
  const isSubmitted = useStore(
    form.store,
    (store) => store.submissionAttempts > 0,
  )

  const displayError =
    (state.meta.isTouched && state.meta.isBlurred) || isSubmitted

  return (
    <Field>
      {label && <FieldLabel htmlFor={name}>{label}</FieldLabel>}
      <Input
        id={name}
        name={name}
        value={state.value}
        type={type}
        onBlur={handleBlur}
        onChange={(e) => handleChange(e.target.value)}
      />
      {displayError && <FieldError errors={state.meta.errors} />}
    </Field>
  )
}
