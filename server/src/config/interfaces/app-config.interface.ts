import { NodeEnvEnum } from '../enum/node-env.enum';

export interface AppConfig {
  'node-env': NodeEnvEnum;
  'client-path': string;
  'http-port': number;
  'https-port': number;
  'openapi-dir': string;
  version: string;
  description: string;
  'stremhu-catalog-url': string;
}
