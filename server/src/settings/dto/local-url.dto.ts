import { IsString } from 'class-validator';

export class LocalUrlDto {
  /** Helyi elérési út */
  @IsString()
  localUrl: string;
}
