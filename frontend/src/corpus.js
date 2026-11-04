// Corpus picker logic: filter by campaign and free text. Activating an entry yields its text unchanged.

export function campaigns(sentences) {
  return [...new Set(sentences.map((s) => s.campaign))].sort();
}

export function filterCorpus(sentences, { campaign = "", query = "" } = {}) {
  const q = query.trim().toLowerCase();
  return sentences.filter((s) => {
    if (campaign && s.campaign !== campaign) return false;
    if (!q) return true;
    return s.text.toLowerCase().includes(q) || s.id.toLowerCase().includes(q) || s.scenario.toLowerCase().includes(q);
  });
}

export const activate = (entry) => entry.text;
