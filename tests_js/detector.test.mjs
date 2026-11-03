import { test } from "node:test";
import assert from "node:assert/strict";
import path from "node:path";
import { loadJingleTemplates, checkCorrelation, LiveAudioDetector } from "../site/lib/live_detector.js";

const JINGLES_PATH = path.resolve("site/data/jingles.json");

test("loadJingleTemplates laeb jingles.json korrektselt", async () => {
  const tpls = await loadJingleTemplates(JINGLES_PATH);
  assert.equal(tpls.sampleRate, 2000);
  assert.ok(tpls.start.samples.length > 5000, "Alguskõll peab sisaldama näidiseid");
  assert.ok(tpls.ends.length >= 6, "Peab olema vähemalt 6 lõpukõlli");
});

test("checkCorrelation annab etaloni enesekorrelatsiooniks ~1.0", async () => {
  const tpls = await loadJingleTemplates(JINGLES_PATH);
  const start = tpls.start;

  // Teeme puhvri, mille lõpus on täpselt alguskõll
  const buf = new Float32Array(2000 * 7);
  const offset = buf.length - start.length;
  buf.set(start.samples, offset);

  const score = checkCorrelation(buf, 0, start, 500, 4);
  assert.ok(score >= 0.98, `Enesekorrelatsioon peab olema lähedal 1.0-le (saadi ${score})`);
});

test("LiveAudioDetector tuvastab voost alguskõlli ja lõpukõlli", async () => {
  let adStarted = false;
  let adEnded = false;

  const detector = new LiveAudioDetector({
    onAdStart: () => { adStarted = true; },
    onAdEnd: () => { adEnded = true; },
  });
  await detector.init(JINGLES_PATH);

  const tpls = await loadJingleTemplates(JINGLES_PATH);

  // 1. Sööme 2 sekundit juhuslikku müra (ei tohi lülituda)
  const noise = new Float32Array(44100 * 2);
  for (let i = 0; i < noise.length; i++) noise[i] = (Math.random() - 0.5) * 0.1;
  detector.processAudio(noise, 44100);
  assert.equal(adStarted, false, "Müra ei tohi alguskõlli käivitada");

  // 2. Sööme alguskõlli + 0.5s vaikust (et kõll jõuaks otsinguaknasse)
  const startAudio2k = tpls.start.samples;
  const padSamples = Math.floor(2000 * 0.5);
  const stream2k = new Float32Array(startAudio2k.length + padSamples);
  stream2k.set(startAudio2k, 0);

  const ratio = 44100 / 2000;
  const audio44k = new Float32Array(Math.floor(stream2k.length * ratio));
  for (let i = 0; i < audio44k.length; i++) {
    audio44k[i] = stream2k[Math.floor(i / ratio)];
  }

  // Saadame tükkidena (nagu reaalses brauseris 4096 kaupa)
  const chunkSize = 4096;
  for (let i = 0; i < audio44k.length; i += chunkSize) {
    const chunk = audio44k.subarray(i, Math.min(audio44k.length, i + chunkSize));
    detector.processAudio(chunk, 44100);
  }

  assert.equal(adStarted, true, "Alguskõll pidi käivitama onAdStart");
  assert.equal(detector.state, "ad", "Olek pidi minema reklaamile");

  // 3. Sööme lõpukõlli + 0.5s vaikust
  detector.cooldownUntil = 0; // Testis tühistame cooldowni
  const endAudio2k = tpls.ends[0].samples;
  const endStream2k = new Float32Array(endAudio2k.length + padSamples);
  endStream2k.set(endAudio2k, 0);

  const endAudio44k = new Float32Array(Math.floor(endStream2k.length * ratio));
  for (let i = 0; i < endAudio44k.length; i++) {
    endAudio44k[i] = endStream2k[Math.floor(i / ratio)];
  }

  for (let i = 0; i < endAudio44k.length; i += chunkSize) {
    const chunk = endAudio44k.subarray(i, Math.min(endAudio44k.length, i + chunkSize));
    detector.processAudio(chunk, 44100);
  }

  assert.equal(adEnded, true, "Lõpukõll pidi käivitama onAdEnd");
  assert.equal(detector.state, "show", "Olek pidi naasma saate peale");
});
