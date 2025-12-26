import { Resolution } from '@ctrl/video-filename-parser';
import {
  Column,
  CreateDateColumn,
  Entity,
  Index,
  PrimaryGeneratedColumn,
  UpdateDateColumn,
} from 'typeorm';

import { LanguageEnum } from 'src/common/enum/language.enum';
import { VideoQualityEnum } from 'src/stremio/streams/enum/video-quality.enum';

import { UserRoleEnum } from '../enum/user-role.enum';

@Entity('users')
export class User {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @Column({ unique: true })
  username: string;

  @Column({ name: 'password_hash', type: 'text', nullable: true })
  passwordHash: string | null;

  @Index()
  @Column({ name: 'token', type: 'uuid' })
  token: string;

  @Column({
    name: 'user_role',
    type: 'simple-enum',
    enum: UserRoleEnum,
  })
  userRole: UserRoleEnum;

  @Column({
    name: 'torrent_resolutions',
    type: 'simple-json',
    default: JSON.stringify(Object.values(Resolution)),
  })
  torrentResolutions: Resolution[];

  @Column({
    name: 'torrent_video_qualities',
    type: 'simple-json',
    default: JSON.stringify(Object.values(VideoQualityEnum)),
  })
  torrentVideoQualities: VideoQualityEnum[];

  @Column({
    name: 'torrent_languages',
    type: 'simple-json',
    default: JSON.stringify(Object.values(LanguageEnum)),
  })
  torrentLanguages: LanguageEnum[];

  @Column({
    name: 'torrent_seed',
    type: 'integer',
    nullable: true,
    default: null,
  })
  torrentSeed: number | null;

  @Column({ name: 'only_best_torrent', type: 'boolean', default: false })
  onlyBestTorrent!: boolean;

  @UpdateDateColumn({ name: 'updated_at' })
  updatedAt: Date;

  @CreateDateColumn({ name: 'created_at' })
  createdAt: Date;
}
