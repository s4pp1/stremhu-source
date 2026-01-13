import { Body, Controller, Put, UseGuards } from '@nestjs/common';
import { ApiParam, ApiResponse, ApiTags } from '@nestjs/swagger';

import { Roles } from 'src/auth/decorators/roles.decorator';
import { RolesGuard } from 'src/auth/guards/roles.guard';
import { TokenGuard } from 'src/auth/guards/token.guard';
import { UserRoleEnum } from 'src/users/enum/user-role.enum';

import { SettingDto } from './dto/setting.dto';
import { UpdateExternalSettingDto } from './dto/update-external-setting.dto';
import { RelaySettingsService } from './relay/relay-settings.service';

@UseGuards(TokenGuard, RolesGuard)
@Roles(UserRoleEnum.ADMIN)
@Controller(':token/external/relay/settings')
@ApiParam({
  name: 'token',
  required: true,
  type: 'string',
})
@ApiTags('External Relay Settings')
export class ExternalRelaySettingsController {
  constructor(private readonly relaySettingsService: RelaySettingsService) {}

  @ApiResponse({ status: 200, type: SettingDto })
  @Put('/')
  async update(@Body() body: UpdateExternalSettingDto): Promise<void> {
    await this.relaySettingsService.update(body);
  }
}
