import { ApiProperty } from '@nestjs/swagger';
import { Expose } from 'class-transformer';
import { IsEnum, IsString } from 'class-validator';

import { VideoQualityEnum } from 'src/preference-items/enum/video-quality.enum';

export class VideoQualityMetaDto {
  /** Videó minőség értéke */
  @Expose()
  @IsEnum(VideoQualityEnum)
  @ApiProperty({ enum: VideoQualityEnum, enumName: 'VideoQualityEnum' })
  value: VideoQualityEnum;

  /** Megjelenített név */
  @Expose()
  @IsString()
  label: string;
}
