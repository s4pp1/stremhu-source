import { MigrationInterface, QueryRunner } from 'typeorm';

export class SettingsStructureRefactor1768251172677 implements MigrationInterface {
  name = 'SettingsStructureRefactor1768251172677';

  public async up(queryRunner: QueryRunner): Promise<void> {
    await queryRunner.query(
      `CREATE TABLE "temporary_settings" ("key" text PRIMARY KEY NOT NULL, "value" text NOT NULL DEFAULT ('{}'))`,
    );
    await queryRunner.query(
      `INSERT INTO "temporary_settings"("key", "value")
       SELECT 'app',
              json_object('enebledlocalIp', "enebled_local_ip", 'address', "address")
       FROM "settings"
       LIMIT 1`,
    );
    await queryRunner.query(`DROP TABLE "settings"`);
    await queryRunner.query(
      `ALTER TABLE "temporary_settings" RENAME TO "settings"`,
    );
  }

  public async down(queryRunner: QueryRunner): Promise<void> {
    await queryRunner.query(
      `ALTER TABLE "settings" RENAME TO "temporary_settings"`,
    );
    await queryRunner.query(
      `CREATE TABLE "settings" ("id" text PRIMARY KEY NOT NULL, "enebled_local_ip" boolean NOT NULL DEFAULT (1), "upload_limit" integer NOT NULL DEFAULT (-1), "hit_and_run" boolean NOT NULL DEFAULT (0), "address" text, "download_limit" integer NOT NULL DEFAULT (-1), "catalog_token" text, "keep_seed_seconds" integer, "cache_retention_seconds" integer)`,
    );
    await queryRunner.query(
      `INSERT INTO "settings"("id", "enebled_local_ip", "address")
       SELECT 'app',
              json_extract("value", '$.enebledlocalIp'),
              json_extract("value", '$.address')
       FROM "temporary_settings"
       WHERE "key" = 'app'
       LIMIT 1`,
    );
    await queryRunner.query(`DROP TABLE "temporary_settings"`);
  }
}
