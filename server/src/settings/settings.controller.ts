import { Body, Controller, Get, Post, Put, UseGuards } from '@nestjs/common';
import { ApiResponse, ApiTags } from '@nestjs/swagger';

import { Roles } from 'src/auth/decorators/roles.decorator';
import { AuthGuard } from 'src/auth/guards/auth.guard';
import { RolesGuard } from 'src/auth/guards/roles.guard';
import { toDto } from 'src/common/utils/to-dto';
import { TorrentCacheService } from 'src/torrent-cache/torrent-cache.service';
import { UserRoleEnum } from 'src/users/enums/user-role.enum';

import { SettingsStore } from './core/settings.store';
import { SettingDto } from './dto/setting.dto';
import { UpdateSettingDto } from './dto/update-setting.dto';
import { SettingsService } from './settings.service';

@UseGuards(AuthGuard, RolesGuard)
@Roles(UserRoleEnum.ADMIN)
@Controller('/settings')
@ApiTags('Settings')
export class SettingsController {
  constructor(
    private settingsStore: SettingsStore,
    private settingsService: SettingsService,
    private torrentsCache: TorrentCacheService,
  ) {}

  @ApiResponse({ status: 200, type: SettingDto })
  @Get('/')
  async findOne(): Promise<SettingDto> {
    const setting = await this.settingsStore.findOneOrThrow();
    return toDto(SettingDto, setting);
  }

  @ApiResponse({ status: 200, type: SettingDto })
  @Put('/')
  async update(@Body() body: UpdateSettingDto): Promise<SettingDto> {
    return this.settingsService.update(body);
  }

  @ApiResponse({ status: 200 })
  @Post('/cache/torrents/retention-cleanup')
  async cacheTorrentsCleanup(): Promise<void> {
    return this.torrentsCache.runRetentionCleanup();
  }
}
