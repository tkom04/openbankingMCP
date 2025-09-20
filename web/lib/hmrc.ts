import type { Tx } from "./types";

export type HmrcRow = {
  Date: string; Description: string; Category: string; Amount: string; Direction: "in" | "out"; Account: string; Note: string;
};

export function toSelfAssessmentCSV(txs: Tx[]): string {
  const header = ["Date","Description","Category","Amount","Direction","Account","Note"].join(",");
  const body = txs.map((t) =>
    [t.date, csvSafe(t.description), t.category ?? "", t.amount.toFixed(2), t.direction, t.account, csvSafe(t.note ?? "")]
      .join(",")
  );
  return [header, ...body].join("\n");
}

function csvSafe(s: string) {
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}
