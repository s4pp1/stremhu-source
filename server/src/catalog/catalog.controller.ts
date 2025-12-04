import { Controller, Get } from '@nestjs/common';
import { ApiResponse, ApiTags } from '@nestjs/swagger';

import { CatalogService } from './catalog.service';
import { CatalogHealthDto } from './dto/catalog-health.dto';

@Controller('/catalog')
@ApiTags('StremHU | Catalog')
export class CatalogController {
  constructor(private readonly catalogService: CatalogService) {}

  @Get('/health')
  @ApiResponse({ status: 200, type: CatalogHealthDto })
  health(): Promise<CatalogHealthDto> {
    const health = this.catalogService.catalogHealthCheck();

    return health;
  }
}
