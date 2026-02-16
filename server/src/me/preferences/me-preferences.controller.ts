import {
  Body,
  Controller,
  Delete,
  Get,
  Param,
  ParseEnumPipe,
  Post,
  Put,
  Req,
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
import type { Request } from 'express';

import { AuthGuard } from 'src/auth/guards/auth.guard';
import { toDto } from 'src/common/utils/to-dto';
import type { PreferenceDto } from 'src/preferences/dto/preference.dto';
import {
  PREFERENCE_SWAGGER_MODELS,
  preferenceDtoMap,
} from 'src/preferences/dto/preference.dto';
import { ReorderPreferencesDto } from 'src/preferences/dto/reorder-preferences.dto';
import { PreferenceEnum } from 'src/preferences/enum/preference.enum';
import { UserPreferencesService } from 'src/users/preferences/user-preferences.service';

@ApiExtraModels(...PREFERENCE_SWAGGER_MODELS)
@UseGuards(AuthGuard)
@Controller('/me/preference')
@ApiTags('Me Preferences')
export class MePreferencesController {
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
  async create(@Req() req: Request, @Body() payload: PreferenceDto) {
    const userPreference = await this.userPreferencesService.create(
      req.user!.id,
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
  async find(@Req() req: Request) {
    const userPreferences = await this.userPreferencesService.find(
      req.user!.id,
    );

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
  async reorder(@Req() req: Request, @Body() payload: ReorderPreferencesDto) {
    const userPreferences = await this.userPreferencesService.reorder(
      req.user!.id,
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
    @Req() req: Request,
    @Param('preference', new ParseEnumPipe(PreferenceEnum))
    preference: PreferenceEnum,
  ) {
    const userPreference =
      await this.userPreferencesService.findOneByPreferenceOrThrow(
        req.user!.id,
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
    @Req() req: Request,
    @Param('preference', new ParseEnumPipe(PreferenceEnum))
    preference: PreferenceEnum,
    @Body() payload: PreferenceDto,
  ) {
    const userPreference = await this.userPreferencesService.updateOne(
      req.user!.id,
      preference,
      payload,
    );

    return toDto(preferenceDtoMap[userPreference.preference], userPreference);
  }

  @ApiParam({ name: 'preference', type: 'enum', enum: PreferenceEnum })
  @Delete('/:preference')
  async delete(
    @Req() req: Request,
    @Param('preference', new ParseEnumPipe(PreferenceEnum))
    preference: PreferenceEnum,
  ) {
    await this.userPreferencesService.deleteByPreference(
      req.user!.id,
      preference,
    );
  }
}
