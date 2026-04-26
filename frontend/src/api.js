/**
 * Normalizuje bazowy URL API, usuwając końcowy ukośnik.
 */
export function normalizeApiBaseUrl(apiBaseUrl) {
  return (apiBaseUrl || "").replace(/\/+$/, "");
}

/**
 * Pobiera publiczną konfigurację widżetu z backendu.
 */
export async function fetchPublicConfig(apiBaseUrl) {
  const response = await fetch(`${normalizeApiBaseUrl(apiBaseUrl)}/api/v1/control/public-config`);
  if (!response.ok) {
    throw new Error("Nie udało się pobrać konfiguracji widżetu.");
  }
  return response.json();
}

/**
 * Rozpoczyna nowy czat i zwraca lead_id oraz pierwszą wiadomość.
 */
export async function startChat(apiBaseUrl) {
  const response = await fetch(`${normalizeApiBaseUrl(apiBaseUrl)}/api/v1/chat/start`, {
    method: "POST",
  });
  if (!response.ok) {
    throw new Error("Nie udało się uruchomić czatu.");
  }
  return response.json();
}

/**
 * Wysyła tekst klienta do backendu.
 */
export async function sendChatMessage(apiBaseUrl, payload) {
  const response = await fetch(`${normalizeApiBaseUrl(apiBaseUrl)}/api/v1/chat/message`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(body?.detail || "Nie udało się wysłać wiadomości.");
  }
  return body;
}

/**
 * Wysyła zdjęcie lub wideo do leada.
 */
export async function uploadLeadMedia(apiBaseUrl, leadId, mediaFile) {
  const formData = new FormData();
  formData.append("lead_id", String(leadId));
  formData.append("media", mediaFile);
  const response = await fetch(`${normalizeApiBaseUrl(apiBaseUrl)}/api/v1/chat/upload`, {
    method: "POST",
    body: formData,
  });
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(body?.detail || "Nie udało się przesłać pliku.");
  }
  return body;
}

/**
 * Tworzy wycenę na podstawie przesłanego pliku.
 */
export async function estimateLeadMedia(apiBaseUrl, payload) {
  const response = await fetch(`${normalizeApiBaseUrl(apiBaseUrl)}/api/v1/estimate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(body?.detail || "Nie udało się przygotować wyceny.");
  }
  return body;
}
