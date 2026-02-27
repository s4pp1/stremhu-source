import { ApiProperty } from '@nestjs/swagger';
import { IsArray } from 'class-validator';

import { AudioQualityMetaDto } from 'src/metadata/dto/audio-quality-meta.dto';
import { AudioSpatialMetaDto } from 'src/metadata/dto/audio-spatial-meta.dto';
import { LanguageMetaDto } from 'src/metadata/dto/language-meta.dto';
import { ResolutionMetaDto } from 'src/metadata/dto/resolution-meta.dto';
import { SourceMetaDto } from 'src/metadata/dto/source-meta.dto';
import { TrackerMetaDto } from 'src/metadata/dto/tracker-meta.dto';
import { VideoQualityMetaDto } from 'src/metadata/dto/video-quality-meta.dto';

export class KodiImdbStreamDto {
  @ApiProperty({ type: 'string' })
  torrentName: string;

  @ApiProperty({ type: 'string' })
  fileName: string;

  @ApiProperty({ type: 'integer' })
  seeders: number;

  @ApiProperty({ type: 'string' })
  size: string;

  @ApiProperty({
    type: TrackerMetaDto,
  })
  tracker: TrackerMetaDto;

  @IsArray()
  @ApiProperty({
    type: LanguageMetaDto,
    isArray: true,
  })
  languages: LanguageMetaDto[];

  @ApiProperty({
    type: ResolutionMetaDto,
  })
  resolution: ResolutionMetaDto;

  @IsArray()
  @ApiProperty({
    type: VideoQualityMetaDto,
    isArray: true,
  })
  videoQualities: VideoQualityMetaDto[];

  @ApiProperty({
    type: AudioQualityMetaDto,
    required: false,
  })
  audioQuality?: AudioQualityMetaDto;

  @ApiProperty({
    type: AudioSpatialMetaDto,
    required: false,
  })
  audioSpatial?: AudioSpatialMetaDto;

  @ApiProperty({
    type: SourceMetaDto,
  })
  source: SourceMetaDto;

  @ApiProperty()
  url: string;
}
