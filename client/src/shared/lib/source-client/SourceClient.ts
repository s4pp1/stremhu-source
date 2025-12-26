/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { BaseHttpRequest } from './core/BaseHttpRequest';
import type { OpenAPIConfig } from './core/OpenAPI';
import { FetchHttpRequest } from './core/FetchHttpRequest';
import { AppService } from './services/AppService';
import { AuthenticationService } from './services/AuthenticationService';
import { MeService } from './services/MeService';
import { MetadataService } from './services/MetadataService';
import { SettingsService } from './services/SettingsService';
import { StremHuCatalogService } from './services/StremHuCatalogService';
import { StremioManifestService } from './services/StremioManifestService';
import { StremioPlaybackService } from './services/StremioPlaybackService';
import { StremioStreamsService } from './services/StremioStreamsService';
import { TorrentsService } from './services/TorrentsService';
import { TorrentsCacheService } from './services/TorrentsCacheService';
import { TrackersService } from './services/TrackersService';
import { UsersService } from './services/UsersService';
type HttpRequestConstructor = new (config: OpenAPIConfig) => BaseHttpRequest;
export class SourceClient {
    public readonly app: AppService;
    public readonly authentication: AuthenticationService;
    public readonly me: MeService;
    public readonly metadata: MetadataService;
    public readonly settings: SettingsService;
    public readonly stremHuCatalog: StremHuCatalogService;
    public readonly stremioManifest: StremioManifestService;
    public readonly stremioPlayback: StremioPlaybackService;
    public readonly stremioStreams: StremioStreamsService;
    public readonly torrents: TorrentsService;
    public readonly torrentsCache: TorrentsCacheService;
    public readonly trackers: TrackersService;
    public readonly users: UsersService;
    public readonly request: BaseHttpRequest;
    constructor(config?: Partial<OpenAPIConfig>, HttpRequest: HttpRequestConstructor = FetchHttpRequest) {
        this.request = new HttpRequest({
            BASE: config?.BASE ?? '',
            VERSION: config?.VERSION ?? '1.0.0',
            WITH_CREDENTIALS: config?.WITH_CREDENTIALS ?? false,
            CREDENTIALS: config?.CREDENTIALS ?? 'include',
            TOKEN: config?.TOKEN,
            USERNAME: config?.USERNAME,
            PASSWORD: config?.PASSWORD,
            HEADERS: config?.HEADERS,
            ENCODE_PATH: config?.ENCODE_PATH,
        });
        this.app = new AppService(this.request);
        this.authentication = new AuthenticationService(this.request);
        this.me = new MeService(this.request);
        this.metadata = new MetadataService(this.request);
        this.settings = new SettingsService(this.request);
        this.stremHuCatalog = new StremHuCatalogService(this.request);
        this.stremioManifest = new StremioManifestService(this.request);
        this.stremioPlayback = new StremioPlaybackService(this.request);
        this.stremioStreams = new StremioStreamsService(this.request);
        this.torrents = new TorrentsService(this.request);
        this.torrentsCache = new TorrentsCacheService(this.request);
        this.trackers = new TrackersService(this.request);
        this.users = new UsersService(this.request);
    }
}

