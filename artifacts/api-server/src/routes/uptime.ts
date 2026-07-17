/**
 * POST /api/alert/uptime
 *
 * Receives a webhook call from an external uptime monitor (UptimeRobot,
 * BetterUptime, etc.) when the bot health endpoint stops responding, then
 * forwards a Discord embed to the configured alert channel via a Discord
 * Incoming Webhook URL.
 *
 * Because this handler runs in the API Server — a separate process from the
 * Discord bot — it stays reachable even when the bot itself has crashed.
 *
 * Required environment variable:
 *   DISCORD_ALERT_WEBHOOK_URL  — Discord Incoming Webhook URL for the alert channel
 *
 * Optional environment variable:
 *   UPTIME_WEBHOOK_SECRET      — If set, requests must include the header
 *                                X-Webhook-Secret: <value>; others get HTTP 401.
 *
 * Payload (JSON body, all fields optional):
 *   alert_type   "down" | "up" | "recovery" (defaults to "down")
 *   monitor_name Friendly name shown in the embed
 *   monitor_url  URL being monitored
 *   details      Additional context shown in the embed
 *
 * UptimeRobot native keys (alertType, alertTypeFriendlyName, monitorURL,
 * monitorFriendlyName, alertDetails) are also accepted automatically.
 */

import { Router, type IRouter, type Request, type Response } from "express";
import { logger } from "../lib/logger";

const router: IRouter = Router();

// ---------------------------------------------------------------------------
// Discord Embed colours
// ---------------------------------------------------------------------------
const COLOR_RED = 0xe74c3c;
const COLOR_GREEN = 0x2ecc71;

// ---------------------------------------------------------------------------
// Helper: post an embed to a Discord Incoming Webhook URL
// ---------------------------------------------------------------------------
async function sendDiscordEmbed(
  webhookUrl: string,
  embed: Record<string, unknown>,
): Promise<void> {
  const res = await fetch(webhookUrl, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ embeds: [embed] }),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`Discord webhook responded ${res.status}: ${text}`);
  }
}

// ---------------------------------------------------------------------------
// POST /api/alert/uptime
// ---------------------------------------------------------------------------
router.post("/alert/uptime", async (req: Request, res: Response) => {
  // --- Optional secret validation ------------------------------------------
  const expectedSecret = process.env["UPTIME_WEBHOOK_SECRET"] ?? "";
  if (expectedSecret) {
    const provided = req.headers["x-webhook-secret"] ?? "";
    if (provided !== expectedSecret) {
      logger.warn("Uptime webhook: invalid or missing X-Webhook-Secret");
      res.status(401).json({ ok: false, error: "Unauthorized" });
      return;
    }
  }

  // --- Parse body (best-effort) -------------------------------------------
  const body: Record<string, unknown> =
    req.body && typeof req.body === "object" ? req.body : {};

  // Normalise keys — accept both our generic format and UptimeRobot's format.
  const rawAlertType =
    (body["alert_type"] as string | undefined) ??
    (body["alertTypeFriendlyName"] as string | undefined) ??
    (String(body["alertType"] ?? "1") === "1" ? "down" : "up");

  const alertType = rawAlertType.toLowerCase();
  const monitorName =
    (body["monitor_name"] as string | undefined) ??
    (body["monitorFriendlyName"] as string | undefined) ??
    "Bot health endpoint";
  const monitorUrl =
    (body["monitor_url"] as string | undefined) ??
    (body["monitorURL"] as string | undefined) ??
    "";
  const details =
    (body["details"] as string | undefined) ??
    (body["alertDetails"] as string | undefined) ??
    "";

  logger.info(
    { alertType, monitorName, monitorUrl },
    "Uptime webhook received",
  );

  // --- Check required config -----------------------------------------------
  const webhookUrl = process.env["DISCORD_ALERT_WEBHOOK_URL"];
  if (!webhookUrl) {
    logger.warn(
      "DISCORD_ALERT_WEBHOOK_URL not set — uptime webhook received but cannot forward to Discord",
    );
    res.json({ ok: true, forwarded: false, reason: "DISCORD_ALERT_WEBHOOK_URL not configured" });
    return;
  }

  // --- Build embed ---------------------------------------------------------
  const isDown =
    alertType.includes("down") ||
    !["up", "recovery", "recovered"].includes(alertType);

  const now = new Date().toISOString();

  const fields: Array<{ name: string; value: string; inline?: boolean }> = [];
  if (monitorUrl) {
    fields.push({ name: "URL ที่ตรวจสอบ", value: monitorUrl, inline: false });
  }
  if (details) {
    fields.push({ name: "รายละเอียด", value: details.slice(0, 1024), inline: false });
  }
  fields.push({ name: "แหล่งที่มา", value: "External uptime monitor → API Server webhook", inline: true });

  const embed: Record<string, unknown> = {
    title: isDown
      ? "🔴 บอทออฟไลน์ (ตรวจพบโดย Uptime Monitor)"
      : "🟢 บอทกลับมาออนไลน์ (ยืนยันโดย Uptime Monitor)",
    description: isDown
      ? `Uptime monitor รายงานว่า **${monitorName}** ไม่สามารถเข้าถึงได้\nบอทอาจขัดข้องหรือกำลังรีสตาร์ท`
      : `Uptime monitor ยืนยันว่า **${monitorName}** กลับมาตอบสนองแล้ว`,
    color: isDown ? COLOR_RED : COLOR_GREEN,
    timestamp: now,
    fields,
    footer: { text: "Style-Bot Uptime Alerts" },
  };

  // --- Forward to Discord --------------------------------------------------
  try {
    await sendDiscordEmbed(webhookUrl, embed);
    logger.info({ isDown, monitorName }, "Uptime alert forwarded to Discord");
    res.json({ ok: true, forwarded: true });
  } catch (err) {
    logger.error({ err }, "Failed to forward uptime alert to Discord");
    res.status(500).json({ ok: false, error: "Failed to send Discord embed" });
  }
});

export default router;
