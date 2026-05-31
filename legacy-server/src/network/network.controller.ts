import { Body, Controller, Logger, Post, UseGuards } from '@nestjs/common';
import {
  ApiBody,
  ApiExtraModels,
  ApiTags,
  getSchemaPath,
} from '@nestjs/swagger';

import { Roles } from 'src/auth/decorators/roles.decorator';
import { AuthGuard } from 'src/auth/guards/auth.guard';
import { RolesGuard } from 'src/auth/guards/roles.guard';
import { UserRoleEnum } from 'src/users/enum/user-role.enum';

import {
  NetworkAutoSetupDto,
  NetworkManualSetupDto,
  NetworkSetupDto,
} from './dto/network-setup.dto';
import { NetworkService } from './network.service';

@UseGuards(AuthGuard, RolesGuard)
@Roles(UserRoleEnum.ADMIN)
@Controller('network')
@ApiTags('Network')
@ApiExtraModels(NetworkAutoSetupDto, NetworkManualSetupDto)
export class NetworkController {
  private readonly logger = new Logger(NetworkController.name);

  constructor(private readonly networkService: NetworkService) {}

  @Post('config')
  @ApiBody({
    schema: {
      oneOf: [
        { $ref: getSchemaPath(NetworkAutoSetupDto) },
        { $ref: getSchemaPath(NetworkManualSetupDto) },
      ],
      discriminator: {
        propertyName: 'mode',
        mapping: {
          auto: getSchemaPath(NetworkAutoSetupDto),
          manual: getSchemaPath(NetworkManualSetupDto),
        },
      },
    },
  })
  async config(@Body() dto: NetworkSetupDto) {
    await this.networkService.setup(dto);
    return { message: 'Network setup started' };
  }
}
