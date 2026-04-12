import {
  Body,
  Controller,
  HttpCode,
  Post,
  Req,
  Res,
  SerializeOptions,
  UseGuards,
} from '@nestjs/common';
import { ApiTags } from '@nestjs/swagger';
import { type Request, type Response } from 'express';

import { UserDto } from 'src/users/dto/user.dto';

import { AuthService } from './auth.service';
import { AuthLoginDto } from './dto/auth-login.dto';
import { AuthGuard } from './guards/auth.guard';

@Controller({ path: 'auth' })
@ApiTags('Authentication')
export class AuthController {
  constructor(private authService: AuthService) {}

  @SerializeOptions({ type: UserDto })
  @Post('login')
  async login(
    @Req() req: Request,
    @Body() payload: AuthLoginDto,
  ): Promise<UserDto> {
    const user = await this.authService.validate(
      payload.username,
      payload.password,
    );
    req.session.userId = user.id;

    return user;
  }

  @UseGuards(AuthGuard)
  @Post('logout')
  @HttpCode(200)
  logout(@Req() req: Request, @Res({ passthrough: true }) res: Response) {
    const { session } = req;

    if (session) {
      session.destroy(() => {});
    }

    res.cookie('connect.sid', '', { maxAge: 0 });
  }
}
