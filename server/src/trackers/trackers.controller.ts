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
import { TrackerCredentialsService } from 'src/trackers/credentials/tracker-credentials.service';
import { TrackerEnum } from 'src/trackers/enums/tracker.enum';
import { TrackersService } from 'src/trackers/trackers.service';
import { UserRoleEnum } from 'src/users/enums/user-role.enum';

import { TrackerCredentialDto } from './credentials/dto/tracker-credential.dto';
import { LoginTrackerDto } from './dto/login-tracker.dto';

@UseGuards(AuthGuard, RolesGuard)
@Roles(UserRoleEnum.ADMIN)
@Controller('/trackers/')
@ApiTags('Trackers')
export class TrackersController {
  constructor(
    private trackersService: TrackersService,
    private trackerCredentialsService: TrackerCredentialsService,
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
    const trackerCredentials = await this.trackerCredentialsService.find();
    return trackerCredentials.map((trackerCredential) =>
      toDto(TrackerCredentialDto, trackerCredential),
    );
  }

  @ApiResponse({ status: 200 })
  @Delete('/hit-and-run')
  async cleanupHitAndRun() {
    return this.trackersService.cleanupHitAndRun();
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
    await this.trackerCredentialsService.delete(tracker);
  }
}
