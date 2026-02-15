import { MigrationInterface, QueryRunner } from 'typeorm';

export class UserPreferences1771077178005 implements MigrationInterface {
  name = 'UserPreferences1771077178005';

  public async up(queryRunner: QueryRunner): Promise<void> {
    await queryRunner.query(
      `CREATE TABLE "user_preferences" ("preference" text NOT NULL, "user_id" varchar NOT NULL, "preferred" text NOT NULL, "blocked" text NOT NULL, "order" integer, PRIMARY KEY ("preference", "user_id"))`,
    );
    await queryRunner.query(`DROP INDEX "IDX_7869db61ed722d562da1acf6d5"`);
    await queryRunner.query(
      `CREATE TABLE "temporary_users" ("id" varchar PRIMARY KEY NOT NULL, "username" varchar NOT NULL, "password_hash" text, "user_role" varchar CHECK( "user_role" IN ('admin','user') ) NOT NULL, "torrent_seed" integer, "token" varchar NOT NULL, "updated_at" datetime NOT NULL DEFAULT (datetime('now')), "created_at" datetime NOT NULL DEFAULT (datetime('now')), "only_best_torrent" boolean NOT NULL DEFAULT (0), CONSTRAINT "UQ_fe0bb3f6520ee0469504521e710" UNIQUE ("username"))`,
    );
    await queryRunner.query(
      `INSERT INTO "temporary_users"("id", "username", "password_hash", "user_role", "torrent_seed", "token", "updated_at", "created_at", "only_best_torrent") SELECT "id", "username", "password_hash", "user_role", "torrent_seed", "token", "updated_at", "created_at", "only_best_torrent" FROM "users"`,
    );
    await queryRunner.query(`DROP TABLE "users"`);
    await queryRunner.query(`ALTER TABLE "temporary_users" RENAME TO "users"`);
    await queryRunner.query(
      `CREATE INDEX "IDX_7869db61ed722d562da1acf6d5" ON "users" ("token") `,
    );
    await queryRunner.query(
      `CREATE TABLE "temporary_user_preferences" ("preference" text NOT NULL, "user_id" varchar NOT NULL, "preferred" text NOT NULL, "blocked" text NOT NULL, "order" integer, CONSTRAINT "FK_458057fa75b66e68a275647da2e" FOREIGN KEY ("user_id") REFERENCES "users" ("id") ON DELETE CASCADE ON UPDATE NO ACTION, PRIMARY KEY ("preference", "user_id"))`,
    );
    await queryRunner.query(
      `INSERT INTO "temporary_user_preferences"("preference", "user_id", "preferred", "blocked", "order") SELECT "preference", "user_id", "preferred", "blocked", "order" FROM "user_preferences"`,
    );
    await queryRunner.query(`DROP TABLE "user_preferences"`);
    await queryRunner.query(
      `ALTER TABLE "temporary_user_preferences" RENAME TO "user_preferences"`,
    );
  }

  public async down(queryRunner: QueryRunner): Promise<void> {
    await queryRunner.query(
      `ALTER TABLE "user_preferences" RENAME TO "temporary_user_preferences"`,
    );
    await queryRunner.query(
      `CREATE TABLE "user_preferences" ("preference" text NOT NULL, "user_id" varchar NOT NULL, "preferred" text NOT NULL, "blocked" text NOT NULL, "order" integer, PRIMARY KEY ("preference", "user_id"))`,
    );
    await queryRunner.query(
      `INSERT INTO "user_preferences"("preference", "user_id", "preferred", "blocked", "order") SELECT "preference", "user_id", "preferred", "blocked", "order" FROM "temporary_user_preferences"`,
    );
    await queryRunner.query(`DROP TABLE "temporary_user_preferences"`);
    await queryRunner.query(`DROP INDEX "IDX_7869db61ed722d562da1acf6d5"`);
    await queryRunner.query(`ALTER TABLE "users" RENAME TO "temporary_users"`);
    await queryRunner.query(
      `CREATE TABLE "users" ("id" varchar PRIMARY KEY NOT NULL, "username" varchar NOT NULL, "password_hash" text, "user_role" varchar CHECK( "user_role" IN ('admin','user') ) NOT NULL, "torrent_resolutions" text NOT NULL DEFAULT ('["2160P","1080P","720P","576P","540P","480P"]'), "torrent_languages" text NOT NULL DEFAULT ('["hu","en"]'), "torrent_seed" integer, "token" varchar NOT NULL, "updated_at" datetime NOT NULL DEFAULT (datetime('now')), "created_at" datetime NOT NULL DEFAULT (datetime('now')), "torrent_video_qualities" text NOT NULL DEFAULT ('["dolby-vision","hdr10+","hdr10","hlg","sdr"]'), "only_best_torrent" boolean NOT NULL DEFAULT (0), "torrent_source_types" text NOT NULL DEFAULT ('["disc-remux","disc-rip","web-dl","web-rip","broadcast","theatrical","unknown"]'), "torrent_audio_codecs" text NOT NULL DEFAULT ('["truehd","dts-hd-ma","ddp","dts","dd","aac","unknown"]'), CONSTRAINT "UQ_fe0bb3f6520ee0469504521e710" UNIQUE ("username"))`,
    );
    await queryRunner.query(
      `INSERT INTO "users"("id", "username", "password_hash", "user_role", "torrent_seed", "token", "updated_at", "created_at", "only_best_torrent") SELECT "id", "username", "password_hash", "user_role", "torrent_seed", "token", "updated_at", "created_at", "only_best_torrent" FROM "temporary_users"`,
    );
    await queryRunner.query(`DROP TABLE "temporary_users"`);
    await queryRunner.query(
      `CREATE INDEX "IDX_7869db61ed722d562da1acf6d5" ON "users" ("token") `,
    );
    await queryRunner.query(`DROP TABLE "user_preferences"`);
  }
}
