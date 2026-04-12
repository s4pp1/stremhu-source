import {
  Body,
  Controller,
  Delete,
  Get,
  Param,
  ParseEnumPipe,
  Post,
  Put,
  SerializeOptions,
  UseGuards,
} from '@nestjs/common';
import { ApiParam, ApiTags } from '@nestjs/swagger';

import { Roles } from 'src/auth/decorators/roles.decorator';
import { AuthGuard } from 'src/auth/guards/auth.guard';
import { RolesGuard } from 'src/auth/guards/roles.guard';
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

  @Post('/')
  async login(@Body() body: LoginTrackerDto): Promise<void> {
    const { tracker, ...rest } = body;
    await this.trackersService.login(tracker, rest);
  }

  @SerializeOptions({ type: TrackerDto })
  @Get('/')
  async trackers(): Promise<TrackerDto[]> {
    const trackerCredentials = await this.trackersStore.find();
    return trackerCredentials;
  }

  @Post('/cleanup')
  async cleanup(): Promise<void> {
    return this.trackerMaintenanceService.runTrackersCleanup();
  }

  @SerializeOptions({ type: TrackerDto })
  @ApiParam({
    name: 'tracker',
    enum: TrackerEnum,
  })
  @Put('/:tracker')
  async update(
    @Param('tracker', new ParseEnumPipe(TrackerEnum)) tracker: TrackerEnum,
    @Body() payload: UpdateTrackerDto,
  ): Promise<TrackerDto> {
    const updatedItem = await this.trackersService.updateOneOrThrow(
      tracker,
      payload,
    );

    return updatedItem;
  }

  @ApiParam({
    name: 'tracker',
    enum: TrackerEnum,
  })
  @Delete('/:tracker')
  async delete(
    @Param('tracker', new ParseEnumPipe(TrackerEnum)) tracker: TrackerEnum,
  ): Promise<void> {
    await this.trackersService.delete(tracker);
  }
}
