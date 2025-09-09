
// lib/api.ts
export async function loginUser(username: string, password: string): Promise<{ token: string, user_id: string }> {
  // Build OAuth2 form data
  const body = new URLSearchParams({
    username,
    password,
    grant_type: "password",
  });

  const res = await fetch("http://localhost:8000/token", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });

  const rawText = await res.text();

  if (!res.ok) {
    console.error("Login failed:", rawText);
    throw new Error("Login failed");
  }

  const json = JSON.parse(rawText);

  if (!json.access_token) {
    throw new Error("No access token received");
  }

  // Derive user_id from JWT `sub` claim
  const token: string = json.access_token;

  const decodeJwtSub = (jwt: string): string | null => {
    try {
      const parts = jwt.split(".");
      if (parts.length < 2) return null;
      // Convert base64url to base64
      const base64 = parts[1].replace(/-/g, "+").replace(/_/g, "/");
      // Pad if necessary
      const padded = base64.padEnd(base64.length + (4 - (base64.length % 4)) % 4, "=");
      const jsonPayload = atob(padded);
      const payload = JSON.parse(jsonPayload);
      return typeof payload?.sub === "string" ? payload.sub : null;
    } catch {
      return null;
    }
  };

  const userId = decodeJwtSub(token) ?? username;

  return { token, user_id: userId };
}
