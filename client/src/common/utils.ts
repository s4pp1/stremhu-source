import _ from 'lodash'

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
