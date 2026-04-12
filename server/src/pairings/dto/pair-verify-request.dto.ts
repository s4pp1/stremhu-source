import { IsString } from 'class-validator';

export class PairVerifyRequestDto {
  /** A megjelenő 4 jegyű kód */
  @IsString()
  userCode: string;
}
