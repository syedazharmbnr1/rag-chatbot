
// lib/api.ts
export async function loginUser(username: string, password: string): Promise<{ token: string, user_id: string }> {
  console.log("Starting login for user:", username);
  
  // Build OAuth2 form data
  const body = new URLSearchParams({
    username,
    password,
    grant_type: "password",
  });

  console.log("Making request to login endpoint...");
  
  let rawText: string;
  
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 30000); // 30 second timeout

    const res = await fetch("http://34.70.203.66:8002/token", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body,
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    console.log("Response received, status:", res.status);
    
    rawText = await res.text();
    console.log("Login response status:", res.status);
    console.log("Login response text:", rawText);

    if (!res.ok) {
      console.error("Login failed with status:", res.status);
      console.error("Login error response:", rawText);
      
      // More specific error messages
      if (res.status === 401) {
        throw new Error("Invalid username or password");
      } else if (res.status === 422) {
        throw new Error("Invalid request format");
      } else if (res.status >= 500) {
        throw new Error("Server error - please try again later");
      } else {
        throw new Error(`Login failed with status ${res.status}`);
      }
    }
    
    console.log("Login successful, parsing response...");
  } catch (networkError) {
    console.error("Network error during login:", networkError);
    
    if (networkError instanceof Error) {
      if (networkError.name === 'AbortError') {
        throw new Error("Login request timed out - please try again");
      }
      if (networkError.message.includes('fetch') || networkError.message.includes('network')) {
        throw new Error("Unable to connect to server - please check your internet connection");
      }
    }
    
    throw networkError;
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
