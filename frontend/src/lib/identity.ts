const DEVICE_ID_KEY = "streammind_device_id";

function generateId(): string {
  // crypto.randomUUID() requires secure context (HTTPS or localhost)
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  // Fallback for non-secure contexts (e.g. LAN IP over HTTP)
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    return (c === "x" ? r : (r & 0x3) | 0x8).toString(16);
  });
}

export function getDeviceId(): string {
  if (typeof window === "undefined") return "";
  let id = localStorage.getItem(DEVICE_ID_KEY);
  if (!id) {
    id = generateId();
    localStorage.setItem(DEVICE_ID_KEY, id);
  }
  return id;
}

export function getSyncCode(): string {
  const id = getDeviceId();
  // Derive 8-char alphanumeric from device ID
  return id.replace(/-/g, "").slice(0, 8).toUpperCase();
}

export function haptic(ms: number = 10): void {
  try {
    navigator?.vibrate?.(ms);
  } catch {
    // Silent fallback
  }
}
