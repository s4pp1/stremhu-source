import {
  Body,
  Controller,
  Delete,
  Get,
  Param,
  ParseEnumPipe,
  ParseUUIDPipe,
  Post,
  Put,
  UseGuards,
} from '@nestjs/common';
import {
  ApiBody,
  ApiExtraModels,
  ApiParam,
  ApiResponse,
  ApiTags,
  getSchemaPath,
} from '@nestjs/swagger';

import { Roles } from 'src/auth/decorators/roles.decorator';
import { AuthGuard } from 'src/auth/guards/auth.guard';
import { RolesGuard } from 'src/auth/guards/roles.guard';
import { toDto } from 'src/common/utils/to-dto';
import type { PreferenceDto } from 'src/preferences/dto/preference.dto';
import {
  PREFERENCE_SWAGGER_MODELS,
  preferenceDtoMap,
} from 'src/preferences/dto/preference.dto';
import { ReorderPreferencesDto } from 'src/preferences/dto/reorder-preferences.dto';
import { PreferenceEnum } from 'src/preferences/enum/preference.enum';
import { UserPreferencesService } from 'src/users/preferences/user-preferences.service';

import { UserRoleEnum } from '../enum/user-role.enum';

@UseGuards(AuthGuard, RolesGuard)
@Roles(UserRoleEnum.ADMIN)
@Controller('/users/:userId/preferences')
@ApiExtraModels(...PREFERENCE_SWAGGER_MODELS)
@ApiTags('User Preferences')
export class UserPreferencesController {
  constructor(
    private readonly userPreferencesService: UserPreferencesService,
  ) {}

  @ApiBody({
    schema: {
      oneOf: PREFERENCE_SWAGGER_MODELS.map((model) => ({
        $ref: getSchemaPath(model),
      })),
    },
  })
  @Post('/')
  async create(
    @Param('userId', new ParseUUIDPipe()) userId: string,
    @Body() payload: PreferenceDto,
  ) {
    const userPreference = await this.userPreferencesService.create(
      userId,
      payload,
    );
    return toDto(preferenceDtoMap[userPreference.preference], userPreference);
  }

  @ApiResponse({
    status: 200,
    schema: {
      type: 'array',
      items: {
        oneOf: PREFERENCE_SWAGGER_MODELS.map((model) => ({
          $ref: getSchemaPath(model),
        })),
      },
    },
  })
  @Get('/')
  async find(@Param('userId', new ParseUUIDPipe()) userId: string) {
    const userPreferences = await this.userPreferencesService.find(userId);

    return userPreferences.map((userPreference) =>
      toDto(preferenceDtoMap[userPreference.preference], userPreference),
    );
  }

  @ApiResponse({
    status: 200,
    schema: {
      type: 'array',
      items: {
        oneOf: PREFERENCE_SWAGGER_MODELS.map((model) => ({
          $ref: getSchemaPath(model),
        })),
      },
    },
  })
  @Post('/reorder')
  async reorder(
    @Param('userId', new ParseUUIDPipe()) userId: string,
    @Body() payload: ReorderPreferencesDto,
  ) {
    const userPreferences = await this.userPreferencesService.reorder(
      userId,
      payload.preferences,
    );

    return userPreferences.map((userPreference) =>
      toDto(preferenceDtoMap[userPreference.preference], userPreference),
    );
  }

  @ApiParam({
    name: 'preference',
    type: 'enum',
    enum: PreferenceEnum,
    enumName: 'PreferenceEnum',
  })
  @ApiResponse({
    status: 200,
    schema: {
      oneOf: PREFERENCE_SWAGGER_MODELS.map((model) => ({
        $ref: getSchemaPath(model),
      })),
    },
  })
  @Get('/:preference')
  async findOne(
    @Param('userId', new ParseUUIDPipe()) userId: string,
    @Param('preference', new ParseEnumPipe(PreferenceEnum))
    preference: PreferenceEnum,
  ) {
    const userPreference =
      await this.userPreferencesService.findOneByPreferenceOrThrow(
        userId,
        preference,
      );

    return toDto(preferenceDtoMap[userPreference.preference], userPreference);
  }

  @ApiParam({
    name: 'preference',
    type: 'enum',
    enum: PreferenceEnum,
    enumName: 'PreferenceEnum',
  })
  @ApiBody({
    schema: {
      oneOf: PREFERENCE_SWAGGER_MODELS.map((model) => ({
        $ref: getSchemaPath(model),
      })),
    },
  })
  @ApiResponse({
    status: 200,
    schema: {
      oneOf: PREFERENCE_SWAGGER_MODELS.map((model) => ({
        $ref: getSchemaPath(model),
      })),
    },
  })
  @Put('/:preference')
  async update(
    @Param('userId', new ParseUUIDPipe()) userId: string,
    @Param('preference', new ParseEnumPipe(PreferenceEnum))
    preference: PreferenceEnum,
    @Body() payload: PreferenceDto,
  ) {
    const userPreference = await this.userPreferencesService.updateOne(
      userId,
      preference,
      payload,
    );

    return toDto(preferenceDtoMap[userPreference.preference], userPreference);
  }

  @ApiParam({ name: 'preference', type: 'enum', enum: PreferenceEnum })
  @Delete('/:preference')
  async delete(
    @Param('userId', new ParseUUIDPipe()) userId: string,
    @Param('preference', new ParseEnumPipe(PreferenceEnum))
    preference: PreferenceEnum,
  ) {
    await this.userPreferencesService.deleteByPreference(userId, preference);
  }
}
