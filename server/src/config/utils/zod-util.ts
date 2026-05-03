import { type ZodType, z } from 'zod';

type ConfigProps = {
  value: unknown;
  zod: ZodType<unknown>;
};

export type ZodConfig<T> = Record<keyof T, ConfigProps>;

export default class ZodUtil {
  static validate<T extends object>(config: ZodConfig<T>): T {
    const schemas = this.pick(config, 'zod');
    const values = this.pick(config, 'value');

    // Build a Zod object shape from typed keys
    const shape: Record<string, ZodType<unknown>> = {};
    for (const k of Object.keys(schemas) as Array<keyof T>) {
      shape[String(k)] = schemas[k];
    }

    const schema = z.object(shape);
    const parsed = schema.safeParse(values);

    if (!parsed.success) {
      const msg = parsed.error.issues
        .map((i) => `${i.path.join('.') || '(root)'}: ${i.message}`)
        .join('; ');
      throw new Error(
        `Validation failed - Is there an environment variable missing?\n${msg}`,
      );
    }
    return parsed.data as T;
  }

  private static pick<T extends object, P extends keyof ConfigProps>(
    config: ZodConfig<T>,
    prop: P,
  ): Record<keyof T, ConfigProps[P]> {
    const out = {} as Record<keyof T, ConfigProps[P]>;
    for (const key of Object.keys(config) as Array<keyof T>) {
      out[key] = config[key][prop];
    }
    return out;
  }
}
