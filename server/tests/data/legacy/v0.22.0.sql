-- StremHU Source v0.22.0: empty database schema, produced by replaying the SQL of
-- every TypeORM migration of the v0.22.0 git tag. Last migration: FilelistTracker1776000000000
CREATE TABLE "migrations" ("id" integer PRIMARY KEY AUTOINCREMENT NOT NULL, "timestamp" bigint NOT NULL, "name" varchar NOT NULL);
INSERT INTO "migrations" VALUES(1,1762598798738,'InitSchema1762598798738');
INSERT INTO "migrations" VALUES(2,1762636792261,'BithumenCred1762636792261');
INSERT INTO "migrations" VALUES(3,1762889799992,'MajomparedeCred1762889799992');
INSERT INTO "migrations" VALUES(4,1763657893263,'CatalogToken1763657893263');
INSERT INTO "migrations" VALUES(5,1763766443923,'DownloadLimit1763766443923');
INSERT INTO "migrations" VALUES(6,1764367521545,'AddressRefactor1764367521545');
INSERT INTO "migrations" VALUES(7,1765482192206,'WebTorrentRunDates1765482192206');
INSERT INTO "migrations" VALUES(8,1766131196717,'DbRefactor1766131196717');
INSERT INTO "migrations" VALUES(9,1766767970910,'OnlyBestTorrent1766767970910');
INSERT INTO "migrations" VALUES(10,1766865562826,'TorrentSourceType1766865562826');
INSERT INTO "migrations" VALUES(11,1768251172677,'SettingsStructureRefactor1768251172677');
INSERT INTO "migrations" VALUES(12,1769360214276,'InsaneIntegralasa1769360214276');
INSERT INTO "migrations" VALUES(13,1769892987562,'AudioCodecs1769892987562');
INSERT INTO "migrations" VALUES(14,1769948887547,'TorrentFullDownload1769948887547');
INSERT INTO "migrations" VALUES(15,1771077178005,'UserPreferences1771077178005');
INSERT INTO "migrations" VALUES(16,1771760591061,'DeleteImdbFromTorrent1771760591061');
INSERT INTO "migrations" VALUES(17,1774800518975,'UploadRemoveFromTorrents1774800518975');
INSERT INTO "migrations" VALUES(18,1775940623860,'DevicePairing1775940623860');
INSERT INTO "migrations" VALUES(19,1776000000000,'FilelistTracker1776000000000');
CREATE TABLE "pairings" (
        "id" varchar PRIMARY KEY NOT NULL,
        "user_code" text NOT NULL,
        "device_code" varchar NOT NULL,
        "status" varchar CHECK( "status" IN ('pending','linked','expired') ) NOT NULL DEFAULT ('pending'),
        "user_id" varchar,
        "expires_at" datetime NOT NULL,
        "created_at" datetime NOT NULL DEFAULT (datetime('now')),
        CONSTRAINT "FK_d1ca9fdbdc00362b98cc3f91b80" FOREIGN KEY ("user_id") REFERENCES "users" ("id") ON DELETE CASCADE ON UPDATE NO ACTION
      );
CREATE TABLE "sessions" ("sid" text PRIMARY KEY NOT NULL, "data" text NOT NULL, "expires" integer NOT NULL);
CREATE TABLE "settings" ("key" text PRIMARY KEY NOT NULL, "value" text NOT NULL DEFAULT ('{}'));
CREATE TABLE "torrents" ("tracker" varchar CHECK( "tracker" IN ('ncore','bithumen','majomparade','insane','filelist') ) NOT NULL, "torrent_id" varchar NOT NULL, "info_hash" varchar PRIMARY KEY NOT NULL, "updated_at" datetime NOT NULL DEFAULT (datetime('now')), "created_at" datetime NOT NULL DEFAULT (datetime('now')), "is_persisted" boolean NOT NULL DEFAULT (0), "last_played_at" datetime NOT NULL, "full_download" boolean, CONSTRAINT "unique_torrent_tracker_torrent_id" UNIQUE ("tracker", "torrent_id"));
CREATE TABLE "trackers" ("tracker" varchar CHECK( "tracker" IN ('ncore','bithumen','majomparade','insane','filelist') ) PRIMARY KEY NOT NULL, "username" text NOT NULL, "password" text NOT NULL, "hit_and_run" boolean, "keep_seed_seconds" integer, "download_full_torrent" boolean NOT NULL DEFAULT (0), "order_index" integer NOT NULL DEFAULT (0), "updated_at" datetime NOT NULL DEFAULT (datetime('now')), "created_at" datetime NOT NULL DEFAULT (datetime('now')));
CREATE TABLE "user_preferences" ("preference" text NOT NULL, "user_id" varchar NOT NULL, "preferred" text NOT NULL, "blocked" text NOT NULL, "order" integer, CONSTRAINT "FK_458057fa75b66e68a275647da2e" FOREIGN KEY ("user_id") REFERENCES "users" ("id") ON DELETE CASCADE ON UPDATE NO ACTION, PRIMARY KEY ("preference", "user_id"));
CREATE TABLE "users" ("id" varchar PRIMARY KEY NOT NULL, "username" varchar NOT NULL, "password_hash" text, "user_role" varchar CHECK( "user_role" IN ('admin','user') ) NOT NULL, "torrent_seed" integer, "token" varchar NOT NULL, "updated_at" datetime NOT NULL DEFAULT (datetime('now')), "created_at" datetime NOT NULL DEFAULT (datetime('now')), "only_best_torrent" boolean NOT NULL DEFAULT (0), CONSTRAINT "UQ_fe0bb3f6520ee0469504521e710" UNIQUE ("username"));
CREATE INDEX "IDX_b7b5a67d8378ee0fce99a4a191" ON "sessions" ("expires") ;
CREATE INDEX "IDX_7869db61ed722d562da1acf6d5" ON "users" ("token") ;
CREATE INDEX "IDX_8d754f5855c4ecf9f6894771cb" ON "pairings" ("user_code");
CREATE INDEX "IDX_a1b742199816b28b3fd4c09c45" ON "pairings" ("device_code");
DELETE FROM "sqlite_sequence";
INSERT INTO "sqlite_sequence" VALUES('migrations',19);
