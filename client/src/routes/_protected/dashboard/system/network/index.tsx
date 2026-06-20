import { Link, createFileRoute } from '@tanstack/react-router'
import type { SyntheticEvent } from 'react'

import { NetworkSelector } from '@/routes/_protected/dashboard/system/network/-features/network-access/network-selector'
import { UrlConfiguration } from '@/routes/_protected/dashboard/system/network/-features/network-access/url-configuration'
import { Button } from '@/shared/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/shared/components/ui/card'
import { Separator } from '@/shared/components/ui/separator'

import { useNetworkAccessForm } from './-features/network-access/use-network-access-form'
import { DASHBOARD_SYSTEM_NETWORK_NAME } from './route'

export const Route = createFileRoute('/_protected/dashboard/system/network/')({
  component: RouteComponent,
})

function RouteComponent() {
  const form = useNetworkAccessForm()

  const handleSubmit = async (e: SyntheticEvent<HTMLFormElement>) => {
    e.preventDefault()
    e.stopPropagation()
    await form.handleSubmit()
  }

  return (
    <Card>
      <form.AppForm>
        <form className="grid gap-6" onSubmit={handleSubmit}>
          <CardHeader>
            <CardTitle>{DASHBOARD_SYSTEM_NETWORK_NAME}</CardTitle>
            <CardDescription>
              {DASHBOARD_SYSTEM_NETWORK_NAME} frissítése vagy új konfiguráció
              alkalmazása.
            </CardDescription>
          </CardHeader>

          <Separator />

          <CardContent className="grid gap-4">
            <NetworkSelector form={form} />
            <UrlConfiguration form={form} />
          </CardContent>

          <CardFooter className="gap-4 justify-end">
            <Button variant="outline" asChild>
              <Link to="/dashboard/system">Mégsem</Link>
            </Button>
            <form.Subscribe
              selector={(state) => ({
                mode: state.values.mode,
                isSubmitting: state.isSubmitting,
              })}
            >
              {({ mode, isSubmitting }) => {
                if (mode === 'none') return null

                return (
                  <Button type="submit" disabled={isSubmitting}>
                    Alkalmazás
                  </Button>
                )
              }}
            </form.Subscribe>
          </CardFooter>
        </form>
      </form.AppForm>
    </Card>
  )
}
