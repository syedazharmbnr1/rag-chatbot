
// lib/api.ts
export async function loginUser(username: string, password: string): Promise<{ token: string, user_id: string }> {
  // Build OAuth2 form data
  const body = new URLSearchParams({
    username,
    password,
    grant_type: "password",
  });

  const res = await fetch("http://34.10.53.15:8001/token", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });

  const rawText = await res.text();
  console.log("Login response status:", res.status);
  console.log("Login response text:", rawText);

  if (!res.ok) {
    console.error("Login failed:", rawText);
    throw new Error("Login failed");
  }

  let json;
  try {
    json = JSON.parse(rawText);
  } catch (error) {
    console.error("Failed to parse JSON response:", error);
    console.error("Raw response:", rawText);
    throw new Error("Invalid response format");
  }

  if (!json.access_token) {
    console.error("No access_token in response:", json);
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
    } catch (error) {
      console.error("JWT decode error:", error);
      return null;
    }
  };

  const userId = decodeJwtSub(token) ?? username;
  console.log("Decoded user_id:", userId);

  return { token, user_id: userId };
}
