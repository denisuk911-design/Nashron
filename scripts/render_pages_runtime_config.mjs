import { readFileSync, writeFileSync } from "node:fs";

const target = process.argv[2] || "apps/web/static/runtime-config.js";
const apiBase = (process.env.LUMINIFERA_API_BASE || "").trim().replace(/\/$/, "");

if (!apiBase || !/^https:\/\//i.test(apiBase)) {
  throw new Error("LUMINIFERA_API_BASE must be an HTTPS URL");
}

const template = readFileSync("runtime-config.template.js", "utf8");
writeFileSync(target, template.replace('"__LUMINIFERA_API_BASE__"', JSON.stringify(apiBase)), "utf8");
