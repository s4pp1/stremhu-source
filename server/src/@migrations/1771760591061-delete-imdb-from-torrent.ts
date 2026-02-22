import { MigrationInterface, QueryRunner } from 'typeorm';

export class DeleteImdbFromTorrent1771760591061 implements MigrationInterface {
  name = 'DeleteImdbFromTorrent1771760591061';

  public async up(queryRunner: QueryRunner): Promise<void> {
    await queryRunner.query(
      `CREATE TABLE "temporary_torrents" ("tracker" varchar CHECK( "tracker" IN ('ncore','bithumen','majomparade','insane') ) NOT NULL, "torrent_id" varchar NOT NULL, "info_hash" varchar PRIMARY KEY NOT NULL, "imdb_id" varchar NOT NULL, "uploaded" integer NOT NULL DEFAULT (0), "updated_at" datetime NOT NULL DEFAULT (datetime('now')), "created_at" datetime NOT NULL DEFAULT (datetime('now')), "is_persisted" boolean NOT NULL DEFAULT (0), "last_played_at" datetime NOT NULL, "full_download" boolean)`,
    );
    await queryRunner.query(
      `INSERT INTO "temporary_torrents"("tracker", "torrent_id", "info_hash", "imdb_id", "uploaded", "updated_at", "created_at", "is_persisted", "last_played_at", "full_download") SELECT "tracker", "torrent_id", "info_hash", "imdb_id", "uploaded", "updated_at", "created_at", "is_persisted", "last_played_at", "full_download" FROM "torrents"`,
    );
    await queryRunner.query(`DROP TABLE "torrents"`);
    await queryRunner.query(
      `ALTER TABLE "temporary_torrents" RENAME TO "torrents"`,
    );
    await queryRunner.query(
      `CREATE TABLE "temporary_torrents" ("tracker" varchar CHECK( "tracker" IN ('ncore','bithumen','majomparade','insane') ) NOT NULL, "torrent_id" varchar NOT NULL, "info_hash" varchar PRIMARY KEY NOT NULL, "uploaded" integer NOT NULL DEFAULT (0), "updated_at" datetime NOT NULL DEFAULT (datetime('now')), "created_at" datetime NOT NULL DEFAULT (datetime('now')), "is_persisted" boolean NOT NULL DEFAULT (0), "last_played_at" datetime NOT NULL, "full_download" boolean)`,
    );
    await queryRunner.query(
      `INSERT INTO "temporary_torrents"("tracker", "torrent_id", "info_hash", "uploaded", "updated_at", "created_at", "is_persisted", "last_played_at", "full_download") SELECT "tracker", "torrent_id", "info_hash", "uploaded", "updated_at", "created_at", "is_persisted", "last_played_at", "full_download" FROM "torrents"`,
    );
    await queryRunner.query(`DROP TABLE "torrents"`);
    await queryRunner.query(
      `ALTER TABLE "temporary_torrents" RENAME TO "torrents"`,
    );
    await queryRunner.query(
      `CREATE TABLE "temporary_torrents" ("tracker" varchar CHECK( "tracker" IN ('ncore','bithumen','majomparade','insane') ) NOT NULL, "torrent_id" varchar NOT NULL, "info_hash" varchar PRIMARY KEY NOT NULL, "uploaded" integer NOT NULL DEFAULT (0), "updated_at" datetime NOT NULL DEFAULT (datetime('now')), "created_at" datetime NOT NULL DEFAULT (datetime('now')), "is_persisted" boolean NOT NULL DEFAULT (0), "last_played_at" datetime NOT NULL, "full_download" boolean, CONSTRAINT "unique_torrent_tracker_torrent_id" UNIQUE ("tracker", "torrent_id"))`,
    );
    await queryRunner.query(
      `INSERT INTO "temporary_torrents"("tracker", "torrent_id", "info_hash", "uploaded", "updated_at", "created_at", "is_persisted", "last_played_at", "full_download") SELECT "tracker", "torrent_id", "info_hash", "uploaded", "updated_at", "created_at", "is_persisted", "last_played_at", "full_download" FROM "torrents"`,
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
      `CREATE TABLE "torrents" ("tracker" varchar CHECK( "tracker" IN ('ncore','bithumen','majomparade','insane') ) NOT NULL, "torrent_id" varchar NOT NULL, "info_hash" varchar PRIMARY KEY NOT NULL, "uploaded" integer NOT NULL DEFAULT (0), "updated_at" datetime NOT NULL DEFAULT (datetime('now')), "created_at" datetime NOT NULL DEFAULT (datetime('now')), "is_persisted" boolean NOT NULL DEFAULT (0), "last_played_at" datetime NOT NULL, "full_download" boolean)`,
    );
    await queryRunner.query(
      `INSERT INTO "torrents"("tracker", "torrent_id", "info_hash", "uploaded", "updated_at", "created_at", "is_persisted", "last_played_at", "full_download") SELECT "tracker", "torrent_id", "info_hash", "uploaded", "updated_at", "created_at", "is_persisted", "last_played_at", "full_download" FROM "temporary_torrents"`,
    );
    await queryRunner.query(`DROP TABLE "temporary_torrents"`);
    await queryRunner.query(
      `ALTER TABLE "torrents" RENAME TO "temporary_torrents"`,
    );
    await queryRunner.query(
      `CREATE TABLE "torrents" ("tracker" varchar CHECK( "tracker" IN ('ncore','bithumen','majomparade','insane') ) NOT NULL, "torrent_id" varchar NOT NULL, "info_hash" varchar PRIMARY KEY NOT NULL, "imdb_id" varchar NOT NULL, "uploaded" integer NOT NULL DEFAULT (0), "updated_at" datetime NOT NULL DEFAULT (datetime('now')), "created_at" datetime NOT NULL DEFAULT (datetime('now')), "is_persisted" boolean NOT NULL DEFAULT (0), "last_played_at" datetime NOT NULL, "full_download" boolean)`,
    );
    await queryRunner.query(
      `INSERT INTO "torrents"("tracker", "torrent_id", "info_hash", "uploaded", "updated_at", "created_at", "is_persisted", "last_played_at", "full_download") SELECT "tracker", "torrent_id", "info_hash", "uploaded", "updated_at", "created_at", "is_persisted", "last_played_at", "full_download" FROM "temporary_torrents"`,
    );
    await queryRunner.query(`DROP TABLE "temporary_torrents"`);
    await queryRunner.query(
      `ALTER TABLE "torrents" RENAME TO "temporary_torrents"`,
    );
    await queryRunner.query(
      `CREATE TABLE "torrents" ("tracker" varchar CHECK( "tracker" IN ('ncore','bithumen','majomparade','insane') ) NOT NULL, "torrent_id" varchar NOT NULL, "info_hash" varchar PRIMARY KEY NOT NULL, "imdb_id" varchar NOT NULL, "uploaded" integer NOT NULL DEFAULT (0), "updated_at" datetime NOT NULL DEFAULT (datetime('now')), "created_at" datetime NOT NULL DEFAULT (datetime('now')), "is_persisted" boolean NOT NULL DEFAULT (0), "last_played_at" datetime NOT NULL, "full_download" boolean, CONSTRAINT "unique_torrent_imdb_id_tracker_torrent_id" UNIQUE ("imdb_id", "tracker", "torrent_id"))`,
    );
    await queryRunner.query(
      `INSERT INTO "torrents"("tracker", "torrent_id", "info_hash", "imdb_id", "uploaded", "updated_at", "created_at", "is_persisted", "last_played_at", "full_download") SELECT "tracker", "torrent_id", "info_hash", "imdb_id", "uploaded", "updated_at", "created_at", "is_persisted", "last_played_at", "full_download" FROM "temporary_torrents"`,
    );
    await queryRunner.query(`DROP TABLE "temporary_torrents"`);
  }
}
