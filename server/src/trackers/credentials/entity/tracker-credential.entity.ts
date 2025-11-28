import { Column, Entity, PrimaryColumn } from 'typeorm';

import { TrackerEnum } from 'src/trackers/enum/tracker.enum';

@Entity('tracker_credentials')
export class TrackerCredential {
  @PrimaryColumn({ type: 'simple-enum', enum: TrackerEnum })
  tracker!: TrackerEnum;

  @Column({ type: 'text' })
  username!: string;

  @Column({ type: 'text' })
  password!: string;
}
