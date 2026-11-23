import type { ReactNode } from "react";

type TableShellProps = {
  columns: string[];
  emptyMessage: string;
  footer?: ReactNode;
};

export default function TableShell({
  columns,
  emptyMessage,
  footer,
}: TableShellProps) {
  return (
    <div className="overflow-x-auto rounded-md border border-surface-border">
      <table className="min-w-full text-sm">
        <thead className="bg-surface-muted">
          <tr>
            {columns.map((column) => (
              <th
                key={column}
                scope="col"
                className="px-3 py-2 text-left text-[11px] font-medium uppercase tracking-[0.12em] text-ink-subtle"
              >
                {column}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="bg-surface">
          <tr>
            <td
              colSpan={columns.length}
              className="px-3 py-8 text-center text-sm text-ink-muted"
            >
              {emptyMessage}
            </td>
          </tr>
        </tbody>
      </table>
      {footer ? (
        <div className="border-t border-surface-border bg-surface-muted px-3 py-2 text-xs text-ink-muted">
          {footer}
        </div>
      ) : null}
    </div>
  );
}
