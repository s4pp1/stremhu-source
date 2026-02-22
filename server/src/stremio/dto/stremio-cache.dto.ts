import { ApiProperty } from '@nestjs/swagger';

export class StremioCacheDto {
  /**
   * (in seconds) sets the Cache-Control header to max-age=$cacheMaxAge
   * and overwrites the global cache time set in serveHTTP options.
   */
  @ApiProperty({ required: false })
  cacheMaxAge?: number;
  /**
   * (in seconds) sets the Cache-Control header to stale-while-revalidate=$staleRevalidate.
   */
  @ApiProperty({ required: false })
  staleRevalidate?: number;
  /**
   * (in seconds) sets the Cache-Control header to stale-if-error=$staleError.
   */
  @ApiProperty({ required: false })
  staleError?: number;
}
