import { z } from 'zod';

export const RelaySettingsSchema = z.object({
  port: z.number().int().default(6881).catch(6881),
  downloadLimit: z.number().int().default(0).catch(0),
  uploadLimit: z.number().int().default(0).catch(0),
  connectionsLimit: z.number().int().default(200).catch(200),
  torrentConnectionsLimit: z.number().int().default(20).catch(20),
  enableUpnpAndNatpmp: z.boolean().default(false).catch(false),
});
