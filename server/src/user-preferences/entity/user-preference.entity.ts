import { Column, Entity, JoinColumn, ManyToOne, PrimaryColumn } from 'typeorm';

import { PreferenceEnum } from 'src/preferences/enum/preference.enum';
import { User } from 'src/users/entity/user.entity';

import { PreferenceValue } from '../type/preference-value.type';

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
  preferred: Array<PreferenceValue>;

  @Column({
    type: 'simple-json',
  })
  blocked: Array<PreferenceValue>;

  @Column({ type: 'int', nullable: true })
  order: number | null;
}
