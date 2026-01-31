import { MigrationInterface, QueryRunner } from 'typeorm';

export class AudioCodecs1769892987562 implements MigrationInterface {
  name = 'AudioCodecs1769892987562';

  public async up(queryRunner: QueryRunner): Promise<void> {
    await queryRunner.query(`DROP INDEX "IDX_7869db61ed722d562da1acf6d5"`);
    await queryRunner.query(
      `CREATE TABLE "temporary_users" ("id" varchar PRIMARY KEY NOT NULL, "username" varchar NOT NULL, "password_hash" text, "user_role" varchar CHECK( "user_role" IN ('admin','user') ) NOT NULL, "torrent_resolutions" text NOT NULL DEFAULT ('["2160P","1080P","720P","576P","540P","480P"]'), "torrent_languages" text NOT NULL DEFAULT ('["hu","en"]'), "torrent_seed" integer, "token" varchar NOT NULL, "updated_at" datetime NOT NULL DEFAULT (datetime('now')), "created_at" datetime NOT NULL DEFAULT (datetime('now')), "torrent_video_qualities" text NOT NULL DEFAULT ('["dolby-vision","hdr10+","hdr10","hlg","sdr"]'), "only_best_torrent" boolean NOT NULL DEFAULT (0), "torrent_source_types" text NOT NULL DEFAULT ('["disc-remux","disc-rip","web-dl","web-rip","broadcast","theatrical","unknown"]'), "torrent_audio_codecs" text NOT NULL DEFAULT ('["truehd","dts-hd-ma","ddp","dts","dd","aac","unknown"]'), CONSTRAINT "UQ_fe0bb3f6520ee0469504521e710" UNIQUE ("username"))`,
    );
    await queryRunner.query(
      `INSERT INTO "temporary_users"("id", "username", "password_hash", "user_role", "torrent_resolutions", "torrent_languages", "torrent_seed", "token", "updated_at", "created_at", "torrent_video_qualities", "only_best_torrent", "torrent_source_types") SELECT "id", "username", "password_hash", "user_role", "torrent_resolutions", "torrent_languages", "torrent_seed", "token", "updated_at", "created_at", "torrent_video_qualities", "only_best_torrent", "torrent_source_types" FROM "users"`,
    );
    await queryRunner.query(`DROP TABLE "users"`);
    await queryRunner.query(`ALTER TABLE "temporary_users" RENAME TO "users"`);
    await queryRunner.query(
      `CREATE INDEX "IDX_7869db61ed722d562da1acf6d5" ON "users" ("token") `,
    );
  }

  public async down(queryRunner: QueryRunner): Promise<void> {
    await queryRunner.query(`DROP INDEX "IDX_7869db61ed722d562da1acf6d5"`);
    await queryRunner.query(`ALTER TABLE "users" RENAME TO "temporary_users"`);
    await queryRunner.query(
      `CREATE TABLE "users" ("id" varchar PRIMARY KEY NOT NULL, "username" varchar NOT NULL, "password_hash" text, "user_role" varchar CHECK( "user_role" IN ('admin','user') ) NOT NULL, "torrent_resolutions" text NOT NULL DEFAULT ('["2160P","1080P","720P","576P","540P","480P"]'), "torrent_languages" text NOT NULL DEFAULT ('["hu","en"]'), "torrent_seed" integer, "token" varchar NOT NULL, "updated_at" datetime NOT NULL DEFAULT (datetime('now')), "created_at" datetime NOT NULL DEFAULT (datetime('now')), "torrent_video_qualities" text NOT NULL DEFAULT ('["dolby-vision","hdr10+","hdr10","hlg","sdr"]'), "only_best_torrent" boolean NOT NULL DEFAULT (0), "torrent_source_types" text NOT NULL DEFAULT ('["disc-remux","disc-rip","web-dl","web-rip","broadcast","theatrical","unknown"]'), CONSTRAINT "UQ_fe0bb3f6520ee0469504521e710" UNIQUE ("username"))`,
    );
    await queryRunner.query(
      `INSERT INTO "users"("id", "username", "password_hash", "user_role", "torrent_resolutions", "torrent_languages", "torrent_seed", "token", "updated_at", "created_at", "torrent_video_qualities", "only_best_torrent", "torrent_source_types") SELECT "id", "username", "password_hash", "user_role", "torrent_resolutions", "torrent_languages", "torrent_seed", "token", "updated_at", "created_at", "torrent_video_qualities", "only_best_torrent", "torrent_source_types" FROM "temporary_users"`,
    );
    await queryRunner.query(`DROP TABLE "temporary_users"`);
    await queryRunner.query(
      `CREATE INDEX "IDX_7869db61ed722d562da1acf6d5" ON "users" ("token") `,
    );
  }
}
