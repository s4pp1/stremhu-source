import { MigrationInterface, QueryRunner } from 'typeorm';

export class InsaneIntegralasa1769360214276 implements MigrationInterface {
  name = 'InsaneIntegralasa1769360214276';

  public async up(queryRunner: QueryRunner): Promise<void> {
    await queryRunner.query(
      `CREATE TABLE "temporary_trackers" ("tracker" varchar CHECK( "tracker" IN ('ncore','bithumen','majomparade','insane') ) PRIMARY KEY NOT NULL, "username" text NOT NULL, "password" text NOT NULL, "hit_and_run" boolean, "keep_seed_seconds" integer, "download_full_torrent" boolean NOT NULL DEFAULT (0), "order_index" integer NOT NULL DEFAULT (0), "updated_at" datetime NOT NULL DEFAULT (datetime('now')), "created_at" datetime NOT NULL DEFAULT (datetime('now')))`,
    );
    await queryRunner.query(
      `INSERT INTO "temporary_trackers"("tracker", "username", "password", "hit_and_run", "keep_seed_seconds", "download_full_torrent", "order_index", "updated_at", "created_at") SELECT "tracker", "username", "password", "hit_and_run", "keep_seed_seconds", "download_full_torrent", "order_index", "updated_at", "created_at" FROM "trackers"`,
    );
    await queryRunner.query(`DROP TABLE "trackers"`);
    await queryRunner.query(
      `ALTER TABLE "temporary_trackers" RENAME TO "trackers"`,
    );
    await queryRunner.query(
      `CREATE TABLE "temporary_torrents" ("tracker" varchar CHECK( "tracker" IN ('ncore','bithumen','majomparade') ) NOT NULL, "torrent_id" varchar NOT NULL, "info_hash" varchar PRIMARY KEY NOT NULL, "imdb_id" varchar NOT NULL, "uploaded" integer NOT NULL DEFAULT (0), "updated_at" datetime NOT NULL DEFAULT (datetime('now')), "created_at" datetime NOT NULL DEFAULT (datetime('now')), "is_persisted" boolean NOT NULL DEFAULT (0), "last_played_at" datetime NOT NULL)`,
    );
    await queryRunner.query(
      `INSERT INTO "temporary_torrents"("tracker", "torrent_id", "info_hash", "imdb_id", "uploaded", "updated_at", "created_at", "is_persisted", "last_played_at") SELECT "tracker", "torrent_id", "info_hash", "imdb_id", "uploaded", "updated_at", "created_at", "is_persisted", "last_played_at" FROM "torrents"`,
    );
    await queryRunner.query(`DROP TABLE "torrents"`);
    await queryRunner.query(
      `ALTER TABLE "temporary_torrents" RENAME TO "torrents"`,
    );
    await queryRunner.query(
      `CREATE TABLE "temporary_torrents" ("tracker" varchar CHECK( "tracker" IN ('ncore','bithumen','majomparade','insane') ) NOT NULL, "torrent_id" varchar NOT NULL, "info_hash" varchar PRIMARY KEY NOT NULL, "imdb_id" varchar NOT NULL, "uploaded" integer NOT NULL DEFAULT (0), "updated_at" datetime NOT NULL DEFAULT (datetime('now')), "created_at" datetime NOT NULL DEFAULT (datetime('now')), "is_persisted" boolean NOT NULL DEFAULT (0), "last_played_at" datetime NOT NULL)`,
    );
    await queryRunner.query(
      `INSERT INTO "temporary_torrents"("tracker", "torrent_id", "info_hash", "imdb_id", "uploaded", "updated_at", "created_at", "is_persisted", "last_played_at") SELECT "tracker", "torrent_id", "info_hash", "imdb_id", "uploaded", "updated_at", "created_at", "is_persisted", "last_played_at" FROM "torrents"`,
    );
    await queryRunner.query(`DROP TABLE "torrents"`);
    await queryRunner.query(
      `ALTER TABLE "temporary_torrents" RENAME TO "torrents"`,
    );
    await queryRunner.query(
      `CREATE TABLE "temporary_torrents" ("tracker" varchar CHECK( "tracker" IN ('ncore','bithumen','majomparade','insane') ) NOT NULL, "torrent_id" varchar NOT NULL, "info_hash" varchar PRIMARY KEY NOT NULL, "imdb_id" varchar NOT NULL, "uploaded" integer NOT NULL DEFAULT (0), "updated_at" datetime NOT NULL DEFAULT (datetime('now')), "created_at" datetime NOT NULL DEFAULT (datetime('now')), "is_persisted" boolean NOT NULL DEFAULT (0), "last_played_at" datetime NOT NULL, CONSTRAINT "unique_torrent_imdb_id_tracker_torrent_id" UNIQUE ("imdb_id", "tracker", "torrent_id"))`,
    );
    await queryRunner.query(
      `INSERT INTO "temporary_torrents"("tracker", "torrent_id", "info_hash", "imdb_id", "uploaded", "updated_at", "created_at", "is_persisted", "last_played_at") SELECT "tracker", "torrent_id", "info_hash", "imdb_id", "uploaded", "updated_at", "created_at", "is_persisted", "last_played_at" FROM "torrents"`,
    );
    await queryRunner.query(`DROP TABLE "torrents"`);
    await queryRunner.query(
      `ALTER TABLE "temporary_torrents" RENAME TO "torrents"`,
    );
  }

  public async down(queryRunner: QueryRunner): Promise<void> {
    await queryRunner.query(
      `ALTER TABLE "torrents" RENAME TO "temporary_torrents"`,
    );
    await queryRunner.query(
      `CREATE TABLE "torrents" ("tracker" varchar CHECK( "tracker" IN ('ncore','bithumen','majomparade','insane') ) NOT NULL, "torrent_id" varchar NOT NULL, "info_hash" varchar PRIMARY KEY NOT NULL, "imdb_id" varchar NOT NULL, "uploaded" integer NOT NULL DEFAULT (0), "updated_at" datetime NOT NULL DEFAULT (datetime('now')), "created_at" datetime NOT NULL DEFAULT (datetime('now')), "is_persisted" boolean NOT NULL DEFAULT (0), "last_played_at" datetime NOT NULL)`,
    );
    await queryRunner.query(
      `INSERT INTO "torrents"("tracker", "torrent_id", "info_hash", "imdb_id", "uploaded", "updated_at", "created_at", "is_persisted", "last_played_at") SELECT "tracker", "torrent_id", "info_hash", "imdb_id", "uploaded", "updated_at", "created_at", "is_persisted", "last_played_at" FROM "temporary_torrents"`,
    );
    await queryRunner.query(`DROP TABLE "temporary_torrents"`);
    await queryRunner.query(
      `ALTER TABLE "torrents" RENAME TO "temporary_torrents"`,
    );
    await queryRunner.query(
      `CREATE TABLE "torrents" ("tracker" varchar CHECK( "tracker" IN ('ncore','bithumen','majomparade') ) NOT NULL, "torrent_id" varchar NOT NULL, "info_hash" varchar PRIMARY KEY NOT NULL, "imdb_id" varchar NOT NULL, "uploaded" integer NOT NULL DEFAULT (0), "updated_at" datetime NOT NULL DEFAULT (datetime('now')), "created_at" datetime NOT NULL DEFAULT (datetime('now')), "is_persisted" boolean NOT NULL DEFAULT (0), "last_played_at" datetime NOT NULL)`,
    );
    await queryRunner.query(
      `INSERT INTO "torrents"("tracker", "torrent_id", "info_hash", "imdb_id", "uploaded", "updated_at", "created_at", "is_persisted", "last_played_at") SELECT "tracker", "torrent_id", "info_hash", "imdb_id", "uploaded", "updated_at", "created_at", "is_persisted", "last_played_at" FROM "temporary_torrents"`,
    );
    await queryRunner.query(`DROP TABLE "temporary_torrents"`);
    await queryRunner.query(
      `ALTER TABLE "torrents" RENAME TO "temporary_torrents"`,
    );
    await queryRunner.query(
      `CREATE TABLE "torrents" ("tracker" varchar CHECK( "tracker" IN ('ncore','bithumen','majomparade') ) NOT NULL, "torrent_id" varchar NOT NULL, "info_hash" varchar PRIMARY KEY NOT NULL, "imdb_id" varchar NOT NULL, "uploaded" integer NOT NULL DEFAULT (0), "updated_at" datetime NOT NULL DEFAULT (datetime('now')), "created_at" datetime NOT NULL DEFAULT (datetime('now')), "is_persisted" boolean NOT NULL DEFAULT (0), "last_played_at" datetime NOT NULL, CONSTRAINT "unique_torrent_imdb_id_tracker_torrent_id" UNIQUE ("imdb_id", "tracker", "torrent_id"))`,
    );
    await queryRunner.query(
      `INSERT INTO "torrents"("tracker", "torrent_id", "info_hash", "imdb_id", "uploaded", "updated_at", "created_at", "is_persisted", "last_played_at") SELECT "tracker", "torrent_id", "info_hash", "imdb_id", "uploaded", "updated_at", "created_at", "is_persisted", "last_played_at" FROM "temporary_torrents"`,
    );
    await queryRunner.query(`DROP TABLE "temporary_torrents"`);
    await queryRunner.query(
      `ALTER TABLE "trackers" RENAME TO "temporary_trackers"`,
    );
    await queryRunner.query(
      `CREATE TABLE "trackers" ("tracker" varchar CHECK( "tracker" IN ('ncore','bithumen','majomparade') ) PRIMARY KEY NOT NULL, "username" text NOT NULL, "password" text NOT NULL, "hit_and_run" boolean, "keep_seed_seconds" integer, "download_full_torrent" boolean NOT NULL DEFAULT (0), "order_index" integer NOT NULL DEFAULT (0), "updated_at" datetime NOT NULL DEFAULT (datetime('now')), "created_at" datetime NOT NULL DEFAULT (datetime('now')))`,
    );
    await queryRunner.query(
      `INSERT INTO "trackers"("tracker", "username", "password", "hit_and_run", "keep_seed_seconds", "download_full_torrent", "order_index", "updated_at", "created_at") SELECT "tracker", "username", "password", "hit_and_run", "keep_seed_seconds", "download_full_torrent", "order_index", "updated_at", "created_at" FROM "temporary_trackers"`,
    );
    await queryRunner.query(`DROP TABLE "temporary_trackers"`);
  }
}
