export class PairInitDto {
  /** A 4 jegyű kód, amit a felhasználónak be kell gépelnie */
  userCode: string;

  /** Az eszköz egyedi azonosítója a státusz lekérdezéséhez */
  deviceCode: string;

  /** A kód lejárati ideje */
  expiresAt: Date;
}
