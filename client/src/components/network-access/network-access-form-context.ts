import { createFormHook, createFormHookContexts } from '@tanstack/react-form'

type DefaultValues = {
  connection: 'idle' | 'pending' | 'success' | 'error'
  enebledlocalIp: boolean
  address: string
}

export const defaultValues: DefaultValues = {
  connection: 'idle',
  enebledlocalIp: false,
  address: '',
}

export const { fieldContext, formContext, useFieldContext, useFormContext } =
  createFormHookContexts()

export const { useAppForm, withForm } = createFormHook({
  fieldContext,
  formContext,
  fieldComponents: {},
  formComponents: {},
})
