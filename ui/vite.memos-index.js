// memos_index.json: a small index of public/data/memos.json (prompts, aliases, kinds, suggestions; no
// answer blocks) so the chat paints its chips before the multi-MB answer file arrives. Served in dev,
// emitted into dist at build; derived on the fly from memos.json, never committed.
import { existsSync, readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));

export const safeId = (id) => String(id).replace(/[^A-Za-z0-9_-]/g, "_");

function load(dir) {
  const p = resolve(HERE, "public/data", dir, "memos.json");
  return existsSync(p) ? JSON.parse(readFileSync(p, "utf8")) : null;
}

function make(dir) {
  const p = resolve(HERE, "public/data", dir, "memos.json");
  if (!existsSync(p)) return null;
  const f = JSON.parse(readFileSync(p, "utf8"));
  const { memos, ...rest } = f;
  return JSON.stringify({ ...rest, index_only: true,
    memos: (memos ?? []).map((m) => ({ id: m.id, prompt: m.prompt, aliases: m.aliases, ticker: m.ticker, kind: m.kind, format: m.format })) });
}

export function memosIndex() {
  return {
    name: "memos-index",
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        const one = (req.url || "").match(/\/data\/(_sample\/)?memos\/([A-Za-z0-9_-]+)\.json/);
        if (one) {
          const f = load(one[1] ? "_sample" : "");
          const memo = f && (f.memos || []).find((x) => safeId(x.id) === one[2]);
          if (!memo) { res.statusCode = 404; res.end(); return; }
          res.setHeader("Content-Type", "application/json");
          res.end(JSON.stringify(memo));
          return;
        }
        const m = (req.url || "").match(/\/data\/(_sample\/)?memos_index\.json/);
        if (!m) return next();
        const body = make(m[1] ? "_sample" : "");
        if (!body) { res.statusCode = 404; res.end(); return; }
        res.setHeader("Content-Type", "application/json");
        res.end(body);
      });
    },
    generateBundle() {
      for (const dir of ["", "_sample"]) {
        const body = make(dir);
        if (body) this.emitFile({ type: "asset", fileName: `data/${dir ? `${dir}/` : ""}memos_index.json`, source: body });
        // One file per answer, so a click fetches tens of kB instead of the whole answer file.
        for (const memo of (load(dir)?.memos || [])) {
          this.emitFile({ type: "asset", fileName: `data/${dir ? `${dir}/` : ""}memos/${safeId(memo.id)}.json`, source: JSON.stringify(memo) });
        }
      }
    },
  };
}
