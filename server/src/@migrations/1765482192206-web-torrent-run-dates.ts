import { MigrationInterface, QueryRunner } from 'typeorm';

export class WebTorrentRunDates1765482192206 implements MigrationInterface {
  name = 'WebTorrentRunDates1765482192206';

  public async up(queryRunner: QueryRunner): Promise<void> {
    await queryRunner.query(
      `CREATE TABLE "temporary_web_torrent_runs" ("tracker" varchar CHECK( "tracker" IN ('ncore','bithumen','majomparade') ) NOT NULL, "torrent_id" varchar NOT NULL, "info_hash" varchar NOT NULL, "imdb_id" varchar NOT NULL, "uploaded" integer NOT NULL DEFAULT (0), "updated_at" datetime NOT NULL DEFAULT (datetime('now')), "created_at" datetime NOT NULL DEFAULT (datetime('now')), CONSTRAINT "unique_web_torrent_run_tracker_torrent" UNIQUE ("tracker", "torrent_id"), PRIMARY KEY ("tracker", "torrent_id", "info_hash"))`,
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
      `CREATE TABLE "web_torrent_runs" ("tracker" varchar CHECK( "tracker" IN ('ncore','bithumen','majomparade') ) NOT NULL, "torrent_id" varchar NOT NULL, "info_hash" varchar NOT NULL, "imdb_id" varchar NOT NULL, "uploaded" integer NOT NULL DEFAULT (0), CONSTRAINT "unique_web_torrent_run_tracker_torrent" UNIQUE ("tracker", "torrent_id"), PRIMARY KEY ("tracker", "torrent_id", "info_hash"))`,
    );
    await queryRunner.query(
      `INSERT INTO "web_torrent_runs"("tracker", "torrent_id", "info_hash", "imdb_id", "uploaded") SELECT "tracker", "torrent_id", "info_hash", "imdb_id", "uploaded" FROM "temporary_web_torrent_runs"`,
    );
    await queryRunner.query(`DROP TABLE "temporary_web_torrent_runs"`);
  }
}
