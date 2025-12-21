import { Injectable } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import semver from 'semver';

import { NodeEnvEnum } from 'src/config/enum/node-env.enum';
import { SettingsStore } from 'src/settings/core/settings.store';

import {
  ContentTypeEnum,
  ManifestDto,
  ShortManifestResourceEnum,
} from './dto/manifest.dto';
import { ADDON_PREFIX_ID } from './stream/stremio.constants';

@Injectable()
export class StremioService {
  constructor(
    private configService: ConfigService,
    private settingsStore: SettingsStore,
  ) {}

  async manifest(): Promise<ManifestDto> {
    const nodeEnv = this.configService.getOrThrow<NodeEnvEnum>('app.node-env');
    const version = this.configService.getOrThrow<string>('app.version');
    const description =
      this.configService.getOrThrow<string>('app.description');

    const endpoint = await this.settingsStore.getEndpoint();

    let id = 'hu.stremhu-source.addon';
    let validVersion = semver.clean(version);
    let name = 'StremHU | Source';

    if (nodeEnv !== NodeEnvEnum.PRODUCTION) {
      id = `${id}.dev`;
      name = `${name} (DEV)`;
    }

    if (validVersion === null) {
      validVersion = '0.0.0';
    }

    const manifest: ManifestDto = {
      id,
      version: validVersion,
      name,
      description,
      resources: [ShortManifestResourceEnum.SRTEAM],
      types: [ContentTypeEnum.MOVIE, ContentTypeEnum.SERIES],
      idPrefixes: ['tt', ADDON_PREFIX_ID],
      catalogs: [],
      behaviorHints: {
        configurable: true,
        configurationRequired: false,
      },
      logo: `${endpoint}/logo.png`,
    };

    return manifest;
  }
}
