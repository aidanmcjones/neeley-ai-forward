import { spawn } from "node:child_process"; import { writeFileSync } from "node:fs";
const [url, out, w, h, mode = "dark"] = process.argv.slice(2); const port = 9950 + Math.floor(Math.random() * 40);
const S = "/private/tmp/claude-501/-Users-aidanjones/65520c57-4dc1-4183-a831-845e1b7c0d6e/scratchpad/p2fx";
const chrome = spawn("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", ["--headless=new", `--remote-debugging-port=${port}`, `--user-data-dir=${S}/sw${port}`, "--hide-scrollbars", "--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader", `--window-size=${w},${h}`, "about:blank"], { stdio: "ignore" });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let ws; for (let i = 0; i < 60; i++) { try { const j = await (await fetch(`http://127.0.0.1:${port}/json`)).json(); const p = j.find((x) => x.type === "page"); if (p) { ws = new WebSocket(p.webSocketDebuggerUrl); break; } } catch {} await sleep(250); }
await new Promise((r) => ws.addEventListener("open", r));
let id = 0; const pend = new Map(); const logs = []; const hosts = new Set();
ws.addEventListener("message", (e) => { const m = JSON.parse(e.data); if (m.id && pend.has(m.id)) { pend.get(m.id)(m.result ?? m.error); pend.delete(m.id); }
  if (m.method === "Runtime.consoleAPICalled" && (m.params.type === "error" || m.params.type === "warning")) logs.push(m.params.args.map((a) => a.value ?? a.description).join(" ").slice(0, 200));
  if (m.method === "Runtime.exceptionThrown") logs.push("EXC " + (m.params.exceptionDetails.exception?.description ?? m.params.exceptionDetails.text).slice(0, 200));
  if (m.method === "Network.requestWillBeSent") { try { hosts.add(new URL(m.params.request.url).host); } catch {} } });
const send = (method, params = {}) => new Promise((r) => { const i = ++id; pend.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });
await send("Runtime.enable"); await send("Network.enable");
await send("Emulation.setDeviceMetricsOverride", { width: +w, height: +h, deviceScaleFactor: 2, mobile: +w < 600 });
await send("Emulation.setEmulatedMedia", { features: [{ name: "prefers-color-scheme", value: mode }] });
await send("Page.navigate", { url }); await sleep(3500);
const ev = async (expression) => (await send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true })).result?.value;
const state = () => ev(`JSON.stringify({ cols: document.querySelectorAll('.nd-cmp-col').length, wraps: document.querySelectorAll('.nd-cmp-col .mol-wrap').length, canvases: document.querySelectorAll('.mol canvas').length, lib: !!window.$3Dmol, caps: [...document.querySelectorAll('.mol-cap')].map(c => c.textContent.slice(0, 70)), sizes: [...document.querySelectorAll('.mol')].map(m => Math.round(m.getBoundingClientRect().width) + 'x' + Math.round(m.getBoundingClientRect().height)), order: [...document.querySelectorAll('.nd-cmp-col')].map(c => [...c.children].slice(0, 2).map(x => x.className).join('>')) })`);
await ev("document.querySelector('[data-hero]')?.click()");
for (let i = 0; i < 80; i++) { if (await ev("!!document.querySelector('button[data-p2-chip]')")) break; await sleep(500); }
for (let i = 0; i < 40; i++) { if ((await ev("document.querySelectorAll('.mol canvas').length")) >= 4) break; await sleep(500); }
await sleep(2500);
console.log("after part 1:", await state());
const shotSection = async (name) => { await ev("document.querySelector('section[aria-label=\"Product fine print\"]')?.scrollIntoView({block:'start'})"); await sleep(1500);
  const r = await ev("(() => { const b = document.querySelector('section[aria-label=\"Product fine print\"]').getBoundingClientRect(); return JSON.stringify({ y: b.top + window.scrollY, height: b.height }); })()"); const b = JSON.parse(r);
  const s = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: true, clip: { x: 0, y: b.y, width: +w, height: Math.min(b.height + 20, 1400), scale: 1 } }); writeFileSync(`${out}_${name}.png`, Buffer.from(s.data, "base64")); };
await shotSection("amgn");
await ev("[...document.querySelectorAll('[role=tablist][aria-label=\"Label dimension\"] button')][1]?.click()"); await sleep(1200);
console.log("after dimension switch:", await state());
await ev("[...document.querySelectorAll('[role=tablist] button[role=tab]')][1]?.click()"); await sleep(1500);
for (let i = 0; i < 30; i++) { if ((await ev("document.querySelectorAll('.mol canvas').length")) >= 8) break; await sleep(500); }
await sleep(2500);
console.log("after pick switch:", await state());
await shotSection("pick2");
await ev("[...document.querySelectorAll('[role=tablist] button[role=tab]')][2]?.click()"); await sleep(1500);
for (let i = 0; i < 30; i++) { if ((await ev("document.querySelectorAll('.mol canvas').length")) >= 11) break; await sleep(500); }
await sleep(2500);
console.log("after pick 3:", await state());
await shotSection("pick3");
console.log("hosts:", [...hosts].filter(h => !/127\.0\.0\.1/.test(h)), "logs:", logs.slice(0, 8));
ws.close(); chrome.kill();
