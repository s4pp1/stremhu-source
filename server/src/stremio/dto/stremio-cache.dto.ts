export class StremioCacheDto {
  /**
   * (másodpercben) Beállítja a Cache-Control fejléc max-age értékét ($cacheMaxAge).
   * Felülírja a serveHTTP opciókban megadott globális cache időt.
   */
  cacheMaxAge?: number;

  /**
   * (másodpercben) Beállítja a Cache-Control fejléc stale-while-revalidate értékét ($staleRevalidate).
   */
  staleRevalidate?: number;

  /**
   * (másodpercben) Beállítja a Cache-Control fejléc stale-if-error értékét ($staleError).
   */
  staleError?: number;
}
