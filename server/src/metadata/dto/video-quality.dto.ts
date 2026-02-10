import { ApiProperty } from '@nestjs/swagger';
import { IsEnum, IsString } from 'class-validator';

import { VideoQualityEnum } from 'src/preference-items/enum/video-quality.enum';

export class VideoQualityDto {
  @IsEnum(VideoQualityEnum)
  @ApiProperty({ enum: VideoQualityEnum, enumName: 'VideoQualityEnum' })
  value: VideoQualityEnum;

  @IsString()
  @ApiProperty()
  label: string;
}
