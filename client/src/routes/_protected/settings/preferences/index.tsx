import { createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/_protected/settings/preferences/')({
  component: RouteComponent,
})

function RouteComponent() {
  return <div>Hello "/_protected/preferences/"!</div>
}
