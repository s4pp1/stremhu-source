/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { BaseHttpRequest } from './core/BaseHttpRequest';
import type { OpenAPIConfig } from './core/OpenAPI';
import { AxiosHttpRequest } from './core/AxiosHttpRequest';
import { MonitoringService } from './services/MonitoringService';
import { SettingService } from './services/SettingService';
import { StreamService } from './services/StreamService';
import { TorrentsService } from './services/TorrentsService';
type HttpRequestConstructor = new (config: OpenAPIConfig) => BaseHttpRequest;
export class RelayClient {
    public readonly monitoring: MonitoringService;
    public readonly setting: SettingService;
    public readonly stream: StreamService;
    public readonly torrents: TorrentsService;
    public readonly request: BaseHttpRequest;
    constructor(config?: Partial<OpenAPIConfig>, HttpRequest: HttpRequestConstructor = AxiosHttpRequest) {
        this.request = new HttpRequest({
            BASE: config?.BASE ?? '',
            VERSION: config?.VERSION ?? '0.1.0',
            WITH_CREDENTIALS: config?.WITH_CREDENTIALS ?? false,
            CREDENTIALS: config?.CREDENTIALS ?? 'include',
            TOKEN: config?.TOKEN,
            USERNAME: config?.USERNAME,
            PASSWORD: config?.PASSWORD,
            HEADERS: config?.HEADERS,
            ENCODE_PATH: config?.ENCODE_PATH,
        });
        this.monitoring = new MonitoringService(this.request);
        this.setting = new SettingService(this.request);
        this.stream = new StreamService(this.request);
        this.torrents = new TorrentsService(this.request);
    }
}

