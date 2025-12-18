import {
  Body,
  Controller,
  Delete,
  Get,
  Param,
  ParseEnumPipe,
  Post,
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
import { TrackerCredentialDto } from './credentials/dto/tracker-credential.dto';
import { LoginTrackerDto } from './dto/login-tracker.dto';
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
  async loginTracker(@Body() body: LoginTrackerDto) {
    const { tracker, ...rest } = body;
    await this.trackersService.login(tracker, rest);
  }

  @ApiResponse({ status: 200, type: TrackerCredentialDto, isArray: true })
  @Get('/')
  async trackers(): Promise<TrackerCredentialDto[]> {
    const trackerCredentials = await this.trackersStore.find();
    return trackerCredentials.map((trackerCredential) =>
      toDto(TrackerCredentialDto, trackerCredential),
    );
  }

  @ApiResponse({ status: 200 })
  @Post('/hit-and-run')
  async cleanupHitAndRun() {
    return this.trackerMaintenanceService.cleanupHitAndRun();
  }

  @ApiParam({
    name: 'tracker',
    enum: TrackerEnum,
  })
  @ApiResponse({ status: 200 })
  @Delete('/:tracker')
  async deleteTracker(
    @Param('tracker', new ParseEnumPipe(TrackerEnum)) tracker: TrackerEnum,
  ) {
    await this.trackersService.delete(tracker);
  }
}
