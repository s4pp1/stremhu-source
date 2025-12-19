import {
  Column,
  CreateDateColumn,
  Entity,
  PrimaryColumn,
  Unique,
  UpdateDateColumn,
} from 'typeorm';

import { TrackerEnum } from 'src/trackers/enum/tracker.enum';

@Entity('web_torrent_runs')
@Unique('unique_torrent_imdb_id_tracker_torrent_id', [
  'imdbId',
  'tracker',
  'torrentId',
])
export class WebTorrentRun {
  @PrimaryColumn({ name: 'info_hash' })
  infoHash!: string;

  @Column({ name: 'imdb_id' })
  imdbId!: string;

  @Column({ type: 'simple-enum', enum: TrackerEnum })
  tracker!: TrackerEnum;

  @Column({ name: 'torrent_id' })
  torrentId!: string;

  @Column({ type: 'integer', default: 0 })
  uploaded: number;

  @Column({ name: 'is_persisted', type: 'boolean', default: false })
  isPersisted: boolean;

  @Column({
    name: 'last_played_at',
    type: 'datetime',
    nullable: true,
    default: null,
  })
  lastPlayedAt: Date | null;

  @UpdateDateColumn({ name: 'updated_at' })
  updatedAt: Date;

  @CreateDateColumn({ name: 'created_at' })
  createdAt: Date;
}
