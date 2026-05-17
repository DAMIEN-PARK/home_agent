const ID_KEY = "home-agent.device-id";
const NAME_KEY = "home-agent.device-name";

function newUuid(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  // RFC4122-ish fallback for environments without crypto.randomUUID
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

export function getDeviceId(): string {
  let id = localStorage.getItem(ID_KEY);
  if (!id) {
    id = newUuid();
    localStorage.setItem(ID_KEY, id);
  }
  return id;
}

export function getDeviceName(): string | null {
  return localStorage.getItem(NAME_KEY);
}

export function setDeviceName(name: string): void {
  localStorage.setItem(NAME_KEY, name);
}

export function clearDeviceName(): void {
  localStorage.removeItem(NAME_KEY);
}
