export class MetaVideoDto {
  /**
   * ID of the video.
   */
  id: string;

  /**
   * Title of the video.
   */
  title: string;

  /**
   * ISO 8601, publish date of the video.
   *
   * for episodes, this should be the initial air date.
   *
   * e.g. "2010-12-06T05:00:00.000Z"
   */
  released?: string;

  /**
   * URL to png of the video thumbnail, in the video's aspect ratio.
   *
   * max file size 5kb.
   */
  thumbnail?: string;

  /**
   * Set to true to explicitly state that this video is available for streaming, from your addon.
   *
   * No need to use this if you've passed stream.
   */
  available?: boolean;

  /**
   * Episode number, if applicable.
   */
  episode?: number;

  /**
   * Season number, if applicable.
   */
  season?: number;

  /**
   * YouTube ID of the trailer video; use if this is an episode for a series.
   */
  trailer?: string;

  /**
   * Video overview/summary
   */
  overview?: string;
}
