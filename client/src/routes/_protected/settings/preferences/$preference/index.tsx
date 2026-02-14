import { createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/_protected/settings/preferences/$preference/')({
  component: RouteComponent,
})

function RouteComponent() {
  return <div>Hello "/_protected/preferences/$preference/"!</div>
}
