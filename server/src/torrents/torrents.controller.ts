import { Controller, Delete, Get, Param, UseGuards } from '@nestjs/common';
import { ApiParam, ApiResponse, ApiTags } from '@nestjs/swagger';
import { filesize } from 'filesize';
import _ from 'lodash';

import { Roles } from 'src/auth/decorators/roles.decorator';
import { AuthGuard } from 'src/auth/guards/auth.guard';
import { RolesGuard } from 'src/auth/guards/roles.guard';
import { toDto } from 'src/common/utils/to-dto';
import { UserRoleEnum } from 'src/users/enum/user-role.enum';

import { TorrentDto } from './dto/torrent.dto';
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
      [(torrent) => torrent.name],
      ['asc'],
    );

    return sortedTorrents.map((torrent) => {
      let uploadSpeed = '-';

      if (torrent.uploadSpeed !== 0) {
        uploadSpeed = `${filesize(torrent.uploadSpeed)}/s`;
      }

      const response = {
        tracker: torrent.tracker,
        name: torrent.name,
        uploadSpeed: uploadSpeed,
        progress: `${_.floor(torrent.progress * 100, 2)}%`,
        downloaded: filesize(torrent.downloaded),
        uploaded: filesize(torrent.uploaded),
        total: filesize(torrent.total),
        infoHash: torrent.infoHash,
      };

      return toDto(TorrentDto, response);
    });
  }

  @ApiParam({ name: 'infoHash', type: 'string' })
  @Delete('/:infoHash')
  async delete(@Param('infoHash') infoHash: string) {
    await this.torrentsService.delete(infoHash);
  }
}
