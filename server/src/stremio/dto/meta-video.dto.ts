import { ApiProperty } from '@nestjs/swagger';

export class MetaVideoDto {
  /**
   * ID of the video.
   */
  @ApiProperty()
  id: string;
  /**
   * Title of the video.
   */
  @ApiProperty()
  title: string;
  /**
   * ISO 8601, publish date of the video.
   *
   * for episodes, this should be the initial air date.
   *
   * e.g. "2010-12-06T05:00:00.000Z"
   */
  @ApiProperty({ type: 'string', required: false })
  released?: string;
  /**
   * URL to png of the video thumbnail, in the video's aspect ratio.
   *
   * max file size 5kb.
   */
  @ApiProperty({ required: false })
  thumbnail?: string;
  /**
   * Set to true to explicitly state that this video is available for streaming, from your addon.
   *
   * No need to use this if you've passed stream.
   */
  @ApiProperty({ required: false })
  available?: boolean;
  /**
   * Episode number, if applicable.
   */
  @ApiProperty({ required: false })
  episode?: number;
  /**
   * Season number, if applicable.
   */
  @ApiProperty({ required: false })
  season?: number;
  /**
   * YouTube ID of the trailer video; use if this is an episode for a series.
   */
  @ApiProperty({ required: false })
  trailer?: string;
  /**
   * Video overview/summary
   */
  @ApiProperty({ required: false })
  overview?: string;
}
