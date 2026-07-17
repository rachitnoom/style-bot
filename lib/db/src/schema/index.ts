// Export your models here. Add one export per file
// export * from "./posts";
//
// Each model/table should ideally be split into different files.
// Each model/table should define a Drizzle table, insert schema, and types:
//
//   import { pgTable, text, serial } from "drizzle-orm/pg-core";
//   import { createInsertSchema } from "drizzle-zod";
//   import { z } from "zod/v4";
//
//   export const postsTable = pgTable("posts", {
//     id: serial("id").primaryKey(),
//     title: text("title").notNull(),
//   });
//
//   export const insertPostSchema = createInsertSchema(postsTable).omit({ id: true });
//   export type InsertPost = z.infer<typeof insertPostSchema>;
//   export type Post = typeof postsTable.$inferSelect;

import {
  pgTable,
  bigint,
  text,
  timestamp,
  index,
  pgEnum,
  primaryKey,
} from "drizzle-orm/pg-core";
import { createSelectSchema } from "drizzle-zod";
import { z } from "zod/v4";

// ---------------------------------------------------------------------------
// presence_status enum
// ---------------------------------------------------------------------------
export const presenceStatusEnum = pgEnum("presence_status", [
  "online",
  "idle",
  "dnd",
  "offline",
]);

// ---------------------------------------------------------------------------
// presence_events — append-only log of every status change
// ---------------------------------------------------------------------------
export const presenceEventsTable = pgTable(
  "presence_events",
  {
    id: bigint("id", { mode: "bigint" })
      .generatedAlwaysAsIdentity()
      .primaryKey(),
    guildId: bigint("guild_id", { mode: "bigint" }).notNull(),
    userId: bigint("user_id", { mode: "bigint" }).notNull(),
    username: text("username").notNull(),
    status: presenceStatusEnum("status").notNull(),
    recordedAt: timestamp("recorded_at", { withTimezone: true })
      .notNull()
      .defaultNow(),
  },
  (t) => [
    index("presence_events_guild_user_idx").on(t.guildId, t.userId),
    index("presence_events_recorded_at_idx").on(t.recordedAt),
  ],
);

export const selectPresenceEventSchema = createSelectSchema(presenceEventsTable);

export type PresenceEvent = typeof presenceEventsTable.$inferSelect;

// ---------------------------------------------------------------------------
// member_current_status — one row per (guild, user); updated on every event
// ---------------------------------------------------------------------------
export const memberCurrentStatusTable = pgTable(
  "member_current_status",
  {
    guildId: bigint("guild_id", { mode: "bigint" }).notNull(),
    userId: bigint("user_id", { mode: "bigint" }).notNull(),
    username: text("username").notNull(),
    status: presenceStatusEnum("status").notNull(),
    updatedAt: timestamp("updated_at", { withTimezone: true })
      .notNull()
      .defaultNow(),
  },
  (t) => [
    primaryKey({ columns: [t.guildId, t.userId], name: "member_current_status_pk" }),
  ],
);

export const selectMemberCurrentStatusSchema = createSelectSchema(
  memberCurrentStatusTable,
);
export type MemberCurrentStatus = typeof memberCurrentStatusTable.$inferSelect;