import {
  Body,
  Controller,
  Get,
  Put,
  SerializeOptions,
  UseGuards,
} from '@nestjs/common';
import { ApiParam, ApiTags } from '@nestjs/swagger';

import { Roles } from 'src/auth/decorators/roles.decorator';
import { RolesGuard } from 'src/auth/guards/roles.guard';
import { TokenGuard } from 'src/auth/guards/token.guard';
import { RelayCoreService } from 'src/relay/core/relay-core.service';
import { SettingsCoreService } from 'src/settings/core/settings-core.service';
import { UserRoleEnum } from 'src/users/enum/user-role.enum';

import { RelaySettingsDto } from '../dto/relay-settings.dto';
import { UpdateRelaySettingsDto } from '../dto/update-relay-settings.dto';

@UseGuards(TokenGuard, RolesGuard)
@Roles(UserRoleEnum.ADMIN)
@Controller(':token/relay/settings')
@ApiParam({
  name: 'token',
  required: true,
  type: 'string',
})
@ApiTags('Relay Beállítások')
export class RelaySettingsIntegrationController {
  constructor(
    private readonly settingsCoreService: SettingsCoreService,
    private readonly relayCoreService: RelayCoreService,
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
