import { useEffect, useState } from "react";
import { AlertTriangle, Info, XCircle, CheckCircle, X } from "lucide-react";

interface Notice {
  id: string;
  type: "info" | "warning" | "error" | "success";
  title: string;
  message?: string;
  active: boolean;
  expires?: string;
}

const ICONS = {
  info:    Info,
  warning: AlertTriangle,
  error:   XCircle,
  success: CheckCircle,
} as const;

function noticeIsActive(n: Notice): boolean {
  if (!n.active) return false;
  if (n.expires && new Date(n.expires) < new Date()) return false;
  return true;
}

export function SystemNotices() {
  const [notices, setNotices] = useState<Notice[]>([]);
  const [dismissed, setDismissed] = useState<Set<string>>(new Set());

  useEffect(() => {
    fetch("/notices.json")
      .then((r) => (r.ok ? r.json() : []))
      .then((data: Notice[]) => setNotices(data))
      .catch(() => {});
  }, []);

  const visible = notices.filter((n) => noticeIsActive(n) && !dismissed.has(n.id));
  if (visible.length === 0) return null;

  function dismiss(id: string) {
    setDismissed((prev) => new Set(prev).add(id));
  }

  return (
    <div className="notices" role="region" aria-label="System notices">
      {visible.map((notice) => {
        const Icon = ICONS[notice.type];
        return (
          <div
            key={notice.id}
            className={`notice notice--${notice.type}`}
            role="alert"
            aria-live="polite"
          >
            <Icon size={16} className="notice__icon" aria-hidden="true" />
            <div className="notice__content">
              <span className="notice__title">{notice.title}</span>
              {notice.message && (
                <p className="notice__message">{notice.message}</p>
              )}
            </div>
            <button
              className="notice__dismiss"
              onClick={() => dismiss(notice.id)}
              aria-label={`Dismiss: ${notice.title}`}
            >
              <X size={14} aria-hidden="true" />
            </button>
          </div>
        );
      })}
    </div>
  );
}
