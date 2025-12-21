/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export { SourceClient } from './SourceClient';

export { ApiError } from './core/ApiError';
export { BaseHttpRequest } from './core/BaseHttpRequest';
export { CancelablePromise, CancelError } from './core/CancelablePromise';
export { OpenAPI } from './core/OpenAPI';
export type { OpenAPIConfig } from './core/OpenAPI';

export type { AuthLoginDto } from './models/AuthLoginDto';
export type { BehaviorHintsDto } from './models/BehaviorHintsDto';
export type { CatalogHealthDto } from './models/CatalogHealthDto';
export type { CreateSetupDto } from './models/CreateSetupDto';
export type { CreateUserDto } from './models/CreateUserDto';
export type { HealthDto } from './models/HealthDto';
export type { LanguageDto } from './models/LanguageDto';
export { LanguageEnum } from './models/LanguageEnum';
export type { LocalUrlDto } from './models/LocalUrlDto';
export type { LocalUrlRequestDto } from './models/LocalUrlRequestDto';
export type { LoginTrackerDto } from './models/LoginTrackerDto';
export type { ManifestDto } from './models/ManifestDto';
export type { MeDto } from './models/MeDto';
export type { MetadataDto } from './models/MetadataDto';
export type { ResolutionDto } from './models/ResolutionDto';
export { ResolutionEnum } from './models/ResolutionEnum';
export type { SettingDto } from './models/SettingDto';
export type { StatusDto } from './models/StatusDto';
export type { StreamDto } from './models/StreamDto';
export type { StreamsResponseDto } from './models/StreamsResponseDto';
export type { TorrentDto } from './models/TorrentDto';
export type { TrackerDto } from './models/TrackerDto';
export { TrackerEnum } from './models/TrackerEnum';
export type { TrackerMetaDto } from './models/TrackerMetaDto';
export type { UpdateMeDto } from './models/UpdateMeDto';
export type { UpdateSettingDto } from './models/UpdateSettingDto';
export type { UpdateTorrentDto } from './models/UpdateTorrentDto';
export type { UpdateTrackerDto } from './models/UpdateTrackerDto';
export type { UpdateUserDto } from './models/UpdateUserDto';
export type { UserDto } from './models/UserDto';
export type { UserRoleDto } from './models/UserRoleDto';
export { UserRoleEnum } from './models/UserRoleEnum';

export { AppService } from './services/AppService';
export { AuthenticationService } from './services/AuthenticationService';
export { MeService } from './services/MeService';
export { MetadataService } from './services/MetadataService';
export { SettingsService } from './services/SettingsService';
export { StremHuCatalogService } from './services/StremHuCatalogService';
export { StremioService } from './services/StremioService';
export { StremioStreamService } from './services/StremioStreamService';
export { TorrentsService } from './services/TorrentsService';
export { TorrentsCacheService } from './services/TorrentsCacheService';
export { TrackersService } from './services/TrackersService';
export { UsersService } from './services/UsersService';
