import { Controller, Get, SerializeOptions } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { ApiTags } from '@nestjs/swagger';

import { HealthDto } from './dto/health.dto';

@Controller('/')
@ApiTags('Monitoring')
export class MonitoringController {
  constructor(private readonly configService: ConfigService) {}

  @SerializeOptions({ type: HealthDto })
  @Get('/health')
  health(): HealthDto {
    const version = this.configService.getOrThrow<string>('app.version');

    return {
      version,
    };
  }
}
