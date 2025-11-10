import { Resolution as ResolutionEnum } from '@ctrl/video-filename-parser';
import { ApiProperty } from '@nestjs/swagger';
import { IsEnum, IsString } from 'class-validator';

export class ResolutionDto {
  @IsEnum(ResolutionEnum)
  @ApiProperty({ enum: ResolutionEnum, enumName: 'ResolutionEnum' })
  value: ResolutionEnum;

  @IsString()
  @ApiProperty()
  label: string;
}
