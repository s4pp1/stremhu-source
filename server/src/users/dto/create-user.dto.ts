import { IsOptional, IsString, MinLength } from 'class-validator';

export class CreateUserDto {
  /** Felhasználónév */
  @IsString()
  username: string;

  /** Jelszó */
  @IsOptional()
  @IsString()
  @MinLength(1, { message: 'A jelszó nem lehet üres' })
  password: string | null;
}
