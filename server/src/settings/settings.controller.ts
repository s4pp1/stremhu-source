import { Body, Controller, Get, Post, Put, UseGuards } from '@nestjs/common';
import { ApiResponse, ApiTags } from '@nestjs/swagger';

import { Roles } from 'src/auth/decorators/roles.decorator';
import { AuthGuard } from 'src/auth/guards/auth.guard';
import { RolesGuard } from 'src/auth/guards/roles.guard';
import { toDto } from 'src/common/utils/to-dto';
import { UserRoleEnum } from 'src/users/enum/user-role.enum';

import { SettingsStore } from './core/settings.store';
import { LocalUrlRequestDto } from './dto/local-url-request.dto';
import { LocalUrlDto } from './dto/local-url.dto';
import { SettingDto } from './dto/setting.dto';
import { UpdateSettingDto } from './dto/update-setting.dto';
import { SettingsService } from './settings.service';

@UseGuards(AuthGuard, RolesGuard)
@Roles(UserRoleEnum.ADMIN)
@Controller('/settings')
@ApiTags('Settings')
export class SettingsController {
  constructor(
    private readonly settingsStore: SettingsStore,
    private readonly settingsService: SettingsService,
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
    const setting = await this.settingsService.update(body);
    return {
      ...setting,
      address: setting.address || '',
    };
  }

  @ApiResponse({ status: 200, type: LocalUrlDto })
  @Post('/local-url')
  buildLocalUrl(@Body() body: LocalUrlRequestDto): LocalUrlDto {
    const localUrl = this.settingsStore.buildLocalUrl(body.ipv4);

    return {
      localUrl,
    };
  }
}
