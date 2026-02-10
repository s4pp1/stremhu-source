import { Resolution } from '@ctrl/video-filename-parser';
import {
  Column,
  CreateDateColumn,
  Entity,
  Index,
  PrimaryGeneratedColumn,
  UpdateDateColumn,
} from 'typeorm';

import { AudioCodecEnum } from 'src/preference-items/enum/audio-codec.enum';
import { LanguageEnum } from 'src/preference-items/enum/language.enum';
import { SourceTypeEnum } from 'src/preference-items/enum/source-type.enum';
import { VideoQualityEnum } from 'src/preference-items/enum/video-quality.enum';

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
    name: 'torrent_audio_codecs',
    type: 'simple-json',
    default: JSON.stringify(Object.values(AudioCodecEnum)),
  })
  torrentAudioCodecs: AudioCodecEnum[];

  @Column({
    name: 'torrent_source_types',
    type: 'simple-json',
    default: JSON.stringify(Object.values(SourceTypeEnum)),
  })
  torrentSourceTypes: SourceTypeEnum[];

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
