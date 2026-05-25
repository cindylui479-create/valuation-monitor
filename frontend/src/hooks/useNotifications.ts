/**
 * SRS v1.3.0 H：浏览器原生通知 hook。
 *
 * 简化方案（不用 Service Worker）：
 *  - tab 打开时定时 poll `/api/v1/opportunities` + `/api/v1/tier-transitions`
 *  - 与上次比对，新增 HIGH 跳变 / 新增极度低估时弹 Notification
 *  - 不持久化历史；刷新页面会重置（避免反复打扰）
 *
 * 用户首次启用时浏览器会问"是否允许通知"，永久授权后不再问。
 */
import { useEffect, useRef, useState } from "react";
import { fetchOpportunities, fetchTierTransitions } from "@/api/opportunities";

const POLL_MS = 60_000;  // 60 秒（不要太频繁，避免烦人 + 节省 API）
const STORAGE_KEY = "valmon.notif.enabled";

interface NotifyState {
  enabled: boolean;
  permission: NotificationPermission;
  request: () => Promise<void>;
  toggle: () => void;
}

function _serialize_transitions(items: { entity_code: string; date: string; severity: string }[]): Set<string> {
  return new Set(items.filter((t) => t.severity === "HIGH").map((t) => `${t.entity_code}@${t.date}`));
}

function _serialize_low(items: { entity_code: string; tier: string }[]): Set<string> {
  return new Set(items.filter((t) => t.tier === "极度低估").map((t) => t.entity_code));
}

export function useNotifications(): NotifyState {
  const [permission, setPermission] = useState<NotificationPermission>(
    typeof Notification !== "undefined" ? Notification.permission : "default",
  );
  const [enabled, setEnabled] = useState<boolean>(() =>
    localStorage.getItem(STORAGE_KEY) === "1" && permission === "granted",
  );

  const seenTransitionsRef = useRef<Set<string>>(new Set());
  const seenLowRef = useRef<Set<string>>(new Set());
  const initializedRef = useRef(false);

  const request = async () => {
    if (typeof Notification === "undefined") return;
    const p = await Notification.requestPermission();
    setPermission(p);
    if (p === "granted") {
      setEnabled(true);
      localStorage.setItem(STORAGE_KEY, "1");
    }
  };

  const toggle = () => {
    if (!enabled && permission !== "granted") {
      void request();
      return;
    }
    const next = !enabled;
    setEnabled(next);
    localStorage.setItem(STORAGE_KEY, next ? "1" : "0");
  };

  useEffect(() => {
    if (!enabled || permission !== "granted") return;
    let stopped = false;

    const poll = async () => {
      try {
        const [opps, trans] = await Promise.all([
          fetchOpportunities(),
          fetchTierTransitions(7),
        ]);
        if (stopped) return;

        const newTransKeys = _serialize_transitions(trans.items);
        const newLowCodes = _serialize_low(opps.low_valuations);

        if (!initializedRef.current) {
          // 首次 poll 不弹：把当前状态作为基线
          seenTransitionsRef.current = newTransKeys;
          seenLowRef.current = newLowCodes;
          initializedRef.current = true;
          return;
        }

        // HIGH 跳变新增
        const newTrans = trans.items.filter(
          (t) => t.severity === "HIGH" && !seenTransitionsRef.current.has(`${t.entity_code}@${t.date}`),
        );
        for (const t of newTrans.slice(0, 3)) {
          new Notification(
            `档位跳变 · ${t.entity_name} (${t.entity_code})`,
            {
              body: `${t.from_tier ?? "—"} → ${t.to_tier} · 温度 ${t.direction === "up" ? "↑" : "↓"} ${t.temperature_delta}`,
              tag: `transition-${t.entity_code}-${t.date}`,
            },
          );
        }
        seenTransitionsRef.current = newTransKeys;

        // 极度低估新增
        const newLow = opps.low_valuations.filter(
          (o) => o.tier === "极度低估" && !seenLowRef.current.has(o.entity_code),
        );
        for (const o of newLow.slice(0, 3)) {
          new Notification(
            `极度低估 · ${o.entity_name} (${o.entity_code})`,
            {
              body: `温度 ${parseFloat(o.temperature).toFixed(1)} · ${o.entity_type}`,
              tag: `lowval-${o.entity_code}`,
            },
          );
        }
        seenLowRef.current = newLowCodes;
      } catch {
        // 静默忽略错误（避免反复弹）
      }
    };

    void poll();
    const id = window.setInterval(poll, POLL_MS);
    return () => {
      stopped = true;
      window.clearInterval(id);
    };
  }, [enabled, permission]);

  return { enabled, permission, request, toggle };
}
