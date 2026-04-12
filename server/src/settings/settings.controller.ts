import {
  Body,
  Controller,
  Get,
  Post,
  Put,
  SerializeOptions,
  UseGuards,
} from '@nestjs/common';
import { ApiTags } from '@nestjs/swagger';

import { Roles } from 'src/auth/decorators/roles.decorator';
import { AuthGuard } from 'src/auth/guards/auth.guard';
import { RolesGuard } from 'src/auth/guards/roles.guard';
import { UserRoleEnum } from 'src/users/enum/user-role.enum';

import { AppSettingsService } from './app/app-settings.service';
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
    private readonly settingsService: SettingsService,
    private readonly appSettingsService: AppSettingsService,
  ) {}

  @SerializeOptions({ type: SettingDto })
  @Get('/')
  async findOne(): Promise<SettingDto> {
    const setting = await this.appSettingsService.get();
    return setting;
  }

  @SerializeOptions({ type: SettingDto })
  @Put('/')
  async update(@Body() body: UpdateSettingDto): Promise<SettingDto> {
    const setting = await this.settingsService.update(body);
    return setting;
  }

  @SerializeOptions({ type: LocalUrlDto })
  @Post('/local-url')
  buildLocalUrl(@Body() body: LocalUrlRequestDto): LocalUrlDto {
    const localUrl = this.settingsService.buildLocalUrl(body.ipv4);

    return {
      localUrl,
    };
  }
}
