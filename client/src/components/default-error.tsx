import type { ErrorComponentProps } from '@tanstack/react-router'
import { AlertCircleIcon } from 'lucide-react'

import { Alert, AlertDescription, AlertTitle } from './ui/alert'
import { Button } from './ui/button'

export function DefaultError(props: ErrorComponentProps) {
  const { error } = props

  return (
    <div className="flex justify-center py-4">
      <Alert variant="default" className="max-w-sm">
        <AlertCircleIcon className="stroke-destructive" />
        <AlertTitle className="text-destructive">
          Hiba történt az StremHU Source betöltése közben!
        </AlertTitle>
        <AlertDescription>
          <p className="font-mono">{error.message}</p>
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
