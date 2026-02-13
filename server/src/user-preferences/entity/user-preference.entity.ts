import { Column, Entity, JoinColumn, ManyToOne, PrimaryColumn } from 'typeorm';

import { AudioQualityEnum } from 'src/preference-items/enum/audio-quality.enum';
import { LanguageEnum } from 'src/preference-items/enum/language.enum';
import { ResolutionEnum } from 'src/preference-items/enum/resolution.enum';
import { SourceEnum } from 'src/preference-items/enum/source.enum';
import { VideoQualityEnum } from 'src/preference-items/enum/video-quality.enum';
import { PreferenceEnum } from 'src/preferences/enum/preference.enum';
import { TrackerEnum } from 'src/trackers/enum/tracker.enum';
import { User } from 'src/users/entity/user.entity';

@Entity('user_preferences')
export class UserPreference {
  @PrimaryColumn({ type: 'text' })
  preference: PreferenceEnum;

  @ManyToOne(() => User, { onDelete: 'CASCADE' })
  @JoinColumn({ name: 'user_id' })
  user?: User;

  @PrimaryColumn({ name: 'user_id' })
  userId: string;

  @Column({
    type: 'simple-json',
  })
  preferred: Array<
    | LanguageEnum
    | ResolutionEnum
    | VideoQualityEnum
    | SourceEnum
    | AudioQualityEnum
    | TrackerEnum
  >;

  @Column({
    type: 'simple-json',
  })
  blocked: Array<
    | LanguageEnum
    | ResolutionEnum
    | VideoQualityEnum
    | SourceEnum
    | AudioQualityEnum
    | TrackerEnum
  >;

  @Column({ type: 'int', nullable: true })
  order: number | null;
}
