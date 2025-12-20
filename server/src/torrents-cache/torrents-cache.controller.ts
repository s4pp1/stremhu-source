import { Controller, Post, UseGuards } from '@nestjs/common';
import { ApiResponse, ApiTags } from '@nestjs/swagger';

import { Roles } from 'src/auth/decorators/roles.decorator';
import { AuthGuard } from 'src/auth/guards/auth.guard';
import { RolesGuard } from 'src/auth/guards/roles.guard';
import { UserRoleEnum } from 'src/users/enum/user-role.enum';

import { TorrentsCacheService } from './torrents-cache.service';

@UseGuards(AuthGuard, RolesGuard)
@Roles(UserRoleEnum.ADMIN)
@Controller('/torrents/cache')
@ApiTags('Torrents Cache')
export class TorrentsCacheController {
  constructor(private readonly torrentsCacheService: TorrentsCacheService) {}

  @ApiResponse({ status: 200 })
  @Post('/cleanup')
  async cleanup(): Promise<void> {
    return this.torrentsCacheService.runRetentionCleanup(0);
  }
}
