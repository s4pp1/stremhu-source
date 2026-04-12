export class MetaDetailBehaviorHintsDto {
  /**
   * Alapértelmezett videó azonosító.
   * Ha meg van adva, a részletező oldal közvetlenül ennek a videónak a streamjeit nyitja meg.
   */
  defaultVideoId?: string;

  /** Vannak-e időzített videók */
  hasScheduledVideos?: boolean;
}
