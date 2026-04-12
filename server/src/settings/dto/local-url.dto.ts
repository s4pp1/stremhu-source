import { Expose } from 'class-transformer';
import { IsString } from 'class-validator';

export class LocalUrlDto {
  /** Helyi elérési út */
  @IsString()
  @Expose()
  localUrl: string;
}
