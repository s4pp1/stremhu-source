import { z } from 'zod';

import { RelaySettingsSchema } from '../schema/relay-settings.schema';

export type RelaySettings = z.infer<typeof RelaySettingsSchema>;
