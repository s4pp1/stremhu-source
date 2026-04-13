import {
  Body,
  Controller,
  Get,
  Put,
  SerializeOptions,
  UseGuards,
} from '@nestjs/common';
import { ApiTags } from '@nestjs/swagger';

import { Roles } from 'src/auth/decorators/roles.decorator';
import { AuthGuard } from 'src/auth/guards/auth.guard';
import { RolesGuard } from 'src/auth/guards/roles.guard';
import { SettingsCoreService } from 'src/settings/core/settings-core.service';
import { UserRoleEnum } from 'src/users/enum/user-role.enum';

import { RelayCoreService } from '../../core/relay-core.service';
import { RelaySettingsDto } from '../dto/relay-settings.dto';
import { UpdateRelaySettingsDto } from '../dto/update-relay-settings.dto';

@UseGuards(AuthGuard, RolesGuard)
@Roles(UserRoleEnum.ADMIN)
@Controller('/relay/settings')
@ApiTags('Relay Beállítások')
export class RelaySettingsInternalController {
  constructor(
    private readonly relayCoreService: RelayCoreService,
    private readonly settingsCoreService: SettingsCoreService,
  ) {}

  @SerializeOptions({ type: RelaySettingsDto })
  @Get('/')
  async get(): Promise<RelaySettingsDto> {
    const settings = await this.settingsCoreService.relaySettings();
    return settings;
  }

  @SerializeOptions({ type: RelaySettingsDto })
  @Put('/')
  async update(
    @Body() payload: UpdateRelaySettingsDto,
  ): Promise<RelaySettingsDto> {
    const settings =
      await this.settingsCoreService.updateRelaySettings(payload);
    await this.relayCoreService.updateConfig(settings);

    return settings;
  }
}
