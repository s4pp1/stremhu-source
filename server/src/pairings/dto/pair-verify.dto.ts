import { Expose } from 'class-transformer';

export class PairVerifyDto {
  /** Sikeres volt-e a párosítás jóváhagyása */
  @Expose()
  success: boolean;
}
