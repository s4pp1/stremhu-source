import { MigrationInterface, QueryRunner } from 'typeorm';

export class OnlyBestTorrent1766767970910 implements MigrationInterface {
  name = 'OnlyBestTorrent1766767970910';

  public async up(queryRunner: QueryRunner): Promise<void> {
    await queryRunner.query(`DROP INDEX "IDX_7869db61ed722d562da1acf6d5"`);
    await queryRunner.query(
      `CREATE TABLE "temporary_users" ("id" varchar PRIMARY KEY NOT NULL, "username" varchar NOT NULL, "password_hash" text, "user_role" varchar CHECK( "user_role" IN ('admin','user') ) NOT NULL, "torrent_resolutions" text NOT NULL DEFAULT ('["2160P","1080P","720P","576P","540P","480P"]'), "torrent_languages" text NOT NULL DEFAULT ('["hu","en"]'), "torrent_seed" integer, "token" varchar NOT NULL, "updated_at" datetime NOT NULL DEFAULT (datetime('now')), "created_at" datetime NOT NULL DEFAULT (datetime('now')), "torrent_video_qualities" text NOT NULL DEFAULT ('["dolby-vision","hdr10+","hdr10","hlg","sdr"]'), "only_best_torrent" boolean NOT NULL DEFAULT (0), CONSTRAINT "UQ_fe0bb3f6520ee0469504521e710" UNIQUE ("username"))`,
    );
    await queryRunner.query(
      `INSERT INTO "temporary_users"("id", "username", "password_hash", "user_role", "torrent_resolutions", "torrent_languages", "torrent_seed", "token", "updated_at", "created_at") SELECT "id", "username", "password_hash", "user_role", "torrent_resolutions", "torrent_languages", "torrent_seed", "token", "updated_at", "created_at" FROM "users"`,
    );
    await queryRunner.query(`DROP TABLE "users"`);
    await queryRunner.query(`ALTER TABLE "temporary_users" RENAME TO "users"`);
    await queryRunner.query(
      `CREATE INDEX "IDX_7869db61ed722d562da1acf6d5" ON "users" ("token") `,
    );
    await queryRunner.query(
      `CREATE TABLE "temporary_torrents" ("tracker" varchar CHECK( "tracker" IN ('ncore','bithumen','majomparade') ) NOT NULL, "torrent_id" varchar NOT NULL, "info_hash" varchar PRIMARY KEY NOT NULL, "imdb_id" varchar NOT NULL, "uploaded" integer NOT NULL DEFAULT (0), "updated_at" datetime NOT NULL DEFAULT (datetime('now')), "created_at" datetime NOT NULL DEFAULT (datetime('now')), "is_persisted" boolean NOT NULL DEFAULT (0), "last_played_at" datetime NOT NULL, CONSTRAINT "unique_torrent_imdb_id_tracker_torrent_id" UNIQUE ("imdb_id", "tracker", "torrent_id"))`,
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
      `CREATE TABLE "torrents" ("tracker" varchar CHECK( "tracker" IN ('ncore','bithumen','majomparade') ) NOT NULL, "torrent_id" varchar NOT NULL, "info_hash" varchar PRIMARY KEY NOT NULL, "imdb_id" varchar NOT NULL, "uploaded" integer NOT NULL DEFAULT (0), "updated_at" datetime NOT NULL DEFAULT (datetime('now')), "created_at" datetime NOT NULL DEFAULT (datetime('now')), "is_persisted" boolean NOT NULL DEFAULT (0), "last_played_at" datetime NOT NULL DEFAULT (datetime('now')), CONSTRAINT "unique_torrent_imdb_id_tracker_torrent_id" UNIQUE ("imdb_id", "tracker", "torrent_id"))`,
    );
    await queryRunner.query(
      `INSERT INTO "torrents"("tracker", "torrent_id", "info_hash", "imdb_id", "uploaded", "updated_at", "created_at", "is_persisted", "last_played_at") SELECT "tracker", "torrent_id", "info_hash", "imdb_id", "uploaded", "updated_at", "created_at", "is_persisted", "last_played_at" FROM "temporary_torrents"`,
    );
    await queryRunner.query(`DROP TABLE "temporary_torrents"`);
    await queryRunner.query(`DROP INDEX "IDX_7869db61ed722d562da1acf6d5"`);
    await queryRunner.query(`ALTER TABLE "users" RENAME TO "temporary_users"`);
    await queryRunner.query(
      `CREATE TABLE "users" ("id" varchar PRIMARY KEY NOT NULL, "username" varchar NOT NULL, "password_hash" text, "user_role" varchar CHECK( "user_role" IN ('admin','user') ) NOT NULL, "torrent_resolutions" text NOT NULL DEFAULT ('["2160P","1080P","720P","576P","540P","480P"]'), "torrent_languages" text NOT NULL DEFAULT ('["hu","en"]'), "torrent_seed" integer, "token" varchar NOT NULL, "updated_at" datetime NOT NULL DEFAULT (datetime('now')), "created_at" datetime NOT NULL DEFAULT (datetime('now')), CONSTRAINT "UQ_fe0bb3f6520ee0469504521e710" UNIQUE ("username"))`,
    );
    await queryRunner.query(
      `INSERT INTO "users"("id", "username", "password_hash", "user_role", "torrent_resolutions", "torrent_languages", "torrent_seed", "token", "updated_at", "created_at") SELECT "id", "username", "password_hash", "user_role", "torrent_resolutions", "torrent_languages", "torrent_seed", "token", "updated_at", "created_at" FROM "temporary_users"`,
    );
    await queryRunner.query(`DROP TABLE "temporary_users"`);
    await queryRunner.query(
      `CREATE INDEX "IDX_7869db61ed722d562da1acf6d5" ON "users" ("token") `,
    );
  }
}
