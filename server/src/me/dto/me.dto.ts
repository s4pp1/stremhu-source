import { Expose, Type } from 'class-transformer';

import { UserDto } from 'src/users/dto/user.dto';

export class MeDto {
  /** Saját felhasználói adatok */
  @Type(() => UserDto)
  @Expose()
  me: UserDto | null;
}
