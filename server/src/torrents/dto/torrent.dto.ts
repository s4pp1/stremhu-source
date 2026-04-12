import { ApiProperty } from '@nestjs/swagger';
import { Expose } from 'class-transformer';

import { TrackerEnum } from 'src/trackers/enum/tracker.enum';

export class TorrentDto {
  /** Tracker azonosító */
  @Expose()
  @ApiProperty({ enum: TrackerEnum, enumName: 'TrackerEnum' })
  tracker: TrackerEnum;

  /** Torrent neve */
  @Expose()
  name: string;

  /** Letöltési sebesség */
  @Expose()
  downloadSpeed: number;

  /** Feltöltési sebesség */
  @Expose()
  uploadSpeed: number;

  /** Haladás (0-1) */
  @Expose()
  progress: number;

  /** Letöltött adat mennyisége */
  @Expose()
  downloaded: number;

  /** Feltöltött adat mennyisége */
  @Expose()
  uploaded: number;

  /** Teljes méret */
  @Expose()
  total: number;

  /** Info hash */
  @Expose()
  infoHash: string;

  /** Egyedi torrent azonosító */
  @Expose()
  torrentId: string;

  /** Mentve van-e az adatbázisba */
  @Expose()
  isPersisted: boolean;

  /** Teljes letöltés állapota */
  @Expose()
  fullDownload: boolean | null;

  /** Utolsó lejátszás időpontja */
  @Expose()
  lastPlayedAt: Date;

  /** Utolsó frissítés időpontja */
  @Expose()
  updatedAt: Date;

  /** Létrehozás időpontja */
  @Expose()
  createdAt: Date;
}
