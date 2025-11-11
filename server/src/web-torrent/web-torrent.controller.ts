import { Controller, Delete, Get, Param, UseGuards } from '@nestjs/common';
import { ApiParam, ApiResponse } from '@nestjs/swagger';
import { filesize } from 'filesize';
import _ from 'lodash';

import { AuthGuard } from 'src/auth/guards/auth.guard';
import { toDto } from 'src/common/utils/to-dto';

import { TorrentDto } from './dto/torrent.dto';
import { WebTorrentService } from './web-torrent.service';

@UseGuards(AuthGuard)
@Controller('/torrents')
export class WebTorrentController {
  constructor(private readonly webTorrentService: WebTorrentService) {}

  @Get('/')
  @ApiResponse({ status: 200, type: TorrentDto, isArray: true })
  async find(): Promise<TorrentDto[]> {
    const torrents = await this.webTorrentService.getTorrents();

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
    await this.webTorrentService.delete(infoHash);
  }
}
