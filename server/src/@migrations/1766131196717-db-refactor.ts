import ms from 'ms';
import { MigrationInterface, QueryRunner } from 'typeorm';

export class DbRefactor1766131196717 implements MigrationInterface {
  name = 'DbRefactor1766131196717';

  public async up(queryRunner: QueryRunner): Promise<void> {
    // "web_torrent_runs" frissítése és átnevezés "torrents"-ra
    await queryRunner.query(
      `CREATE TABLE "temporary_web_torrent_runs" ("tracker" varchar CHECK( "tracker" IN ('ncore','bithumen','majomparade') ) NOT NULL, "torrent_id" varchar NOT NULL, "info_hash" varchar PRIMARY KEY NOT NULL, "imdb_id" varchar NOT NULL, "uploaded" integer NOT NULL DEFAULT (0), "updated_at" datetime NOT NULL DEFAULT (datetime('now')), "created_at" datetime NOT NULL DEFAULT (datetime('now')), "is_persisted" boolean NOT NULL DEFAULT (0), "last_played_at" datetime NOT NULL DEFAULT (datetime('now')), CONSTRAINT "unique_torrent_imdb_id_tracker_torrent_id" UNIQUE ("imdb_id", "tracker", "torrent_id"))`,
    );
    await queryRunner.query(
      `INSERT INTO "temporary_web_torrent_runs"("tracker", "torrent_id", "info_hash", "imdb_id", "uploaded", "updated_at", "created_at", "is_persisted", "last_played_at") SELECT "tracker", "torrent_id", "info_hash", "imdb_id", "uploaded", "updated_at", "created_at", 0, datetime('now') FROM "web_torrent_runs"`,
    );
    await queryRunner.query(`DROP TABLE "web_torrent_runs"`);
    await queryRunner.query(
      `ALTER TABLE "temporary_web_torrent_runs" RENAME TO "torrents"`,
    );

    // "users" frissítése
    await queryRunner.query(`DROP INDEX "IDX_37a561a6cfd07ed41e9f2d09d6"`);

    // "users" frissítés
    await queryRunner.query(
      `CREATE TABLE "temporary_users" ("id" varchar PRIMARY KEY NOT NULL, "username" varchar NOT NULL, "password_hash" text, "user_role" varchar CHECK( "user_role" IN ('admin','user') ) NOT NULL, "torrent_resolutions" text NOT NULL DEFAULT ('["2160P","1080P","720P","576P","540P","480P"]'), "torrent_languages" text NOT NULL DEFAULT ('["hu","en"]'), "torrent_seed" integer, "token" varchar NOT NULL, "updated_at" datetime NOT NULL DEFAULT (datetime('now')), "created_at" datetime NOT NULL DEFAULT (datetime('now')), CONSTRAINT "UQ_fe0bb3f6520ee0469504521e710" UNIQUE ("username"))`,
    );
    await queryRunner.query(
      `INSERT INTO "temporary_users"("id", "username", "password_hash", "user_role", "torrent_resolutions", "torrent_languages", "torrent_seed", "token") SELECT "id", "username", "password_hash", "user_role", "torrent_resolutions", "torrent_languages", "torrent_seed", "stremio_token" FROM "users"`,
    );
    await queryRunner.query(`DROP TABLE "users"`);
    await queryRunner.query(`ALTER TABLE "temporary_users" RENAME TO "users"`);

    // "settings" frissítése
    const rows = (await queryRunner.query(
      `SELECT "id", "cache_retention" FROM "settings"`,
    )) as Array<{ id: string; cache_retention: string | null }>;

    await queryRunner.query(
      `CREATE TABLE "temporary_settings" ("id" text PRIMARY KEY NOT NULL, "enebled_local_ip" boolean NOT NULL DEFAULT (1), "upload_limit" integer NOT NULL DEFAULT (-1), "hit_and_run" boolean NOT NULL DEFAULT (0), "address" text, "download_limit" integer NOT NULL DEFAULT (-1), "catalog_token" text, "keep_seed_seconds" integer, "cache_retention_seconds" integer)`,
    );
    await queryRunner.query(
      `INSERT INTO "temporary_settings"("id", "enebled_local_ip", "upload_limit", "hit_and_run", "address", "download_limit", "catalog_token") SELECT "id", "enebled_local_ip", "upload_limit", "hit_and_run", "address", "download_limit", "catalog_token" FROM "settings"`,
    );
    await queryRunner.query(`DROP TABLE "settings"`);
    await queryRunner.query(
      `ALTER TABLE "temporary_settings" RENAME TO "settings"`,
    );

    for (const row of rows) {
      if (!row.cache_retention) continue;
      const parsedMs = ms(row.cache_retention as ms.StringValue);
      if (!parsedMs) continue;

      const seconds = Math.floor(parsedMs / 1000);
      await queryRunner.query(
        `UPDATE "settings" SET "cache_retention_seconds" = ? WHERE "id" = ?`,
        [seconds, row.id],
      );
    }

    // "trackers" frissítés
    await queryRunner.query(
      `CREATE TABLE "temporary_trackers" ("tracker" varchar CHECK( "tracker" IN ('ncore','bithumen','majomparade') ) PRIMARY KEY NOT NULL, "username" text NOT NULL, "password" text NOT NULL, "hit_and_run" boolean, "keep_seed_seconds" integer, "download_full_torrent" boolean NOT NULL DEFAULT (0), "order_index" integer NOT NULL DEFAULT (0), "updated_at" datetime NOT NULL DEFAULT (datetime('now')), "created_at" datetime NOT NULL DEFAULT (datetime('now')))`,
    );
    await queryRunner.query(
      `INSERT INTO "temporary_trackers"("tracker", "username", "password") SELECT "tracker", "username", "password" FROM "tracker_credentials"`,
    );
    await queryRunner.query(`DROP TABLE "tracker_credentials"`);
    await queryRunner.query(
      `ALTER TABLE "temporary_trackers" RENAME TO "trackers"`,
    );
    await queryRunner.query(
      `UPDATE "trackers" SET "download_full_torrent" = 1 WHERE "tracker" = 'majomparade'`,
    );
    await queryRunner.query(
      `CREATE INDEX "IDX_7869db61ed722d562da1acf6d5" ON "users" ("token") `,
    );
  }

  public async down(queryRunner: QueryRunner): Promise<void> {
    // "web_torrent_runs" visszaállítás
    await queryRunner.query(
      `ALTER TABLE "torrents" RENAME TO "temporary_web_torrent_runs"`,
    );
    await queryRunner.query(
      `CREATE TABLE "web_torrent_runs" ("tracker" varchar CHECK( "tracker" IN ('ncore','bithumen','majomparade') ) NOT NULL, "torrent_id" varchar NOT NULL, "info_hash" varchar NOT NULL, "imdb_id" varchar NOT NULL, "uploaded" integer NOT NULL DEFAULT (0), "updated_at" datetime NOT NULL DEFAULT (datetime('now')), "created_at" datetime NOT NULL DEFAULT (datetime('now')), CONSTRAINT "unique_web_torrent_run_tracker_torrent" UNIQUE ("tracker", "torrent_id"), PRIMARY KEY ("tracker", "torrent_id", "info_hash"))`,
    );
    await queryRunner.query(
      `INSERT INTO "web_torrent_runs"("tracker", "torrent_id", "info_hash", "imdb_id", "uploaded", "updated_at", "created_at") SELECT "tracker", "torrent_id", "info_hash", "imdb_id", "uploaded", "updated_at", "created_at" FROM "temporary_web_torrent_runs"`,
    );

    await queryRunner.query(`DROP TABLE "temporary_web_torrent_runs"`);
    await queryRunner.query(`DROP INDEX "IDX_7869db61ed722d562da1acf6d5"`);
    // "trackers" visszaallitas "tracker_credentials"-re
    await queryRunner.query(
      `ALTER TABLE "trackers" RENAME TO "temporary_trackers"`,
    );
    await queryRunner.query(
      `CREATE TABLE "tracker_credentials" ("tracker" varchar CHECK( "tracker" IN ('ncore','bithumen','majomparade') ) PRIMARY KEY NOT NULL, "username" text NOT NULL, "password" text NOT NULL)`,
    );
    await queryRunner.query(
      `INSERT INTO "tracker_credentials"("tracker", "username", "password") SELECT "tracker", "username", "password" FROM "temporary_trackers"`,
    );
    await queryRunner.query(`DROP TABLE "temporary_trackers"`);

    // "users" visszaallitas (token, created_at, updated_at nelkul)
    await queryRunner.query(`ALTER TABLE "users" RENAME TO "temporary_users"`);
    await queryRunner.query(
      `CREATE TABLE "users" ("id" varchar PRIMARY KEY NOT NULL, "username" varchar NOT NULL, "password_hash" text, "user_role" varchar CHECK( "user_role" IN ('admin','user') ) NOT NULL, "torrent_resolutions" text NOT NULL DEFAULT ('["2160P","1080P","720P","576P","540P","480P"]'), "torrent_languages" text NOT NULL DEFAULT ('["hu","en"]'), "torrent_seed" integer, CONSTRAINT "UQ_fe0bb3f6520ee0469504521e710" UNIQUE ("username"))`,
    );
    await queryRunner.query(
      `INSERT INTO "users"("id", "username", "password_hash", "stremio_token", "user_role", "torrent_resolutions", "torrent_languages", "torrent_seed") SELECT "id", "username", "password_hash", "token", "user_role", "torrent_resolutions", "torrent_languages", "torrent_seed" FROM "temporary_users"`,
    );
    await queryRunner.query(`DROP TABLE "temporary_users"`);

    // "settings" visszaallitas (cache_retention visszahozasa)
    await queryRunner.query(
      `ALTER TABLE "settings" RENAME TO "temporary_settings"`,
    );
    await queryRunner.query(
      `CREATE TABLE "settings" ("id" text PRIMARY KEY NOT NULL, "enebled_local_ip" boolean NOT NULL DEFAULT (1), "upload_limit" integer NOT NULL DEFAULT (-1), "hit_and_run" boolean NOT NULL DEFAULT (0), "cache_retention" text, "address" text, "download_limit" integer NOT NULL DEFAULT (-1), "catalog_token" text)`,
    );
    await queryRunner.query(
      `INSERT INTO "settings"("id", "enebled_local_ip", "upload_limit", "hit_and_run", "address", "download_limit", "catalog_token") SELECT "id", "enebled_local_ip", "upload_limit", "hit_and_run", "address", "download_limit", "catalog_token" FROM "temporary_settings"`,
    );
    await queryRunner.query(`DROP TABLE "temporary_settings"`);

    // "users" visszaallitas (stremio_token)
    await queryRunner.query(`ALTER TABLE "users" RENAME TO "temporary_users"`);
    await queryRunner.query(
      `CREATE TABLE "users" ("id" varchar PRIMARY KEY NOT NULL, "username" varchar NOT NULL, "password_hash" text, "stremio_token" varchar NOT NULL, "user_role" varchar CHECK( "user_role" IN ('admin','user') ) NOT NULL, "torrent_resolutions" text NOT NULL DEFAULT ('["2160P","1080P","720P","576P","540P","480P"]'), "torrent_languages" text NOT NULL DEFAULT ('["hu","en"]'), "torrent_seed" integer, CONSTRAINT "UQ_fe0bb3f6520ee0469504521e710" UNIQUE ("username"))`,
    );
    await queryRunner.query(
      `INSERT INTO "users"("id", "username", "password_hash", "user_role", "torrent_resolutions", "torrent_languages", "torrent_seed") SELECT "id", "username", "password_hash", "user_role", "torrent_resolutions", "torrent_languages", "torrent_seed" FROM "temporary_users"`,
    );
    await queryRunner.query(`DROP TABLE "temporary_users"`);
    await queryRunner.query(
      `CREATE INDEX "IDX_37a561a6cfd07ed41e9f2d09d6" ON "users" ("stremio_token") `,
    );
  }
}
