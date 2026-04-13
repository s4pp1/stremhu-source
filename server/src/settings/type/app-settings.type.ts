import { z } from 'zod';

import { AppSettingsSchema } from '../schema/app-settings.schema';

export type AppSettings = z.infer<typeof AppSettingsSchema>;
