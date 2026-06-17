import { LinkIcon, PlayIcon, UserIcon } from 'lucide-react'

import { Badge } from '@/shared/components/ui/badge'
import {
  Item,
  ItemContent,
  ItemDescription,
  ItemTitle,
} from '@/shared/components/ui/item'
import { Progress } from '@/shared/components/ui/progress'
import type {
  PlaybackHistoryResponse,
  PlaybackResponse,
} from '@/shared/lib/source/source-client'
import { formatDateTime } from '@/shared/lib/utils'

type PlaybackItemProps = {
  playback: PlaybackResponse | PlaybackHistoryResponse
}

export function PlaybackItem(props: PlaybackItemProps) {
  const { playback } = props

  return (
    <div className="grid gap-2 border border-transparent rounded-md bg-muted/50 p-4">
      {'progress' in playback ? <Progress value={playback.progress} /> : null}
      <Item className="p-0">
        <ItemContent>
          <ItemTitle className="line-clamp-2 break-all">
            {playback.torrentName}
          </ItemTitle>
          <ItemDescription className="break-all">
            {playback.fileName}
          </ItemDescription>
        </ItemContent>
      </Item>
      <div className="grid gap-2 text-muted-foreground text-sm font-normal">
        <div className="flex flex-wrap gap-2">
          <Badge
            variant="secondary"
            title={`Forrás: ${playback.indexerDefinition.name}`}
          >
            <LinkIcon />
            {playback.indexerDefinition.name}
          </Badge>

          <Badge
            variant="secondary"
            title={`Felhasználó: ${playback.user.username}`}
          >
            <UserIcon />
            {playback.user.username}
          </Badge>

          <Badge
            variant="secondary"
            title={`Lejátszás időpontja: ${formatDateTime(playback.createdAt)}`}
          >
            <PlayIcon />
            {formatDateTime(playback.createdAt)}
          </Badge>
        </div>
      </div>
    </div>
  )
}
