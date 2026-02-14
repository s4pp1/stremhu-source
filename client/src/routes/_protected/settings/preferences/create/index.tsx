import { createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/_protected/settings/preferences/create/')({
  component: RouteComponent,
})

function RouteComponent() {
  return <div>Hello "/_protected/preferences/create/"!</div>
}
