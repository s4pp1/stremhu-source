import { Expose } from 'class-transformer';

import { UserDto } from 'src/users/dto/user.dto';

export class MeDto {
  /** Saját felhasználói adatok */
  @Expose()
  me: UserDto | null;
}
