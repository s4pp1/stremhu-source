import {
  Body,
  Controller,
  Delete,
  Get,
  Param,
  ParseEnumPipe,
  Post,
  Put,
  UseGuards,
} from '@nestjs/common';
import { ApiParam, ApiResponse, ApiTags } from '@nestjs/swagger';

import { Roles } from 'src/auth/decorators/roles.decorator';
import { AuthGuard } from 'src/auth/guards/auth.guard';
import { RolesGuard } from 'src/auth/guards/roles.guard';
import { toDto } from 'src/common/utils/to-dto';
import { TrackerEnum } from 'src/trackers/enum/tracker.enum';
import { TrackersService } from 'src/trackers/trackers.service';
import { UserRoleEnum } from 'src/users/enum/user-role.enum';

import { TrackersStore } from './core/trackers.store';
import { LoginTrackerDto } from './dto/login-tracker.dto';
import { TrackerDto } from './dto/tracker.dto';
import { UpdateTrackerDto } from './dto/update-tracker.dto';
import { TrackerMaintenanceService } from './tracker-maintenance.service';

@UseGuards(AuthGuard, RolesGuard)
@Roles(UserRoleEnum.ADMIN)
@Controller('/trackers/')
@ApiTags('Trackers')
export class TrackersController {
  constructor(
    private readonly trackersStore: TrackersStore,
    private readonly trackersService: TrackersService,
    private readonly trackerMaintenanceService: TrackerMaintenanceService,
  ) {}

  @ApiResponse({ status: 201 })
  @Post('/')
  async login(@Body() body: LoginTrackerDto) {
    const { tracker, ...rest } = body;
    await this.trackersService.login(tracker, rest);
  }

  @ApiResponse({ status: 200, type: TrackerDto, isArray: true })
  @Get('/')
  async trackers(): Promise<TrackerDto[]> {
    const trackerCredentials = await this.trackersStore.find();
    return trackerCredentials.map((trackerCredential) =>
      toDto(TrackerDto, trackerCredential),
    );
  }

  @ApiResponse({ status: 200 })
  @Post('/cleanup')
  async cleanup() {
    return this.trackerMaintenanceService.runTrackersCleanup();
  }

  @ApiParam({
    name: 'tracker',
    enum: TrackerEnum,
  })
  @ApiResponse({ status: 200 })
  @Put('/:tracker')
  async update(
    @Param('tracker', new ParseEnumPipe(TrackerEnum)) tracker: TrackerEnum,
    @Body() payload: UpdateTrackerDto,
  ): Promise<TrackerDto> {
    const updatedItem = await this.trackersService.updateOneOrThrow(
      tracker,
      payload,
    );

    return toDto(TrackerDto, updatedItem);
  }

  @ApiParam({
    name: 'tracker',
    enum: TrackerEnum,
  })
  @ApiResponse({ status: 200 })
  @Delete('/:tracker')
  async delete(
    @Param('tracker', new ParseEnumPipe(TrackerEnum)) tracker: TrackerEnum,
  ) {
    await this.trackersService.delete(tracker);
  }
}
