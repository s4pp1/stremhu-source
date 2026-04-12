import { Controller, Get, SerializeOptions } from '@nestjs/common';
import { ApiTags } from '@nestjs/swagger';

import { MetadataDto } from './dto/metadata.dto';
import { MetadataService } from './metadata.service';

@Controller('/metadata')
@ApiTags('Metadata')
export class MetadataController {
  constructor(private readonly metadataService: MetadataService) {}

  @SerializeOptions({ type: MetadataDto })
  @Get('/')
  async metadata(): Promise<MetadataDto> {
    const metadata = await this.metadataService.get();
    return metadata;
  }
}
