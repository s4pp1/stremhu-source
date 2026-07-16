import { AlertCircleIcon } from 'lucide-react'
import { Trans } from '@lingui/react/macro'

import { Alert, AlertDescription, AlertTitle } from './ui/alert'
import { Button } from './ui/button'

type DefaultError = {
  error: Error
}

export function DefaultError(props: DefaultError) {
  const { error } = props

  return (
    <div className="flex justify-center py-4">
      <Alert variant="default" className="max-w-md">
        <AlertCircleIcon className="stroke-destructive" />
        <AlertTitle className="text-destructive">
          <Trans>An error occurred while loading StremHU Source!</Trans>
        </AlertTitle>
        <AlertDescription>
          <p className="font-mono">{error.message}</p>
          <div className="w-full flex justify-end">
            <Button
              variant="outline"
              size="sm"
              onClick={() => window.location.reload()}
            >
              <Trans>Reload</Trans>
            </Button>
          </div>
        </AlertDescription>
      </Alert>
    </div>
  )
}
