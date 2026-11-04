/**
 * Raadio Kuku otse-eetri reaalajas reklaamikõllide akustiline tuvastaja (Web Audio API).
 * Tuvastab Kuku algus- ja lõpukõllid otse sissetulevast helivoost, kasutades
 * normaliseeritud ristkorrelatsiooni (Pearsoni korrelatsioonikordaja).
 */

const TARGET_SAMPLE_RATE = 2000;
const START_THRESHOLD = 0.68;
const END_THRESHOLD = 0.58;
const BUFFER_SECONDS = 7;
const RING_BUFFER_SIZE = TARGET_SAMPLE_RATE * BUFFER_SECONDS;

let cachedTemplates = null;

/**
 * Laeb etalonkõllid failist data/jingles.json.
 */
export async function loadJingleTemplates(basePath = "data/jingles.json") {
  if (cachedTemplates) return cachedTemplates;

  let json;
  if (typeof window !== "undefined" || basePath.startsWith("http://") || basePath.startsWith("https://")) {
    const resp = await fetch(basePath);
    if (!resp.ok) throw new Error(`Kõllide laadimine ebaõnnestus: ${resp.status}`);
    json = await resp.json();
  } else {
    const fs = await import("node:fs");
    json = JSON.parse(fs.readFileSync(basePath, "utf-8"));
  }

  function decodeF32(b64) {
    if (typeof atob === "function") {
      const bin = atob(b64);
      const bytes = new Uint8Array(bin.length);
      for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
      return new Float32Array(bytes.buffer, bytes.byteOffset, bytes.byteLength / 4);
    }
    // Node.js keskkonnas (testides)
    const buf = Buffer.from(b64, "base64");
    return new Float32Array(buf.buffer, buf.byteOffset, buf.byteLength / 4);
  }

  const start = {
    samples: decodeF32(json.start.samples),
    energy: json.start.energy,
    length: json.start.length,
  };

  const ends = json.ends.map(e => ({
    name: e.name,
    samples: decodeF32(e.samples),
    energy: e.energy,
    length: e.length,
  }));

  cachedTemplates = {
    sampleRate: json.sampleRate || TARGET_SAMPLE_RATE,
    start,
    ends,
  };

  return cachedTemplates;
}

/**
 * Arvutab normaliseeritud ristkorrelatsiooni helipuhvri saba ja etaloni vahel.
 * @param {Float32Array} ringBuffer - Ringpuhver
 * @param {number} ringIndex - Ringpuhvri viimane kirjutuspositsioon
 * @param {object} template - Etaloni objekt ({ samples, energy, length })
 * @param {number} [searchSamples=1000] - Mitu viimast diskreedi positsiooni kontrollitakse (~0.5s)
 * @param {number} [step=4] - Kontrolli samm diskreetides (~2ms 2000Hz juures)
 * @returns {number} Suurim korrelatsioon vahemikus 0..1
 */
export function checkCorrelation(ringBuffer, ringIndex, template, searchSamples = 1000, step = 4) {
  const tLen = template.length;
  const bLen = ringBuffer.length;
  if (bLen < tLen) return 0;

  // Koostame järjestatud saba ringpuhvrist
  const ordered = new Float32Array(bLen);
  const tail = bLen - ringIndex;
  ordered.set(ringBuffer.subarray(ringIndex), 0);
  ordered.set(ringBuffer.subarray(0, ringIndex), tail);

  const maxOffset = bLen - tLen;
  const minOffset = Math.max(0, maxOffset - searchSamples);

  let bestScore = 0;
  const tSamples = template.samples;
  const tEnergy = template.energy;

  for (let offset = minOffset; offset <= maxOffset; offset += step) {
    let dot = 0;
    let eAudio = 0;
    let mAudio = 0;

    for (let i = 0; i < tLen; i++) {
      mAudio += ordered[offset + i];
    }
    mAudio /= tLen;

    for (let i = 0; i < tLen; i++) {
      const a = ordered[offset + i] - mAudio;
      dot += a * tSamples[i];
      eAudio += a * a;
    }

    const denom = Math.sqrt(eAudio * tEnergy + 1e-6);
    const score = dot / denom;
    if (score > bestScore) bestScore = score;
  }

  return bestScore;
}

/**
 * Loob reaalajas Kuku helivoo akustilise kõllituvastaja.
 */
export class LiveAudioDetector {
  constructor({ onAdStart, onAdEnd, onStatus }) {
    this.onAdStart = onAdStart || (() => {});
    this.onAdEnd = onAdEnd || (() => {});
    this.onStatus = onStatus || (() => {});

    this.templates = null;
    this.state = "show"; // "show" | "ad"
    this.ringBuffer = new Float32Array(RING_BUFFER_SIZE);
    this.ringIndex = 0;
    this.resamplePhase = 0;
    this.totalSamplesReceived = 0;
    this.lastCheckSample = 0;
    this.adStartTime = 0;
    this.checkIntervalSamples = TARGET_SAMPLE_RATE * 0.25; // Kontrolli iga 250ms järel
    this.safetyTimeoutMs = 120 * 1000; // 2 minutit max reklaamipaus
    this.cooldownUntil = 0;
  }

  async init(basePath = "data/jingles.json") {
    this.templates = await loadJingleTemplates(basePath);
    return this;
  }

  setState(newState) {
    this.state = newState;
    if (newState === "ad") {
      this.adStartTime = Date.now();
    }
  }

  reset() {
    this.ringBuffer.fill(0);
    this.ringIndex = 0;
    this.resamplePhase = 0;
    this.totalSamplesReceived = 0;
    this.lastCheckSample = 0;
    this.state = "show";
    this.adStartTime = 0;
  }

  checkSafetyTimeout(now = Date.now()) {
    if (this.state === "ad" && this.adStartTime > 0 && now - this.adStartTime > this.safetyTimeoutMs) {
      this.state = "show";
      this.adStartTime = 0;
      this.cooldownUntil = now + 5000;
      this.onAdEnd({ fallback: true });
      return true;
    }
    return false;
  }

  /**
   * Võtab vastu toored PCM float32 helinäidised Web Audio API-st (nt 44.1kHz või 48kHz).
   * @param {Float32Array} inputSamples 
   * @param {number} inputSampleRate 
   */
  processAudio(inputSamples, inputSampleRate = 44100) {
    if (!this.templates) return;

    const now = Date.now();
    if (this.checkSafetyTimeout(now)) return;

    // 1. Faasitäpne alladiskreetimine 2000 Hz peale lineaarse interpolatsiooniga
    const ratio = inputSampleRate / TARGET_SAMPLE_RATE;
    let idx = this.resamplePhase;

    while (idx < inputSamples.length) {
      const idx0 = Math.floor(idx);
      const idx1 = Math.min(idx0 + 1, inputSamples.length - 1);
      const frac = idx - idx0;
      const sample = inputSamples[idx0] * (1 - frac) + inputSamples[idx1] * frac;

      this.ringBuffer[this.ringIndex] = sample;
      this.ringIndex = (this.ringIndex + 1) % RING_BUFFER_SIZE;
      this.totalSamplesReceived++;
      idx += ratio;
    }
    this.resamplePhase = idx - inputSamples.length;

    // 2. Kontrollime kõlle ainult teatud intervalli tagant (nt iga 250ms)
    if (this.totalSamplesReceived - this.lastCheckSample < this.checkIntervalSamples) {
      return;
    }
    this.lastCheckSample = this.totalSamplesReceived;

    if (now < this.cooldownUntil) {
      return;
    }

    // 3. Kõllituvastus vastavalt olekule
    if (this.state === "show") {
      // Saate ajal kuulame reklaami alguskõlli
      const score = checkCorrelation(this.ringBuffer, this.ringIndex, this.templates.start, 1000, 4);
      if (this.onStatus) this.onStatus({ state: "show", score });

      if (score >= START_THRESHOLD) {
        this.state = "ad";
        this.adStartTime = now;
        this.cooldownUntil = now + 15000; // Vähemalt 15s ei otsi uuesti
        this.onAdStart({ score });
      }
    } else if (this.state === "ad") {
      // Reklaami ajal kuulame reklaami lõpukõlle
      let bestScore = 0;
      let bestName = "";

      for (const tpl of this.templates.ends) {
        const s = checkCorrelation(this.ringBuffer, this.ringIndex, tpl, 1000, 4);
        if (s > bestScore) {
          bestScore = s;
          bestName = tpl.name;
        }
      }

      if (this.onStatus) this.onStatus({ state: "ad", score: bestScore, jingle: bestName });

      if (bestScore >= END_THRESHOLD) {
        this.state = "show";
        this.adStartTime = 0;
        this.cooldownUntil = now + 15000; // Vähemalt 15s ei otsi uuesti
        this.onAdEnd({ score: bestScore, jingle: bestName });
      }
    }
  }
}
