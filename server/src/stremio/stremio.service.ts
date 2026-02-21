import { Injectable } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import semver from 'semver';

import { NodeEnvEnum } from 'src/config/enum/node-env.enum';
import { SettingsService } from 'src/settings/settings.service';

import { ManifestCatalog } from './dto/manifest-catalog.dto';
import { ManifestDto } from './dto/manifest.dto';
import { ContentTypeEnum } from './enum/content-type.enum';
import { ExtraEnum } from './enum/extra.enum';
import { ShortManifestResourceEnum } from './enum/short-manifest-resource.enum';
import {
  ADDON_APP_PREFIX_ID,
  ADDON_STREMHU_PREFIX_ID,
  SEARCH_ID,
} from './stremio.constants';

@Injectable()
export class ManifestService {
  constructor(
    private configService: ConfigService,
    private settingsService: SettingsService,
  ) {}

  async manifest(): Promise<ManifestDto> {
    const nodeEnv = this.configService.getOrThrow<NodeEnvEnum>('app.node-env');
    const version = this.configService.getOrThrow<string>('app.version');
    const description =
      this.configService.getOrThrow<string>('app.description');

    const endpoint = await this.settingsService.getEndpoint();

    let id = 'hu.stremhu-source.addon';
    let validVersion = semver.clean(version);
    let name = 'StremHU Source';

    if (nodeEnv !== NodeEnvEnum.PRODUCTION) {
      id = `${id}.dev`;
      name = `${name} (DEV)`;
    }

    if (validVersion === null) {
      validVersion = '0.0.0';
    }

    const catalogs: ManifestCatalog[] = [
      {
        id: SEARCH_ID,
        name: '🔍 Torrent - StremHU',
        type: ContentTypeEnum.MOVIE,
        extra: [{ name: ExtraEnum.SEARCH, isRequired: true }],
      },
    ];

    const manifest: ManifestDto = {
      id,
      version: validVersion,
      name,
      description,
      resources: [
        ShortManifestResourceEnum.SRTEAM,
        ShortManifestResourceEnum.CATALOG,
        ShortManifestResourceEnum.META,
      ],
      types: [ContentTypeEnum.MOVIE, ContentTypeEnum.SERIES],
      idPrefixes: ['tt', ADDON_APP_PREFIX_ID, ADDON_STREMHU_PREFIX_ID],
      catalogs,
      behaviorHints: {
        configurable: true,
        configurationRequired: false,
      },
      logo: `${endpoint}/logo.png`,
    };

    return manifest;
  }
}
