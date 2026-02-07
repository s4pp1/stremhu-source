import type { ClassValue } from 'clsx'
import { clsx } from 'clsx'
import { format } from 'date-fns'
import _ from 'lodash'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: Array<ClassValue>) {
  return twMerge(clsx(inputs))
}

export function parseApiError(error: unknown): string {
  let message = 'Váratlan hiba történt, próbáld újra!'

  const errorMessage: string | Array<string> = _.get(error, ['body', 'message'])

  if (errorMessage) {
    if (_.isArray(errorMessage)) {
      message = errorMessage.join('\n')
    } else {
      message = errorMessage
    }
  }

  return message
}

export const sleep = (ms: number) =>
  new Promise((resolve) => setTimeout(resolve, ms))

export function assertExists<T>(value: T): asserts value is NonNullable<T> {
  if (!value) {
    throw new Error('A store nem érhető el!')
  }
}

export function formatDateTime(dateTime: string) {
  return format(dateTime, 'yyyy.MM.dd. HH:mm')
}
