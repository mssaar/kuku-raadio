/**
 * Cloudflare Worker: Kuku Raadio GitHub Releases helivoo vahendaja (Audio Proxy).
 *
 * Lahendab probleemi, kus iOS (iPhone/iPad Safari ja Messengeri sisebrauser)
 * keeldub esitamast GitHub Releases helifaile vale MIME-tüübi
 * (application/octet-stream) ja Content-Disposition: attachment päiste tõttu.
 *
 * Worker:
 * 1. Lubab CORS päringud (Access-Control-Allow-Origin: *).
 * 2. Toetab HTTP Range päringuid (vajalik iPhone'is helifaili kerimiseks ja puhverdamiseks).
 * 3. Tagastab päise Content-Type: audio/mpeg ja eemaldab sunniviisilise allalaadimise (attachment -> inline).
 */

const CORS_HEADERS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
  "Access-Control-Allow-Headers": "Range, Content-Type, Accept, If-None-Match, If-Modified-Since",
  "Access-Control-Expose-Headers": "Content-Length, Content-Range, Accept-Ranges, Content-Type",
};

export default {
  async fetch(request) {
    if (request.method === "OPTIONS") {
      return new Response(null, {
        status: 204,
        headers: CORS_HEADERS,
      });
    }

    if (request.method !== "GET" && request.method !== "HEAD") {
      return new Response("Meetod pole lubatud", { status: 405, headers: CORS_HEADERS });
    }

    const reqUrl = new URL(request.url);
    const targetUrl = reqUrl.searchParams.get("url");

    if (!targetUrl) {
      return new Response(
        "Kuku Raadio Audio Proxy töötab!\n\nKasutamine: ?url=https://github.com/.../releases/download/.../fail.mp3",
        {
          status: 200,
          headers: { "Content-Type": "text/plain; charset=utf-8", ...CORS_HEADERS },
        }
      );
    }

    let parsedTarget;
    try {
      parsedTarget = new URL(targetUrl);
    } catch {
      return new Response("Vigane URL", { status: 400, headers: CORS_HEADERS });
    }

    // Turvalisus: lubame vahendada ainult GitHubi ametlikke helifaile
    const allowedHosts = [
      "github.com",
      "release-assets.githubusercontent.com",
      "objects.githubusercontent.com",
      "github-production-release-asset-2e65be.s3.amazonaws.com",
    ];

    const hostOk = allowedHosts.some(h => parsedTarget.hostname === h || parsedTarget.hostname.endsWith(".githubusercontent.com") || parsedTarget.hostname.endsWith(".amazonaws.com"));
    if (!hostOk || parsedTarget.protocol !== "https:") {
      return new Response("Lubamatu sihtkoht. Proxy toetab ainult GitHubi helifaile.", { status: 403, headers: CORS_HEADERS });
    }

    // Edastame vajalikud päised (eriti Range päringud)
    const forwardHeaders = new Headers();
    const range = request.headers.get("Range");
    if (range) forwardHeaders.set("Range", range);
    const ifRange = request.headers.get("If-Range");
    if (ifRange) forwardHeaders.set("If-Range", ifRange);
    const ifNoneMatch = request.headers.get("If-None-Match");
    if (ifNoneMatch) forwardHeaders.set("If-None-Match", ifNoneMatch);

    let upstreamResponse;
    try {
      upstreamResponse = await fetch(targetUrl, {
        method: request.method,
        headers: forwardHeaders,
        redirect: "follow",
      });
    } catch (err) {
      return new Response(`Viga GitHubist allalaadimisel: ${err.message}`, { status: 502, headers: CORS_HEADERS });
    }

    // Koostame vastuse päised
    const resHeaders = new Headers(CORS_HEADERS);

    // KRIITILINE: määrame alati puhta audio/mpeg MIME-tüübi ja inline esituse
    resHeaders.set("Content-Type", "audio/mpeg");
    resHeaders.set("Accept-Ranges", "bytes");

    // Eemaldame attachmenti ja määrame failinime inline esituseks
    const urlFilename = parsedTarget.pathname.split("/").pop() || "saade.mp3";
    resHeaders.set("Content-Disposition", `inline; filename="${urlFilename}"`);

    // Kopeerime vajalikud päised algsest vastusest
    const copyHeaders = ["content-length", "content-range", "etag", "last-modified", "cache-control"];
    for (const h of copyHeaders) {
      const val = upstreamResponse.headers.get(h);
      if (val) resHeaders.set(h, val);
    }

    return new Response(upstreamResponse.body, {
      status: upstreamResponse.status,
      statusText: upstreamResponse.statusText,
      headers: resHeaders,
    });
  },
};
