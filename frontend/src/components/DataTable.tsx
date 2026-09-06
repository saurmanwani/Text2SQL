import { Download } from "lucide-react";
import { useMemo, useState } from "react";

interface DataTableProps {
  columns: string[];
  rows: unknown[][];
}

const PAGE_SIZE = 25;

function csvCell(value: unknown) {
  return `"${String(value ?? "").replace(/"/g, '""')}"`;
}

export function DataTable({ columns, rows }: DataTableProps) {
  const [page, setPage] = useState(0);
  const [sortIndex, setSortIndex] = useState<number | null>(null);
  const sortedRows = useMemo(() => {
    if (sortIndex === null) return rows;
    return [...rows].sort((left, right) =>
      String(left[sortIndex] ?? "").localeCompare(String(right[sortIndex] ?? ""), undefined, {
        numeric: true,
      }),
    );
  }, [rows, sortIndex]);
  const pages = Math.max(1, Math.ceil(rows.length / PAGE_SIZE));
  const visibleRows = sortedRows.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);

  const download = () => {
    const csv = [
      columns.map(csvCell).join(","),
      ...rows.map((row) => row.map(csvCell).join(",")),
    ].join("\n");
    const url = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "query-results.csv";
    anchor.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-3">
      <div className="flex justify-end">
        <button onClick={download} className="flex items-center gap-2 text-xs text-muted-foreground">
          <Download className="size-3.5" /> CSV
        </button>
      </div>
      <div className="overflow-auto rounded-md border">
        <table className="w-full text-left text-sm">
          <thead className="bg-muted">
            <tr>
              {columns.map((column, index) => (
                <th key={column} className="whitespace-nowrap px-3 py-2">
                  <button onClick={() => setSortIndex(index)}>{column}</button>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {visibleRows.map((row, rowIndex) => (
              <tr key={rowIndex} className="border-t">
                {row.map((value, cellIndex) => (
                  <td key={cellIndex} className="whitespace-nowrap px-3 py-2">
                    {String(value ?? "")}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <span>{rows.length} rows</span>
        <div className="flex items-center gap-2">
          <button disabled={page === 0} onClick={() => setPage((value) => value - 1)}>
            Previous
          </button>
          <span>{page + 1} / {pages}</span>
          <button disabled={page + 1 >= pages} onClick={() => setPage((value) => value + 1)}>
            Next
          </button>
        </div>
      </div>
    </div>
  );
}
