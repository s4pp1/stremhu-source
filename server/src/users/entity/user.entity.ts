import { Resolution } from '@ctrl/video-filename-parser';
import { Column, Entity, Index, PrimaryGeneratedColumn } from 'typeorm';

import { LanguageEnum } from 'src/common/enums/language.enum';

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
  @Column({ name: 'stremio_token', type: 'uuid' })
  stremioToken: string;

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
}
