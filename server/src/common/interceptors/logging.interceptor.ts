import {
  CallHandler,
  ExecutionContext,
  Injectable,
  Logger,
  NestInterceptor,
} from '@nestjs/common';
import type { Request, Response } from 'express';
import { isArray } from 'lodash';
import { Observable } from 'rxjs';

@Injectable()
export class LoggingInterceptor implements NestInterceptor {
  private readonly logger = new Logger(LoggingInterceptor.name);

  intercept(ctx: ExecutionContext, next: CallHandler): Observable<any> {
    if (ctx.getType() !== 'http') return next.handle();

    const http = ctx.switchToHttp();
    const req = http.getRequest<Request>();
    const res = http.getResponse<Response>();

    const { method } = req;
    const url = req.originalUrl ?? req.url ?? '';
    const token = req.params?.token;

    let maskedUrl = url;

    if (!isArray(token)) {
      const encodedToken = encodeURIComponent(token);
      maskedUrl = maskedUrl.split(token).join('[USER_TOKEN]');
      if (encodedToken !== token) {
        maskedUrl = maskedUrl.split(encodedToken).join('[USER_TOKEN]');
      }
    }
    const started = Date.now();

    const onFinish = () => {
      const ms = Date.now() - started;
      this.logger.log(`${method} ${maskedUrl} ${res.statusCode} - +${ms}ms`);
      res.removeListener('finish', onFinish);
      res.removeListener('close', onFinish);
    };

    res.once('finish', onFinish);
    res.once('close', onFinish);

    return next.handle();
  }
}
