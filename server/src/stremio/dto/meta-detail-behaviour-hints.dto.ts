import { Expose } from 'class-transformer';

export class MetaDetailBehaviorHintsDto {
  /**
   * Alapértelmezett videó azonosító.
   * Ha meg van adva, a részletező oldal közvetlenül ennek a videónak a streamjeit nyitja meg.
   */
  @Expose()
  defaultVideoId?: string;

  /** Vannak-e időzített videók */
  @Expose()
  hasScheduledVideos?: boolean;
}
