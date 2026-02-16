import { Controller, Get } from '@nestjs/common';
import { ApiResponse, ApiTags } from '@nestjs/swagger';

import { MetadataDto } from './dto/metadata.dto';
import { MetadataService } from './metadata.service';

@Controller('/metadata')
@ApiTags('Metadata')
export class MetadataController {
  constructor(private readonly metadataService: MetadataService) {}

  @Get('/')
  @ApiResponse({ status: 200, type: MetadataDto })
  async metadata(): Promise<MetadataDto> {
    return this.metadataService.get();
  }
}
