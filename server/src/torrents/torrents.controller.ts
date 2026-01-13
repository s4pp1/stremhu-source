import {
  Body,
  Controller,
  Delete,
  Get,
  Param,
  Put,
  UseGuards,
} from '@nestjs/common';
import { ApiParam, ApiResponse, ApiTags } from '@nestjs/swagger';
import { orderBy } from 'lodash';

import { Roles } from 'src/auth/decorators/roles.decorator';
import { AuthGuard } from 'src/auth/guards/auth.guard';
import { RolesGuard } from 'src/auth/guards/roles.guard';
import { toDto } from 'src/common/utils/to-dto';
import { RelaySettingsService } from 'src/settings/relay/relay-settings.service';
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
    private readonly relaySettingsService: RelaySettingsService,
  ) {}

  @Get('/settings')
  @ApiResponse({ status: 200, type: RelaySettingsDto })
  async settings() {
    const settings = await this.relaySettingsService.get();
    return toDto(RelaySettingsDto, settings);
  }

  @Put('/settings')
  @ApiResponse({ status: 200, type: TorrentDto, isArray: true })
  async updateSettings(@Body() payload: UpdateRelaySettingsDto) {
    const settings = await this.relaySettingsService.update(payload);
    await this.torrentsService.updateTorrentClient(settings);

    return toDto(RelaySettingsDto, settings);
  }

  @Get('/torrents')
  @ApiResponse({ status: 200, type: TorrentDto, isArray: true })
  async find(): Promise<TorrentDto[]> {
    const torrents = await this.torrentsService.getTorrents();

    const sortedTorrents = orderBy(
      torrents,
      [(torrent) => torrent.isPersisted, (torrent) => torrent.name],
      ['desc', 'asc'],
    );

    return sortedTorrents.map((torrent) => {
      return toDto(TorrentDto, torrent);
    });
  }

  @Put('/torrents/:infoHash')
  @ApiParam({ name: 'infoHash', type: 'string' })
  @ApiResponse({ status: 200, type: TorrentDto })
  async update(
    @Param('infoHash') infoHash: string,
    @Body() payload: UpdateTorrentDto,
  ): Promise<TorrentDto> {
    const mergedTorrent = await this.torrentsService.updateOneForRest(
      infoHash,
      payload,
    );

    return toDto(TorrentDto, mergedTorrent);
  }

  @Delete('/torrents/:infoHash')
  @ApiParam({ name: 'infoHash', type: 'string' })
  async delete(@Param('infoHash') infoHash: string) {
    await this.torrentsService.delete(infoHash);
  }
}
