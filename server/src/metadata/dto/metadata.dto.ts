import { ApiProperty } from '@nestjs/swagger';
import { IsArray, IsString } from 'class-validator';

import { HealthDto } from 'src/common/dto/health.dto';

import { LanguageDto } from './language.dto';
import { ResolutionDto } from './resolution.dto';
import { TrackerMetaDto } from './tracker-meta.dto';
import { UserRoleDto } from './user-role.dto';
import { VideoQualityDto } from './video-quality.dto';

export class MetadataDto extends HealthDto {
  @IsArray()
  @ApiProperty({ type: UserRoleDto, isArray: true })
  userRoles: UserRoleDto[];

  @IsArray()
  @ApiProperty({ type: ResolutionDto, isArray: true })
  resolutions: ResolutionDto[];

  @IsArray()
  @ApiProperty({ type: VideoQualityDto, isArray: true })
  videoQualities: VideoQualityDto[];

  @IsArray()
  @ApiProperty({ type: LanguageDto, isArray: true })
  languages: LanguageDto[];

  @IsArray()
  @ApiProperty({ type: TrackerMetaDto, isArray: true })
  trackers: TrackerMetaDto[];

  @IsString()
  @ApiProperty()
  endpoint: string;
}
