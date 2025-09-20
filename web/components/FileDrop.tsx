"use client";
import Papa from "papaparse";
import { useCallback } from "react";
import { CsvRow, CsvRow as CsvRowType } from "@/lib/schema";

export default function FileDrop({ onRows }: { onRows: (rows: CsvRowType[]) => void }) {
  const onChange = useCallback((file: File) => {
    Papa.parse(file, {
      header: true,
      skipEmptyLines: true,
      complete: (res) => {
        const rows = (res.data as any[]).map((r) => CsvRow.parse(r));
        onRows(rows);
      },
      error: (e) => alert(`Parse error: ${e.message}`),
    });
  }, [onRows]);

  return (
    <label className="block cursor-pointer border-2 border-dashed rounded-2xl p-8 text-center bg-white shadow-sm">
      <input type="file" accept=".csv" className="hidden" onChange={(e) => e.target.files && onChange(e.target.files[0])} />
      <div className="text-lg font-semibold">Drop a bank CSV or click to upload</div>
      <div className="text-sm text-gray-500 mt-1">We parse locally—data stays in your browser.</div>
    </label>
  );
}
