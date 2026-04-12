import { Expose } from 'class-transformer';
import { IsArray } from 'class-validator';

import { AudioQualityMetaDto } from 'src/metadata/dto/audio-quality-meta.dto';
import { AudioSpatialMetaDto } from 'src/metadata/dto/audio-spatial-meta.dto';
import { LanguageMetaDto } from 'src/metadata/dto/language-meta.dto';
import { ResolutionMetaDto } from 'src/metadata/dto/resolution-meta.dto';
import { SourceMetaDto } from 'src/metadata/dto/source-meta.dto';
import { TrackerMetaDto } from 'src/metadata/dto/tracker-meta.dto';
import { VideoQualityMetaDto } from 'src/metadata/dto/video-quality-meta.dto';

export class KodiImdbStreamDto {
  /** Torrent fájl neve */
  @Expose()
  torrentName: string;

  /** Fájlnév a torrenten belül */
  @Expose()
  fileName: string;

  /** Seederek száma */
  @Expose()
  seeders: number;

  /** Emberi formátumú méret (pl. 2.5 GB) */
  @Expose()
  size: string;

  /** Tracker adatai */
  @Expose()
  tracker: TrackerMetaDto;

  /** Nyelvek listája */
  @Expose()
  @IsArray()
  languages: LanguageMetaDto[];

  /** Felbontás adatai */
  @Expose()
  resolution: ResolutionMetaDto;

  /** Videó minőségi jellemzők */
  @Expose()
  @IsArray()
  videoQualities: VideoQualityMetaDto[];

  /** Audió minőség */
  @Expose()
  audioQuality?: AudioQualityMetaDto;

  /** Térhatású hang jellemzők */
  @Expose()
  audioSpatial?: AudioSpatialMetaDto;

  /** Forrás adatai */
  @Expose()
  source: SourceMetaDto;

  /** Stream URL */
  @Expose()
  url: string;
}
