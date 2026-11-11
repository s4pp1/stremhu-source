import { useQueries } from '@tanstack/react-query'
import { InfoIcon, TriangleAlertIcon } from 'lucide-react'
import { toast } from 'sonner'

import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/shared/components/ui/accordion'
import {
  Alert,
  AlertDescription,
  AlertTitle,
} from '@/shared/components/ui/alert'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/shared/components/ui/card'
import { Label } from '@/shared/components/ui/label'
import { Switch } from '@/shared/components/ui/switch'
import { assertExists, parseApiError } from '@/shared/lib/utils'
import { getMe, useUpdateMe } from '@/shared/queries/me'

export function SubtitleSettingsCard() {
  const [{ data: me }] = useQueries({
    queries: [getMe()],
  })
  assertExists(me)

  const { mutateAsync: updateMe, isPending } = useUpdateMe()

  const handleToggle = async (checked: boolean) => {
    try {
      await updateMe({
        enableFallbackSubtitles: checked,
      })
    } catch (error) {
      const message = parseApiError(error)
      toast.error(message)
    }
  }

  return (
    <Card className="break-inside-avoid mb-4">
      <CardHeader>
        <CardTitle>Torrent feliratok</CardTitle>
        <CardDescription>
          Külső feliratfájlok (.srt, .ass) kezelése, ha a kiválasztott torrent
          nem tartalmaz saját különálló feliratot.
        </CardDescription>
      </CardHeader>
      <CardContent className="grid gap-4">
        <div className="grid gap-1.5">
          <Label
            htmlFor="enable-fallback-subtitles"
            className="flex items-start gap-3 cursor-pointer"
          >
            <Switch
              id="enable-fallback-subtitles"
              checked={Boolean(me.enableFallbackSubtitles)}
              disabled={isPending}
              onCheckedChange={handleToggle}
            />
            <span className="flex-1 text-sm leading-tight font-medium">
              Felirat kölcsönzése más találatból
            </span>
          </Label>
          <p className="text-muted-foreground text-xs pl-11">
            Csak olyan forrásnál (pl. nCore) aktív, ahol nincs bekapcsolva a
            teljes torrent letöltése.
          </p>
        </div>

        {me.enableFallbackSubtitles && (
          <Alert variant="destructive">
            <TriangleAlertIcon />
            <AlertTitle>Dupla seedkötelezettség (Hit'n'Run)</AlertTitle>
            <AlertDescription>
              <p>
                Amikor a rendszer egy másik találati torrentből tölti be a
                feliratot, a videó torrentje mellett a feliratot adó torrent is
                elindul, így{' '}
                <strong>két torrent jelenik meg mint seedkötelezett</strong>!
              </p>
            </AlertDescription>
          </Alert>
        )}

        <Accordion
          type="single"
          collapsible
          className="w-full border rounded-md px-3"
        >
          <AccordionItem value="info">
            <AccordionTrigger className="py-2.5 text-xs font-medium text-muted-foreground hover:no-underline">
              <span className="flex items-center gap-2">
                <InfoIcon className="size-4 shrink-0" />
                Működés és seedkötelezettség tájékoztató
              </span>
            </AccordionTrigger>
            <AccordionContent className="text-xs text-muted-foreground space-y-2 pb-3">
              <p>
                <strong>Hogyan működik?</strong> Ha az elindított torrentben
                nincs különálló feliratfájl (<code>.srt</code>,{' '}
                <code>.ass</code>), a bekapcsolt opcióval a StremHU megpróbál
                magyar feliratot kölcsönözni a többi találati torrent egyikéből.
              </p>
              <p>
                <strong>Teljes torrent letöltése védelem:</strong> A kölcsönzés
                csak akkor történik meg, ha az adott forrásnál (pl. nCore)
                <strong> nincs beállítva a „Teljes torrent letöltése”</strong>,
                így elkerülhető egy második teljes csomag letöltése.
              </p>
              <p className="text-destructive font-medium">
                ⚠️ Figyelem: Mivel a feliratfájl megszerzéséhez a másik
                torrentből is le kell tölteni néhány adatdarabot (piece-t), a
                tracker oldalon két külön torrent jelenik meg mint
                seedkötelezett (Hit'n'Run)! A modern <code>.mkv</code> kiadások
                többsége egyébként már beágyazva tartalmazza a feliratot.
              </p>
            </AccordionContent>
          </AccordionItem>
        </Accordion>
      </CardContent>
    </Card>
  )
}
