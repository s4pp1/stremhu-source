import { Body, Controller, Put, UseGuards } from '@nestjs/common';
import { ApiParam, ApiTags } from '@nestjs/swagger';

import { Roles } from 'src/auth/decorators/roles.decorator';
import { RolesGuard } from 'src/auth/guards/roles.guard';
import { TokenGuard } from 'src/auth/guards/token.guard';
import { SettingsCoreService } from 'src/settings/core/settings-core.service';
import { UpdateExternalSettingDto } from 'src/settings/dto/update-external-setting.dto';
import { TorrentsService } from 'src/torrents/torrents.service';
import { UserRoleEnum } from 'src/users/enum/user-role.enum';

@UseGuards(TokenGuard, RolesGuard)
@Roles(UserRoleEnum.ADMIN)
@Controller(':token/external/relay/settings')
@ApiParam({
  name: 'token',
  required: true,
  type: 'string',
})
@ApiTags('Integrations / Torrents')
export class ExternalRelaySettingsController {
  constructor(
    private readonly settingsCoreService: SettingsCoreService,
    private readonly torrentsService: TorrentsService,
  ) {}

  @Put('/')
  async update(@Body() body: UpdateExternalSettingDto): Promise<void> {
    const settings = await this.settingsCoreService.updateRelaySettings(body);
    await this.torrentsService.updateTorrentClient(settings);
  }
}
