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
import _ from 'lodash';

import { Roles } from 'src/auth/decorators/roles.decorator';
import { AuthGuard } from 'src/auth/guards/auth.guard';
import { RolesGuard } from 'src/auth/guards/roles.guard';
import { toDto } from 'src/common/utils/to-dto';
import { UserRoleEnum } from 'src/users/enum/user-role.enum';

import { TorrentDto } from './dto/torrent.dto';
import { UpdateTorrentDto } from './dto/update-torrent.dto';
import { TorrentsService } from './torrents.service';

@UseGuards(AuthGuard, RolesGuard)
@Roles(UserRoleEnum.ADMIN)
@Controller('/torrents')
@ApiTags('Torrents')
export class TorrentsController {
  constructor(private readonly torrentsService: TorrentsService) {}

  @Get('/')
  @ApiResponse({ status: 200, type: TorrentDto, isArray: true })
  async find(): Promise<TorrentDto[]> {
    const torrents = await this.torrentsService.getTorrents();

    const sortedTorrents = _.orderBy(
      torrents,
      [(torrent) => torrent.isPersisted, (torrent) => torrent.name],
      ['desc', 'asc'],
    );

    return sortedTorrents.map((torrent) => {
      return toDto(TorrentDto, torrent);
    });
  }

  @Put('/:infoHash')
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

  @Delete('/:infoHash')
  @ApiParam({ name: 'infoHash', type: 'string' })
  async delete(@Param('infoHash') infoHash: string) {
    await this.torrentsService.delete(infoHash);
  }
}
