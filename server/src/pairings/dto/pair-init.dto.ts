import { Expose } from 'class-transformer';

export class PairInitDto {
  /** A 4 jegyű kód, amit a felhasználónak be kell gépelnie */
  @Expose()
  userCode: string;

  /** Az eszköz egyedi azonosítója a státusz lekérdezéséhez */
  @Expose()
  deviceCode: string;

  /** A kód lejárati ideje */
  @Expose()
  expiresAt: Date;
}
