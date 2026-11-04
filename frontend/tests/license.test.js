import test from "node:test";
import assert from "node:assert/strict";
import { licenseWarning } from "../src/license.js";

const eng = (flags) => ({ license_code: "MIT", license_model: "MIT", license_flags: flags });

test("non-commercial", () => { const w = licenseWarning(eng(["non-commercial"])); assert.ok(w.restrictive); assert.match(w.text, /Non-commercial/); });
test("copyleft", () => { const w = licenseWarning(eng(["copyleft"])); assert.ok(w.restrictive); assert.match(w.text, /Copyleft/); });
test("both", () => { const w = licenseWarning(eng(["non-commercial", "copyleft"])); assert.deepEqual(w.flags, ["non-commercial", "copyleft"]); assert.match(w.text, /Non-commercial.*Copyleft/); });
test("unknown flag is restrictive with generic text", () => { const w = licenseWarning(eng(["weird"])); assert.ok(w.restrictive); assert.match(w.text, /weird/); });
test("no flags: no warning but license exposed", () => { const w = licenseWarning(eng([])); assert.equal(w.restrictive, false); assert.equal(w.text, ""); assert.equal(w.license_code, "MIT"); assert.equal(w.license_model, "MIT"); });
