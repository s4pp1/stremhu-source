import { Controller, Get } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { ApiResponse, ApiTags } from '@nestjs/swagger';

import { HealthDto } from './common/dto/health.dto';

@Controller('/')
@ApiTags('App')
export class AppController {
  constructor(private readonly configService: ConfigService) {}

  @Get('/health')
  @ApiResponse({ status: 200, type: HealthDto })
  health(): HealthDto {
    const version = this.configService.getOrThrow<string>('app.version');

    return {
      version,
    };
  }
}
