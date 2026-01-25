import { Request } from 'express';
import { createProxyMiddleware } from 'http-proxy-middleware';

import { RELAY_BASE_URL } from 'src/relay/relay.content';

export const streamProxyMiddleware = createProxyMiddleware({
  target: RELAY_BASE_URL,
  changeOrigin: true,
  selfHandleResponse: false,
  pathRewrite: (_, req: Request) => {
    return `/stream/${req.infoHash}/${req.fileIndex}`;
  },
});
