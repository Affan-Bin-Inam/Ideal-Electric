// The server's validation messages are written for developers.
// This turns the common ones into plain language. Unknown messages pass through unchanged.
export function friendlyMessage(msg: string): string {
  if (msg.startsWith("String should match pattern")) {
    return "This isn't in an accepted format. Please check it.";
  }
  const most = msg.match(/at most (\d+) character/);
  if (most) return `Too long: at most ${most[1]} characters.`;
  const least = msg.match(/at least (\d+) character/);
  if (least) return `Too short: at least ${least[1]} characters.`;
  if (msg === "Field required") return "This field is required.";
  const lower = msg.toLowerCase();
  if (lower.includes("valid email")) return "Please enter a valid email address.";
  if (lower.includes("valid url")) {
    return "Please enter a full web address, starting with https://";
  }
  return msg;
}