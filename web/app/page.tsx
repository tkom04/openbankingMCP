"use client";
import { useMemo, useState, useEffect } from "react";
import { apiClient, type Account, type Transaction } from "@/lib/api";
import type { Tx } from "@/lib/types";

export default function Page() {
  const [txs, setTxs] = useState<Tx[]>([]);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [selectedAccount, setSelectedAccount] = useState<string>("");
  const [query, setQuery] = useState("");
  const [from, setFrom] = useState<string>("");
  const [to, setTo] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>("");

  // Load accounts on component mount
  useEffect(() => {
    async function loadAccounts() {
      try {
        setLoading(true);
        const response = await apiClient.getAccounts();
        setAccounts(response.accounts);
        if (response.accounts.length > 0) {
          setSelectedAccount(response.accounts[0].id);
        }
      } catch (err) {
        setError(`Failed to load accounts: ${err instanceof Error ? err.message : 'Unknown error'}`);
      } finally {
        setLoading(false);
      }
    }
    loadAccounts();
  }, []);

  // Load transactions when account or date range changes
  useEffect(() => {
    if (selectedAccount && from && to) {
      loadTransactions();
    }
  }, [selectedAccount, from, to]);

  async function loadTransactions() {
    if (!selectedAccount || !from || !to) return;

    try {
      setLoading(true);
      setError("");
      const response = await apiClient.getTransactions(selectedAccount, from, to);

      // Convert API transactions to local Tx format
      const convertedTxs: Tx[] = response.transactions.map((tx: Transaction) => ({
        id: tx.id,
        date: tx.date,
        description: tx.description,
        amount: Math.abs(tx.amount),
        direction: tx.direction === 'credit' ? 'in' : 'out',
        account: tx.account_id,
        category: tx.category,
      }));

      setTxs(convertedTxs);
    } catch (err) {
      setError(`Failed to load transactions: ${err instanceof Error ? err.message : 'Unknown error'}`);
    } finally {
      setLoading(false);
    }
  }

  const filtered = useMemo(() => {
    return txs.filter((t) => {
      if (query && !t.description.toLowerCase().includes(query.toLowerCase())) return false;
      return true;
    });
  }, [txs, query]);

  const total = useMemo(() => {
    const incoming = filtered.filter(t => t.direction === "in").reduce((s, t) => s + t.amount, 0);
    const outgoing = filtered.filter(t => t.direction === "out").reduce((s, t) => s + t.amount, 0);
    return { incoming, outgoing, net: incoming - outgoing };
  }, [filtered]);

  async function downloadCSV() {
    if (!selectedAccount || !from || !to) {
      setError("Please select an account and date range");
      return;
    }

    try {
      setLoading(true);
      setError("");
      const blob = await apiClient.downloadHMRCCSV(selectedAccount, from, to);

      // Trigger download
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = `hmrc-export-${selectedAccount}-${from}-${to}.csv`;
      a.click();
      URL.revokeObjectURL(a.href);
    } catch (err) {
      setError(`Failed to download CSV: ${err instanceof Error ? err.message : 'Unknown error'}`);
    } finally {
      setLoading(false);
    }
  }

  function clearAll() {
    setTxs([]);
    setQuery("");
    setFrom("");
    setTo("");
    setError("");
  }

  return (
    <main className="mx-auto max-w-5xl p-6 space-y-6">
      <h1 className="text-2xl font-bold">Finance Autopilot — Open Banking → Timeline → HMRC CSV</h1>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-red-700">
          {error}
        </div>
      )}

      <section className="grid grid-cols-1 md:grid-cols-5 gap-3">
        <select
          className="border rounded-xl p-2"
          value={selectedAccount}
          onChange={(e) => setSelectedAccount(e.target.value)}
          disabled={loading}
        >
          <option value="">Select Account</option>
          {accounts.map((account) => (
            <option key={account.id} value={account.id}>
              {account.name} ({account.type})
            </option>
          ))}
        </select>

        <input
          className="border rounded-xl p-2"
          type="date"
          value={from}
          onChange={(e) => setFrom(e.target.value)}
          disabled={loading}
          placeholder="From date"
        />

        <input
          className="border rounded-xl p-2"
          type="date"
          value={to}
          onChange={(e) => setTo(e.target.value)}
          disabled={loading}
          placeholder="To date"
        />

        <input
          className="border rounded-xl p-2"
          placeholder="Search description…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          disabled={loading}
        />

        <div className="flex gap-2">
          <button
            onClick={downloadCSV}
            className="px-4 py-2 rounded-xl bg-black text-white disabled:opacity-50"
            disabled={loading || !selectedAccount || !from || !to}
          >
            {loading ? "Loading..." : "Export HMRC CSV"}
          </button>
          <button
            onClick={clearAll}
            className="px-4 py-2 rounded-xl border disabled:opacity-50"
            disabled={loading}
          >
            Clear
          </button>
        </div>
      </section>

      {txs.length > 0 && (
        <>
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

      {txs.length === 0 && !loading && selectedAccount && from && to && (
        <div className="text-center text-gray-500 py-8">
          No transactions found for the selected account and date range.
        </div>
      )}

      {loading && (
        <div className="text-center text-gray-500 py-8">
          Loading...
        </div>
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
