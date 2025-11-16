import { createFileRoute, redirect } from '@tanstack/react-router'

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { getMe } from '@/queries/me'

import { LoginForm } from './-components/login-form'

export const Route = createFileRoute('/login/')({
  beforeLoad: async ({ context }) => {
    const queryClient = context.queryClient

    const me = await queryClient.ensureQueryData(getMe)

    if (me !== null) {
      throw redirect({ to: '/' })
    }
  },
  component: LoginRoute,
})

function LoginRoute() {
  return (
    <div className="flex flex-col items-center py-10">
      <Card className="w-sm">
        <CardHeader>
          <CardTitle>Bejelentkezés a fiókodba</CardTitle>
          <CardDescription>
            Add meg felhasználóneved és jelszavad a bejelentkezéshez
          </CardDescription>
        </CardHeader>
        <CardContent>
          <LoginForm />
        </CardContent>
      </Card>
    </div>
  )
}
