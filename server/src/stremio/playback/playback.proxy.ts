import { Request } from 'express';
import { createProxyMiddleware } from 'http-proxy-middleware';

import { RELAY_BASE_URL } from 'src/relay/relay.content';

const CANON: Record<string, string> = {
  'accept-ranges': 'Accept-Ranges',
  'content-length': 'Content-Length',
  'content-type': 'Content-Type',
  'content-range': 'Content-Range',
  'cache-control': 'Cache-Control',
  connection: 'Connection',
  'keep-alive': 'Keep-Alive',
  vary: 'Vary',
};

export const streamProxyMiddleware = createProxyMiddleware({
  target: RELAY_BASE_URL,
  changeOrigin: true,
  selfHandleResponse: false,
  pathRewrite: (_, req: Request) => {
    return `/stream/${req.infoHash}/${req.fileIndex}`;
  },
  on: {
    proxyReq(proxyReq, req, res) {
      const destroyProxyReq = () => {
        if (!proxyReq.destroyed) {
          proxyReq.destroy();
        }
      };

      req.once('aborted', destroyProxyReq);
      res.once('close', destroyProxyReq);
    },
    proxyRes(proxyRes) {
      for (const [key, canonKey] of Object.entries(CANON)) {
        const value = proxyRes.headers[key];

        if (value === undefined) {
          continue;
        }

        delete proxyRes.headers[key];
        proxyRes.headers[canonKey] = value;
      }
    },
  },
});
