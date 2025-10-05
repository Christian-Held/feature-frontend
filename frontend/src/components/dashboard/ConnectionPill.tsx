import { useJobEvents } from '../../hooks/useJobEvents'
import { Badge } from '../ui/Badge'

const statusText: Record<ReturnType<typeof useJobEvents>, string> = {
  connecting: 'Connecting…',
  open: 'Live updates',
  closed: 'Reconnecting…',
  error: 'Connection issue',
}

export function ConnectionPill() {
  const status = useJobEvents()
  return <Badge variant={status === 'open' ? 'running' : status === 'error' ? 'failed' : 'pending'}>{statusText[status]}</Badge>
}
