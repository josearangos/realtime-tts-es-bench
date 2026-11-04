import test from "node:test";
import assert from "node:assert/strict";
import { filterCorpus, activate, campaigns } from "../src/corpus.js";

const S = [
  { id: "COB-001", text: "El saldo es de cien pesos.", campaign: "collections", scenario: "card_balance", tags: [] },
  { id: "VEN-001", text: "Buenos días, ¿cómo está?", campaign: "outbound_sales", scenario: "greeting", tags: [] },
];

test("filter by campaign", () => assert.deepEqual(filterCorpus(S, { campaign: "collections" }).map((s) => s.id), ["COB-001"]));
test("filter by free text, case-insensitive", () => assert.deepEqual(filterCorpus(S, { query: "BUENOS" }).map((s) => s.id), ["VEN-001"]));
test("no filter returns all; campaigns listed", () => { assert.equal(filterCorpus(S).length, 2); assert.deepEqual(campaigns(S), ["collections", "outbound_sales"]); });
test("activation returns text unchanged", () => assert.equal(activate(S[1]), "Buenos días, ¿cómo está?"));
