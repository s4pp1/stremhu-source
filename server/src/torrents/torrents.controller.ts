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
import { UserRoleEnum } from 'src/users/enum/user-role.enum';

import { TorrentDto } from './dto/torrent.dto';
import { UpdateTorrentDto } from './dto/update-torrent.dto';
import { TorrentsService } from './torrents.service';

@UseGuards(AuthGuard, RolesGuard)
@Roles(UserRoleEnum.ADMIN)
@Controller('/torrents')
@ApiTags('Torrentek')
export class TorrentsController {
  constructor(private readonly torrentsService: TorrentsService) {}

  @SerializeOptions({ type: TorrentDto })
  @Get('/')
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
  @Put('/:infoHash')
  @ApiParam({ name: 'infoHash', type: 'string' })
  async update(
    @Param('infoHash') infoHash: string,
    @Body() payload: UpdateTorrentDto,
  ): Promise<TorrentDto> {
    const torrent = await this.torrentsService.updateOne(infoHash, payload);

    return torrent;
  }

  @Delete('/:infoHash')
  @ApiParam({ name: 'infoHash', type: 'string' })
  async delete(@Param('infoHash') infoHash: string): Promise<void> {
    await this.torrentsService.delete(infoHash);
  }
}
