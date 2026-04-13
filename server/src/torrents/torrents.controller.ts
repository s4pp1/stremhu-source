import {
  Body,
  Controller,
  Delete,
  Get,
  Param,
  Put,
  SerializeOptions,
  UseGuards,
} from '@nestjs/common';
import { ApiParam, ApiTags } from '@nestjs/swagger';
import { orderBy } from 'lodash';

import { Roles } from 'src/auth/decorators/roles.decorator';
import { AuthGuard } from 'src/auth/guards/auth.guard';
import { RolesGuard } from 'src/auth/guards/roles.guard';
import { SettingsCoreService } from 'src/settings/core/settings-core.service';
import { UserRoleEnum } from 'src/users/enum/user-role.enum';

import { RelaySettingsDto } from './dto/relay-settings.dto';
import { TorrentDto } from './dto/torrent.dto';
import { UpdateRelaySettingsDto } from './dto/update-relay-settings.dto';
import { UpdateTorrentDto } from './dto/update-torrent.dto';
import { TorrentsService } from './torrents.service';

@UseGuards(AuthGuard, RolesGuard)
@Roles(UserRoleEnum.ADMIN)
@Controller('/relay')
@ApiTags('Torrents')
export class TorrentsController {
  constructor(
    private readonly torrentsService: TorrentsService,
    private readonly settingsCoreService: SettingsCoreService,
  ) {}

  @SerializeOptions({ type: RelaySettingsDto })
  @Get('/settings')
  async settings(): Promise<RelaySettingsDto> {
    const settings = await this.settingsCoreService.relaySettings();
    return settings;
  }

  @SerializeOptions({ type: RelaySettingsDto })
  @Put('/settings')
  async updateSettings(
    @Body() payload: UpdateRelaySettingsDto,
  ): Promise<RelaySettingsDto> {
    const settings =
      await this.settingsCoreService.updateRelaySettings(payload);
    await this.torrentsService.updateTorrentClient(settings);

    return settings;
  }

  @SerializeOptions({ type: TorrentDto })
  @Get('/torrents')
  async find(): Promise<TorrentDto[]> {
    const torrents = await this.torrentsService.find();

    const sortedTorrents = orderBy(
      torrents,
      [(torrent) => torrent.isPersisted, (torrent) => torrent.name],
      ['desc', 'asc'],
    );

    return sortedTorrents;
  }

  @SerializeOptions({ type: TorrentDto })
  @Put('/torrents/:infoHash')
  @ApiParam({ name: 'infoHash', type: 'string' })
  async update(
    @Param('infoHash') infoHash: string,
    @Body() payload: UpdateTorrentDto,
  ): Promise<TorrentDto> {
    const torrent = await this.torrentsService.updateOne(infoHash, payload);

    return torrent;
  }

  @Delete('/torrents/:infoHash')
  @ApiParam({ name: 'infoHash', type: 'string' })
  async delete(@Param('infoHash') infoHash: string): Promise<void> {
    await this.torrentsService.delete(infoHash);
  }
}
