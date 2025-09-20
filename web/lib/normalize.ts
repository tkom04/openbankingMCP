import { parseISO, isValid, format } from "date-fns";
import type { CsvRow } from "./schema";
import type { Tx } from "./types";

function parseAmount(raw: string): { amount: number; direction: "in" | "out" } {
  const n = Number(String(raw).replace(/[,£\s]/g, ""));
  if (Number.isNaN(n)) throw new Error(`Bad amount: ${raw}`);
  return n >= 0 ? { amount: Math.abs(n), direction: "in" } : { amount: Math.abs(n), direction: "out" };
}

function parseDateUK(raw: string): string {
  // Accept dd/mm/yyyy or yyyy-mm-dd
  const parts = raw.includes("/") ? raw.split("/") : raw.split("-");
  let iso = "";
  if (raw.includes("/")) {
    const [dd, mm, yyyy] = parts;
    iso = `${yyyy}-${mm.padStart(2, "0")}-${dd.padStart(2, "0")}`;
  } else {
    iso = raw;
  }
  const d = parseISO(iso);
  if (!isValid(d)) throw new Error(`Bad date: ${raw}`);
  return format(d, "yyyy-MM-dd");
}

export function normalize(rows: CsvRow[]): Tx[] {
  return rows.map((r, i) => {
    const { amount, direction } = parseAmount(r.Amount);
    return {
      id: `tx_${i}`,
      date: parseDateUK(r.Date),
      description: r.Description?.trim() ?? "",
      amount,
      direction,
      account: r.Account ?? "Primary",
    };
  });
}
