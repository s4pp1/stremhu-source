import { AlertCircleIcon } from 'lucide-react'

import { Alert, AlertDescription, AlertTitle } from './ui/alert'
import { Button } from './ui/button'

type DefaultErrorProps = {
  error: unknown
}

export function DefaultError(props: DefaultErrorProps) {
  const { error } = props

  const errorMessage = error instanceof Error ? error.message : String(error)

  return (
    <div className="flex justify-center py-4">
      <Alert variant="default" className="max-w-md">
        <AlertCircleIcon className="stroke-destructive" />
        <AlertTitle className="text-destructive">
          Hiba történt az StremHU Source betöltése közben!
        </AlertTitle>
        <AlertDescription>
          <p className="font-mono">{errorMessage}</p>
          <div className="w-full flex justify-end">
            <Button
              variant="outline"
              size="sm"
              onClick={() => window.location.reload()}
            >
              Újratöltés
            </Button>
          </div>
        </AlertDescription>
      </Alert>
    </div>
  )
}
