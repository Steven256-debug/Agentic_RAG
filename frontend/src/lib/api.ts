/**
 * Resolve the backend API base URL, trimming stray whitespace and trailing
 * slashes so copy-pasted environment variables remain valid fetch targets.
 */
export function getApiUrl(): string {
  const envUrl = process.env.NEXT_PUBLIC_API_URL?.trim();
  let apiUrl = envUrl || "http://127.0.0.1:8000";

  if (!envUrl && typeof window !== "undefined") {
    const host = window.location.hostname;
    if (host && host !== "localhost" && host !== "127.0.0.1") {
      apiUrl = `http://${host}:8000`;
    }
  }

  return apiUrl.replace(/\/+$/, "").trim();
}
