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

import { OptionalAuth } from 'src/auth/decorators/optional-auth.decorator';
import { AuthGuard } from 'src/auth/guards/auth.guard';
import { toDto } from 'src/common/utils/to-dto';
import type { PreferenceDto } from 'src/preferences/dto/preference.dto';
import {
  PREFERENCE_SWAGGER_MODELS,
  preferenceDtoMap,
} from 'src/preferences/dto/preference.dto';
import { ReorderPreferencesDto } from 'src/preferences/dto/reorder-preferences.dto';
import { PreferenceEnum } from 'src/preferences/enum/preference.enum';
import { UserPreferencesService } from 'src/user-preferences/user-preferences.service';

import { UserDto } from '../users/dto/user.dto';
import { UsersService } from '../users/users.service';
import { MeDto } from './dto/me.dto';
import { UpdateMeDto } from './dto/update-me.dto';

@ApiExtraModels(...PREFERENCE_SWAGGER_MODELS)
@ApiTags('Me')
@UseGuards(AuthGuard)
@Controller('/me')
export class MeController {
  constructor(
    private readonly usersService: UsersService,
    private readonly userPreferencesService: UserPreferencesService,
  ) {}

  @ApiResponse({
    status: 200,
    type: MeDto,
  })
  @OptionalAuth()
  @Get('/')
  me(@Req() req: Request): MeDto {
    return { me: req.user ? toDto(UserDto, req.user) : null };
  }

  @ApiResponse({ status: 200, type: UserDto })
  @Put('/')
  async updateMe(
    @Req() req: Request,
    @Body() payload: UpdateMeDto,
  ): Promise<UserDto> {
    const user = await this.usersService.updateOrThrow(req.user!.id, payload);
    return toDto(UserDto, user);
  }

  @ApiBody({
    schema: {
      oneOf: PREFERENCE_SWAGGER_MODELS.map((model) => ({
        $ref: getSchemaPath(model),
      })),
    },
  })
  @Post('/preferences')
  async createMePreference(
    @Req() req: Request,
    @Body() payload: PreferenceDto,
  ) {
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
  @Get('/preferences')
  async mePreferences(@Req() req: Request) {
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
  @Post('/preferences/reorder')
  async mePreferenceReorder(
    @Req() req: Request,
    @Body() payload: ReorderPreferencesDto,
  ) {
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
  @Get('/preferences/:preference')
  async mePreference(
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
  @Put('/preferences/:preference')
  async updateMePreference(
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
  @Delete('/preferences/:preference')
  async deleteMePreference(
    @Req() req: Request,
    @Param('preference', new ParseEnumPipe(PreferenceEnum))
    preference: PreferenceEnum,
  ) {
    await this.userPreferencesService.deleteByPreference(
      req.user!.id,
      preference,
    );
  }

  @ApiResponse({ status: 201, type: UserDto })
  @Put('/token/regenerate')
  async regenerateToken(@Req() req: Request): Promise<UserDto> {
    const user = await this.usersService.regenerateToken(req.user!.id);
    return toDto(UserDto, user);
  }
}
