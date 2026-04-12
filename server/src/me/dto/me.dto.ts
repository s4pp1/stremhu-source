import { UserDto } from 'src/users/dto/user.dto';

export class MeDto {
  /** Saját felhasználói adatok */
  me: UserDto | null;
}
