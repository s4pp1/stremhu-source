import { MigrationInterface, QueryRunner } from 'typeorm';

export class BithumenCred1762636792261 implements MigrationInterface {
  name = 'BithumenCred1762636792261';

  public async up(queryRunner: QueryRunner): Promise<void> {
    await queryRunner.query(
      `CREATE TABLE "temporary_tracker_credentials" ("tracker" varchar CHECK( "tracker" IN ('ncore','bithumen') ) PRIMARY KEY NOT NULL, "username" text NOT NULL, "password" text NOT NULL)`,
    );
    await queryRunner.query(
      `INSERT INTO "temporary_tracker_credentials"("tracker", "username", "password") SELECT "tracker", "username", "password" FROM "tracker_credentials"`,
    );
    await queryRunner.query(`DROP TABLE "tracker_credentials"`);
    await queryRunner.query(
      `ALTER TABLE "temporary_tracker_credentials" RENAME TO "tracker_credentials"`,
    );
    await queryRunner.query(
      `CREATE TABLE "temporary_web_torrent_runs" ("tracker" varchar CHECK( "tracker" IN ('ncore') ) NOT NULL, "torrent_id" varchar NOT NULL, "info_hash" varchar NOT NULL, "imdb_id" varchar NOT NULL, "uploaded" integer NOT NULL DEFAULT (0), PRIMARY KEY ("tracker", "torrent_id", "info_hash"))`,
    );
    await queryRunner.query(
      `INSERT INTO "temporary_web_torrent_runs"("tracker", "torrent_id", "info_hash", "imdb_id", "uploaded") SELECT "tracker", "torrent_id", "info_hash", "imdb_id", "uploaded" FROM "web_torrent_runs"`,
    );
    await queryRunner.query(`DROP TABLE "web_torrent_runs"`);
    await queryRunner.query(
      `ALTER TABLE "temporary_web_torrent_runs" RENAME TO "web_torrent_runs"`,
    );
    await queryRunner.query(
      `CREATE TABLE "temporary_web_torrent_runs" ("tracker" varchar CHECK( "tracker" IN ('ncore','bithumen') ) NOT NULL, "torrent_id" varchar NOT NULL, "info_hash" varchar NOT NULL, "imdb_id" varchar NOT NULL, "uploaded" integer NOT NULL DEFAULT (0), PRIMARY KEY ("tracker", "torrent_id", "info_hash"))`,
    );
    await queryRunner.query(
      `INSERT INTO "temporary_web_torrent_runs"("tracker", "torrent_id", "info_hash", "imdb_id", "uploaded") SELECT "tracker", "torrent_id", "info_hash", "imdb_id", "uploaded" FROM "web_torrent_runs"`,
    );
    await queryRunner.query(`DROP TABLE "web_torrent_runs"`);
    await queryRunner.query(
      `ALTER TABLE "temporary_web_torrent_runs" RENAME TO "web_torrent_runs"`,
    );
    await queryRunner.query(
      `CREATE TABLE "temporary_web_torrent_runs" ("tracker" varchar CHECK( "tracker" IN ('ncore','bithumen') ) NOT NULL, "torrent_id" varchar NOT NULL, "info_hash" varchar NOT NULL, "imdb_id" varchar NOT NULL, "uploaded" integer NOT NULL DEFAULT (0), CONSTRAINT "unique_web_torrent_run_tracker_torrent" UNIQUE ("tracker", "torrent_id"), PRIMARY KEY ("tracker", "torrent_id", "info_hash"))`,
    );
    await queryRunner.query(
      `INSERT INTO "temporary_web_torrent_runs"("tracker", "torrent_id", "info_hash", "imdb_id", "uploaded") SELECT "tracker", "torrent_id", "info_hash", "imdb_id", "uploaded" FROM "web_torrent_runs"`,
    );
    await queryRunner.query(`DROP TABLE "web_torrent_runs"`);
    await queryRunner.query(
      `ALTER TABLE "temporary_web_torrent_runs" RENAME TO "web_torrent_runs"`,
    );
  }

  public async down(queryRunner: QueryRunner): Promise<void> {
    await queryRunner.query(
      `ALTER TABLE "web_torrent_runs" RENAME TO "temporary_web_torrent_runs"`,
    );
    await queryRunner.query(
      `CREATE TABLE "web_torrent_runs" ("tracker" varchar CHECK( "tracker" IN ('ncore','bithumen') ) NOT NULL, "torrent_id" varchar NOT NULL, "info_hash" varchar NOT NULL, "imdb_id" varchar NOT NULL, "uploaded" integer NOT NULL DEFAULT (0), PRIMARY KEY ("tracker", "torrent_id", "info_hash"))`,
    );
    await queryRunner.query(
      `INSERT INTO "web_torrent_runs"("tracker", "torrent_id", "info_hash", "imdb_id", "uploaded") SELECT "tracker", "torrent_id", "info_hash", "imdb_id", "uploaded" FROM "temporary_web_torrent_runs"`,
    );
    await queryRunner.query(`DROP TABLE "temporary_web_torrent_runs"`);
    await queryRunner.query(
      `ALTER TABLE "web_torrent_runs" RENAME TO "temporary_web_torrent_runs"`,
    );
    await queryRunner.query(
      `CREATE TABLE "web_torrent_runs" ("tracker" varchar CHECK( "tracker" IN ('ncore') ) NOT NULL, "torrent_id" varchar NOT NULL, "info_hash" varchar NOT NULL, "imdb_id" varchar NOT NULL, "uploaded" integer NOT NULL DEFAULT (0), PRIMARY KEY ("tracker", "torrent_id", "info_hash"))`,
    );
    await queryRunner.query(
      `INSERT INTO "web_torrent_runs"("tracker", "torrent_id", "info_hash", "imdb_id", "uploaded") SELECT "tracker", "torrent_id", "info_hash", "imdb_id", "uploaded" FROM "temporary_web_torrent_runs"`,
    );
    await queryRunner.query(`DROP TABLE "temporary_web_torrent_runs"`);
    await queryRunner.query(
      `ALTER TABLE "web_torrent_runs" RENAME TO "temporary_web_torrent_runs"`,
    );
    await queryRunner.query(
      `CREATE TABLE "web_torrent_runs" ("tracker" varchar CHECK( "tracker" IN ('ncore') ) NOT NULL, "torrent_id" varchar NOT NULL, "info_hash" varchar NOT NULL, "imdb_id" varchar NOT NULL, "uploaded" integer NOT NULL DEFAULT (0), CONSTRAINT "unique_web_torrent_run_tracker_torrent" UNIQUE ("tracker", "torrent_id"), PRIMARY KEY ("tracker", "torrent_id", "info_hash"))`,
    );
    await queryRunner.query(
      `INSERT INTO "web_torrent_runs"("tracker", "torrent_id", "info_hash", "imdb_id", "uploaded") SELECT "tracker", "torrent_id", "info_hash", "imdb_id", "uploaded" FROM "temporary_web_torrent_runs"`,
    );
    await queryRunner.query(`DROP TABLE "temporary_web_torrent_runs"`);
    await queryRunner.query(
      `ALTER TABLE "tracker_credentials" RENAME TO "temporary_tracker_credentials"`,
    );
    await queryRunner.query(
      `CREATE TABLE "tracker_credentials" ("tracker" varchar CHECK( "tracker" IN ('ncore') ) PRIMARY KEY NOT NULL, "username" text NOT NULL, "password" text NOT NULL)`,
    );
    await queryRunner.query(
      `INSERT INTO "tracker_credentials"("tracker", "username", "password") SELECT "tracker", "username", "password" FROM "temporary_tracker_credentials"`,
    );
    await queryRunner.query(`DROP TABLE "temporary_tracker_credentials"`);
  }
}
