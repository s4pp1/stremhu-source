import { MigrationInterface, QueryRunner } from 'typeorm';

export class CatalogToken1763657893263 implements MigrationInterface {
  name = 'CatalogToken1763657893263';

  public async up(queryRunner: QueryRunner): Promise<void> {
    await queryRunner.query(
      `CREATE TABLE "temporary_settings" ("id" text PRIMARY KEY NOT NULL, "enebled_local_ip" boolean NOT NULL DEFAULT (0), "endpoint" text NOT NULL, "upload_limit" integer NOT NULL DEFAULT (-1), "hit_and_run" boolean NOT NULL DEFAULT (1), "cache_retention" text, "catalog_token" text)`,
    );
    await queryRunner.query(
      `INSERT INTO "temporary_settings"("id", "enebled_local_ip", "endpoint", "upload_limit", "hit_and_run", "cache_retention") SELECT "id", "enebled_local_ip", "endpoint", "upload_limit", "hit_and_run", "cache_retention" FROM "settings"`,
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
      `CREATE TABLE "settings" ("id" text PRIMARY KEY NOT NULL, "enebled_local_ip" boolean NOT NULL DEFAULT (0), "endpoint" text NOT NULL, "upload_limit" integer NOT NULL DEFAULT (-1), "hit_and_run" boolean NOT NULL DEFAULT (1), "cache_retention" text)`,
    );
    await queryRunner.query(
      `INSERT INTO "settings"("id", "enebled_local_ip", "endpoint", "upload_limit", "hit_and_run", "cache_retention") SELECT "id", "enebled_local_ip", "endpoint", "upload_limit", "hit_and_run", "cache_retention" FROM "temporary_settings"`,
    );
    await queryRunner.query(`DROP TABLE "temporary_settings"`);
  }
}
