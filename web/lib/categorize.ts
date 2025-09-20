import type { Tx } from "./types";

const RULES: Array<{ match: RegExp; category: string }> = [
  { match: /UBER|BOLT|LYFT/i, category: "Travel" },
  { match: /STARLING|MONZO|REVOLUT/i, category: "Bank Fees" },
  { match: /AWS|GCP|AZURE/i, category: "Hosting" },
  { match: /SUBSTACK|NOTION|GOOGLE/i, category: "Software" },
  { match: /PRET|CAFFE|STARBUCKS/i, category: "Meals" },
];

export function categorize(txs: Tx[]): Tx[] {
  return txs.map((t) => {
    const hit = RULES.find((r) => r.match.test(t.description));
    let category = hit?.category ?? "Uncategorized";

    // Map "Shopping" to "General expenses" for consistency
    if (category === "Shopping") {
      category = "General expenses";
    }

    return { ...t, category };
  });
}
