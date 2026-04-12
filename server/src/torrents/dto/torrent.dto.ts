import { ApiProperty } from '@nestjs/swagger';

import { TrackerEnum } from 'src/trackers/enum/tracker.enum';

export class TorrentDto {
  /** Tracker azonosító */
  @ApiProperty({ enum: TrackerEnum, enumName: 'TrackerEnum' })
  tracker: TrackerEnum;

  /** Torrent neve */
  name: string;

  /** Letöltési sebesség */
  downloadSpeed: number;

  /** Feltöltési sebesség */
  uploadSpeed: number;

  /** Haladás (0-1) */
  progress: number;

  /** Letöltött adat mennyisége */
  downloaded: number;

  /** Feltöltött adat mennyisége */
  uploaded: number;

  /** Teljes méret */
  total: number;

  /** Info hash */
  infoHash: string;

  /** Egyedi torrent azonosító */
  torrentId: string;

  /** Mentve van-e az adatbázisba */
  isPersisted: boolean;

  /** Teljes letöltés állapota */
  fullDownload: boolean | null;

  /** Utolsó lejátszás időpontja */
  lastPlayedAt: Date;

  /** Utolsó frissítés időpontja */
  updatedAt: Date;

  /** Létrehozás időpontja */
  createdAt: Date;
}
