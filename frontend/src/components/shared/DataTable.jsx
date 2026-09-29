import React, { useState } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import EmptyState from './EmptyState';
import Skeleton from './Skeleton';

/**
 * DataTable - Responsive, predictable table with sticky headers, pagination, and empty state.
 */
export default function DataTable({
  columns = [],
  data = [],
  loading = false,
  emptyTitle = 'No records found',
  emptyDescription = 'No data matching the active filters was found in the database.',
  onRowClick,
  selectedRowKey,
  rowKey = (row, idx) => row.id || row.alert_id || row.entity_id || row.job_id || row.case_id || idx,
  pageSize = 15,
  pagination = true,
  className = '',
}) {
  const [currentPage, setCurrentPage] = useState(1);

  if (loading) {
    return (
      <div className="table-container" style={{ padding: '1rem' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          {[1, 2, 3, 4, 5].map((i) => (
            <Skeleton key={i} width="100%" height="36px" style={{ borderRadius: 'var(--radius-sm)' }} />
          ))}
        </div>
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <EmptyState
        title={emptyTitle}
        description={emptyDescription}
      />
    );
  }

  const totalPages = pagination ? Math.ceil(data.length / pageSize) : 1;
  const validPage = Math.min(currentPage, totalPages);
  const startIndex = pagination ? (validPage - 1) * pageSize : 0;
  const endIndex = pagination ? Math.min(startIndex + pageSize, data.length) : data.length;
  const pageData = pagination ? data.slice(startIndex, endIndex) : data;

  return (
    <div className={`data-table-wrapper ${className}`}>
      <div className="table-container" style={{ overflowX: 'auto', width: '100%' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
          <thead>
            <tr>
              {columns.map((col, idx) => (
                <th
                  key={col.key || idx}
                  style={{
                    padding: '0.65rem 0.85rem',
                    fontSize: '0.72rem',
                    fontWeight: 700,
                    textTransform: 'uppercase',
                    letterSpacing: '0.06em',
                    color: 'var(--text-dim)',
                    borderBottom: '1px solid var(--border-subtle)',
                    whiteSpace: 'nowrap',
                    width: col.width,
                    textAlign: col.align || 'left',
                  }}
                >
                  {col.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {pageData.map((row, idx) => {
              const key = rowKey(row, idx);
              const isSelected = selectedRowKey !== undefined && selectedRowKey === key;
              return (
                <tr
                  key={key}
                  onClick={() => onRowClick && onRowClick(row)}
                  style={{
                    cursor: onRowClick ? 'pointer' : 'default',
                    background: isSelected ? 'rgba(247, 147, 26, 0.08)' : 'transparent',
                    borderBottom: '1px solid rgba(255, 255, 255, 0.03)',
                    transition: 'background 0.15s ease',
                  }}
                  className={onRowClick ? 'hover:bg-surface-hover' : ''}
                >
                  {columns.map((col, cIdx) => (
                    <td
                      key={col.key || col.id || cIdx}
                      style={{
                        padding: '0.65rem 0.85rem',
                        fontSize: '0.82rem',
                        verticalAlign: 'middle',
                        textAlign: col.align || 'left',
                      }}
                    >
                      {col.render
                        ? col.render(col.key ? row[col.key] : row, row, idx)
                        : col.cell
                        ? col.cell(row, idx)
                        : ((col.key ? row[col.key] : col.id ? row[col.id] : undefined) ?? '—')}
                    </td>
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {pagination && totalPages > 1 && (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '0.75rem 0.5rem 0 0.5rem',
            borderTop: '1px solid var(--border-subtle)',
            fontSize: '0.78rem',
            color: 'var(--text-muted)',
            flexWrap: 'wrap',
            gap: '0.5rem',
          }}
        >
          <div>
            Showing <strong className="mono">{startIndex + 1}–{endIndex}</strong> of <strong className="mono">{data.length}</strong> records
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <button
              className="btn btn-secondary btn-sm"
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              disabled={validPage <= 1}
              style={{ padding: '0.2rem 0.5rem' }}
            >
              <ChevronLeft size={14} />
            </button>
            <span className="mono" style={{ padding: '0 0.4rem' }}>
              {validPage} / {totalPages}
            </span>
            <button
              className="btn btn-secondary btn-sm"
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
              disabled={validPage >= totalPages}
              style={{ padding: '0.2rem 0.5rem' }}
            >
              <ChevronRight size={14} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
