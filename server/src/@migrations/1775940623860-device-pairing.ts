import { MigrationInterface, QueryRunner } from 'typeorm';

export class DevicePairing1775940623860 implements MigrationInterface {
  name = 'DevicePairing1775940623860';

  public async up(queryRunner: QueryRunner): Promise<void> {
    await queryRunner.query(
      `CREATE TABLE "pairings" (
        "id" varchar PRIMARY KEY NOT NULL,
        "user_code" text NOT NULL,
        "device_code" varchar NOT NULL,
        "status" varchar CHECK( "status" IN ('pending','linked','expired') ) NOT NULL DEFAULT ('pending'),
        "user_id" varchar,
        "expires_at" datetime NOT NULL,
        "created_at" datetime NOT NULL DEFAULT (datetime('now')),
        CONSTRAINT "FK_d1ca9fdbdc00362b98cc3f91b80" FOREIGN KEY ("user_id") REFERENCES "users" ("id") ON DELETE CASCADE ON UPDATE NO ACTION
      )`,
    );
    await queryRunner.query(
      `CREATE INDEX "IDX_8d754f5855c4ecf9f6894771cb" ON "pairings" ("user_code")`,
    );
    await queryRunner.query(
      `CREATE INDEX "IDX_a1b742199816b28b3fd4c09c45" ON "pairings" ("device_code")`,
    );
  }

  public async down(queryRunner: QueryRunner): Promise<void> {
    await queryRunner.query(`DROP INDEX "IDX_a1b742199816b28b3fd4c09c45"`);
    await queryRunner.query(`DROP INDEX "IDX_8d754f5855c4ecf9f6894771cb"`);
    await queryRunner.query(`DROP TABLE "pairings"`);
  }
}
