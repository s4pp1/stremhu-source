import { IsString } from 'class-validator';

export class AuthLoginDto {
  /** Felhasználónév */
  @IsString()
  username: string;

  /** Jelszó */
  @IsString()
  password: string;
}
