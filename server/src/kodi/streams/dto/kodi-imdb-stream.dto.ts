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
  torrentName: string;

  /** Fájlnév a torrenten belül */
  fileName: string;

  /** Seederek száma */
  seeders: number;

  /** Emberi formátumú méret (pl. 2.5 GB) */
  size: string;

  /** Tracker adatai */
  tracker: TrackerMetaDto;

  /** Nyelvek listája */
  @IsArray()
  languages: LanguageMetaDto[];

  /** Felbontás adatai */
  resolution: ResolutionMetaDto;

  /** Videó minőségi jellemzők */
  @IsArray()
  videoQualities: VideoQualityMetaDto[];

  /** Audió minőség */
  audioQuality?: AudioQualityMetaDto;

  /** Térhatású hang jellemzők */
  audioSpatial?: AudioSpatialMetaDto;

  /** Forrás adatai */
  source: SourceMetaDto;

  /** Stream URL */
  url: string;
}
