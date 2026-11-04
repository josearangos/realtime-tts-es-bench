// License warning rules (R8). Restrictive flags are shown prominently; unknown flags fail loud.

const KNOWN = {
  "non-commercial": "Non-commercial license: not for commercial use.",
  copyleft: "Copyleft license: derived work may have to be released under the same terms.",
};

export function licenseWarning(engine) {
  const flags = Array.isArray(engine?.license_flags) ? engine.license_flags : [];
  const info = { license_code: engine?.license_code ?? null, license_model: engine?.license_model ?? null };
  if (flags.length === 0) return { restrictive: false, flags: [], text: "", ...info };
  const parts = flags.map((f) => KNOWN[f] ?? `Restrictive license flag '${f}': check the license before use.`);
  return { restrictive: true, flags: [...flags], text: parts.join(" "), ...info };
}
