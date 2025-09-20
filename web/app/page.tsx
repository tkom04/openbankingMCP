"use client";
import { useMemo, useState } from "react";
import FileDrop from "@/components/FileDrop";
import { normalize } from "@/lib/normalize";
import { categorize } from "@/lib/categorize";
import type { Tx } from "@/lib/types";
import { toSelfAssessmentCSV } from "@/lib/hmrc";

export default function Page() {
  const [txs, setTxs] = useState<Tx[]>([]);
  const [query, setQuery] = useState("");
  const [from, setFrom] = useState<string>("");
  const [to, setTo] = useState<string>("");

  const filtered = useMemo(() => {
    return txs.filter((t) => {
      if (from && t.date < from) return false;
      if (to && t.date > to) return false;
      if (query && !t.description.toLowerCase().includes(query.toLowerCase())) return false;
      return true;
    });
  }, [txs, query, from, to]);

  const total = useMemo(() => {
    const incoming = filtered.filter(t => t.direction === "in").reduce((s, t) => s + t.amount, 0);
    const outgoing = filtered.filter(t => t.direction === "out").reduce((s, t) => s + t.amount, 0);
    return { incoming, outgoing, net: incoming - outgoing };
  }, [filtered]);

  function onUploadRows(rows: any[]) {
    const normalized = normalize(rows as any);
    const withCats = categorize(normalized);
    setTxs(withCats);
  }

  function downloadCSV() {
    const csv = toSelfAssessmentCSV(filtered);
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "hmrc-self-assessment.csv";
    a.click();
    URL.revokeObjectURL(a.href);
  }

  function clearAll() { setTxs([]); setQuery(""); setFrom(""); setTo(""); }

  return (
    <main className="mx-auto max-w-5xl p-6 space-y-6">
      <h1 className="text-2xl font-bold">Finance Autopilot — CSV → Timeline → HMRC CSV</h1>

      {txs.length === 0 ? (
        <FileDrop onRows={onUploadRows}/>
      ) : (
        <>
          <section className="grid grid-cols-1 md:grid-cols-4 gap-3">
            <input className="border rounded-xl p-2" placeholder="Search description…" value={query} onChange={(e)=>setQuery(e.target.value)} />
            <input className="border rounded-xl p-2" type="date" value={from} onChange={(e)=>setFrom(e.target.value)} />
            <input className="border rounded-xl p-2" type="date" value={to} onChange={(e)=>setTo(e.target.value)} />
            <div className="flex gap-2">
              <button onClick={downloadCSV} className="px-4 py-2 rounded-xl bg-black text-white">Export HMRC CSV</button>
              <button onClick={clearAll} className="px-4 py-2 rounded-xl border">Clear</button>
            </div>
          </section>

          <section className="grid grid-cols-3 gap-3">
            <Stat label="Incoming" value={`£${total.incoming.toFixed(2)}`} />
            <Stat label="Outgoing" value={`£${total.outgoing.toFixed(2)}`} />
            <Stat label="Net" value={`£${total.net.toFixed(2)}`} />
          </section>

          <section className="bg-white rounded-2xl shadow-sm overflow-hidden">
            <table className="min-w-full text-sm">
              <thead className="bg-gray-100">
                <tr>
                  <th className="px-3 py-2 text-left">Date</th>
                  <th className="px-3 py-2 text-left">Description</th>
                  <th className="px-3 py-2 text-left">Category</th>
                  <th className="px-3 py-2 text-right">Amount</th>
                  <th className="px-3 py-2 text-left">Direction</th>
                  <th className="px-3 py-2 text-left">Account</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((t) => (
                  <tr key={t.id} className="border-t">
                    <td className="px-3 py-2">{t.date}</td>
                    <td className="px-3 py-2">{t.description}</td>
                    <td className="px-3 py-2">{t.category ?? ""}</td>
                    <td className="px-3 py-2 text-right">£{t.amount.toFixed(2)}</td>
                    <td className="px-3 py-2">{t.direction}</td>
                    <td className="px-3 py-2">{t.account}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        </>
      )}
    </main>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-white rounded-2xl shadow-sm p-4">
      <div className="text-xs text-gray-500">{label}</div>
      <div className="text-xl font-semibold">{value}</div>
    </div>
  );
}
