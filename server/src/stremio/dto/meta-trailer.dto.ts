import { Expose } from 'class-transformer';

export class MetaTrailerDto {
  /** YouTube azonosító */
  @Expose()
  ytId: string;

  /** Előzetes leírása */
  @Expose()
  description: string;
}
