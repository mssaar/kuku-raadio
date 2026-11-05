/**
 * Helivoo aadressi lahendaja (Audio Proxy resolver).
 *
 * Suunab GitHub Releases allalaadimislingid läbi Cloudflare Workeri,
 * kui seadistustes (data/config.json) on määratud audioProxy.
 */
export function resolveAudioUrl(url, proxyBase) {
  if (!url) return "";
  if (!proxyBase) return url;
  if (url.includes("github.com") || url.includes("githubusercontent.com")) {
    const cleanProxy = proxyBase.replace(/\/+$/, "");
    return `${cleanProxy}/?url=${encodeURIComponent(url)}`;
  }
  return url;
}
