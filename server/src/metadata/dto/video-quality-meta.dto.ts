import { ApiProperty } from '@nestjs/swagger';
import { IsEnum, IsString } from 'class-validator';

import { VideoQualityEnum } from 'src/preference-items/enum/video-quality.enum';

export class VideoQualityMetaDto {
  /** Videó minőség értéke */
  @IsEnum(VideoQualityEnum)
  @ApiProperty({ enum: VideoQualityEnum, enumName: 'VideoQualityEnum' })
  value: VideoQualityEnum;

  /** Megjelenített név */
  @IsString()
  label: string;
}
