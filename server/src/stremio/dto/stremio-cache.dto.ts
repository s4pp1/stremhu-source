import { Expose } from 'class-transformer';

export class StremioCacheDto {
  /**
   * (másodpercben) Beállítja a Cache-Control fejléc max-age értékét ($cacheMaxAge).
   * Felülírja a serveHTTP opciókban megadott globális cache időt.
   */
  @Expose()
  cacheMaxAge?: number;

  /**
   * (másodpercben) Beállítja a Cache-Control fejléc stale-while-revalidate értékét ($staleRevalidate).
   */
  @Expose()
  staleRevalidate?: number;

  /**
   * (másodpercben) Beállítja a Cache-Control fejléc stale-if-error értékét ($staleError).
   */
  @Expose()
  staleError?: number;
}
