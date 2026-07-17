import { Router, type IRouter, type Request, type Response } from "express";
import { db } from "@workspace/db";
import {
  presenceEventsTable,
  memberCurrentStatusTable,
} from "@workspace/db/schema";
import { eq, and, desc, sql } from "drizzle-orm";

const router: IRouter = Router();

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function isSnowflake(s: unknown): s is string {
  return typeof s === "string" && /^\d+$/.test(s);
}

function parsePagination(query: Request["query"]): { limit: number; offset: number } | null {
  const limit = query["limit"] !== undefined ? Number(query["limit"]) : 100;
  const offset = query["offset"] !== undefined ? Number(query["offset"]) : 0;
  if (!Number.isInteger(limit) || limit < 1 || limit > 500) return null;
  if (!Number.isInteger(offset) || offset < 0) return null;
  return { limit, offset };
}

// ---------------------------------------------------------------------------
// GET /api/presence/:guildId/current
// Returns the current status snapshot for every tracked member in a guild.
// ---------------------------------------------------------------------------
router.get(
  "/presence/:guildId/current",
  async (req: Request, res: Response) => {
    const { guildId } = req.params as { guildId: string };
    if (!isSnowflake(guildId)) {
      res.status(400).json({ error: "guildId must be a numeric snowflake" });
      return;
    }

    const rows = await db
      .select()
      .from(memberCurrentStatusTable)
      .where(eq(memberCurrentStatusTable.guildId, BigInt(guildId)))
      .orderBy(memberCurrentStatusTable.username);

    res.json(rows.map(serializeStatus));
  },
);

// ---------------------------------------------------------------------------
// GET /api/presence/:guildId/events
// Returns paginated presence event history for a guild.
// Optional query param: userId
// ---------------------------------------------------------------------------
router.get(
  "/presence/:guildId/events",
  async (req: Request, res: Response) => {
    const { guildId } = req.params as { guildId: string };
    if (!isSnowflake(guildId)) {
      res.status(400).json({ error: "guildId must be a numeric snowflake" });
      return;
    }

    const pagination = parsePagination(req.query);
    if (!pagination) {
      res.status(400).json({ error: "limit must be 1-500, offset must be >= 0" });
      return;
    }
    const { limit, offset } = pagination;

    const userIdRaw = req.query["userId"];
    if (userIdRaw !== undefined && !isSnowflake(userIdRaw)) {
      res.status(400).json({ error: "userId must be a numeric snowflake" });
      return;
    }

    const whereClause =
      userIdRaw !== undefined
        ? and(
            eq(presenceEventsTable.guildId, BigInt(guildId)),
            eq(presenceEventsTable.userId, BigInt(userIdRaw as string)),
          )
        : eq(presenceEventsTable.guildId, BigInt(guildId));

    const rows = await db
      .select()
      .from(presenceEventsTable)
      .where(whereClause)
      .orderBy(desc(presenceEventsTable.recordedAt))
      .limit(limit)
      .offset(offset);

    res.json(rows.map(serializeEvent));
  },
);

// ---------------------------------------------------------------------------
// GET /api/presence/:guildId/summary
// Returns counts of online/idle/dnd/offline members from current snapshots.
// ---------------------------------------------------------------------------
router.get(
  "/presence/:guildId/summary",
  async (req: Request, res: Response) => {
    const { guildId } = req.params as { guildId: string };
    if (!isSnowflake(guildId)) {
      res.status(400).json({ error: "guildId must be a numeric snowflake" });
      return;
    }

    const rows = await db
      .select({
        status: memberCurrentStatusTable.status,
        count: sql<number>`cast(count(*) as int)`,
      })
      .from(memberCurrentStatusTable)
      .where(eq(memberCurrentStatusTable.guildId, BigInt(guildId)))
      .groupBy(memberCurrentStatusTable.status);

    const summary: Record<string, number> = {
      online: 0,
      idle: 0,
      dnd: 0,
      offline: 0,
    };

    for (const row of rows) {
      summary[row.status] = row.count;
    }

    res.json(summary);
  },
);

// ---------------------------------------------------------------------------
// Serialisers — convert BigInt fields to strings for JSON safety
// ---------------------------------------------------------------------------

function serializeEvent(row: typeof presenceEventsTable.$inferSelect) {
  return {
    id: String(row.id),
    guildId: String(row.guildId),
    userId: String(row.userId),
    username: row.username,
    status: row.status,
    recordedAt: row.recordedAt,
  };
}

function serializeStatus(row: typeof memberCurrentStatusTable.$inferSelect) {
  return {
    guildId: String(row.guildId),
    userId: String(row.userId),
    username: row.username,
    status: row.status,
    updatedAt: row.updatedAt,
  };
}

export default router;
