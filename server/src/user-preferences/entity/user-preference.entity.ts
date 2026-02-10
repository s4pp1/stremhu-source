import { Column, Entity, JoinColumn, ManyToOne, PrimaryColumn } from 'typeorm';

import { AudioCodecEnum } from 'src/preference-items/enum/audio-codec.enum';
import { LanguageEnum } from 'src/preference-items/enum/language.enum';
import { SourceTypeEnum } from 'src/preference-items/enum/source-type.enum';
import { VideoQualityEnum } from 'src/preference-items/enum/video-quality.enum';
import { PreferenceEnum } from 'src/preferences/enum/preference.enum';
import { User } from 'src/users/entity/user.entity';

@Entity('user_preferences')
export class UserPreference {
  @PrimaryColumn({ type: 'text' })
  preference: PreferenceEnum;

  @ManyToOne(() => User, { onDelete: 'CASCADE' })
  @JoinColumn({ name: 'user_id' })
  user: User;

  @PrimaryColumn({ name: 'user_id' })
  userId: string;

  @Column({
    name: 'preferred',
    type: 'simple-json',
  })
  preferred: Array<
    LanguageEnum | VideoQualityEnum | SourceTypeEnum | AudioCodecEnum
  >;

  @Column({
    name: 'blocked',
    type: 'simple-json',
  })
  blocked: Array<
    LanguageEnum | VideoQualityEnum | SourceTypeEnum | AudioCodecEnum
  >;

  @Column({ type: 'int', nullable: true })
  order: number | null;
}
