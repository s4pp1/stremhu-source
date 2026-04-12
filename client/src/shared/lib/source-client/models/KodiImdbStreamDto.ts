/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { AudioQualityMetaDto } from './AudioQualityMetaDto';
import type { AudioSpatialMetaDto } from './AudioSpatialMetaDto';
import type { LanguageMetaDto } from './LanguageMetaDto';
import type { ResolutionMetaDto } from './ResolutionMetaDto';
import type { SourceMetaDto } from './SourceMetaDto';
import type { TrackerMetaDto } from './TrackerMetaDto';
import type { VideoQualityMetaDto } from './VideoQualityMetaDto';
export type KodiImdbStreamDto = {
    /**
     * Torrent fájl neve
     */
    torrentName: string;
    /**
     * Fájlnév a torrenten belül
     */
    fileName: string;
    /**
     * Seederek száma
     */
    seeders: number;
    /**
     * Emberi formátumú méret (pl. 2.5 GB)
     */
    size: string;
    /**
     * Tracker adatai
     */
    tracker: TrackerMetaDto;
    /**
     * Nyelvek listája
     */
    languages: Array<LanguageMetaDto>;
    /**
     * Felbontás adatai
     */
    resolution: ResolutionMetaDto;
    /**
     * Videó minőségi jellemzők
     */
    videoQualities: Array<VideoQualityMetaDto>;
    /**
     * Audió minőség
     */
    audioQuality?: AudioQualityMetaDto;
    /**
     * Térhatású hang jellemzők
     */
    audioSpatial?: AudioSpatialMetaDto;
    /**
     * Forrás adatai
     */
    source: SourceMetaDto;
    /**
     * Stream URL
     */
    url: string;
};

