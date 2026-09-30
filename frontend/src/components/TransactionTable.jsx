import React, { useState, useMemo } from 'react';
import {
  Search,
  SlidersHorizontal,
  ChevronRight,
  AlertOctagon,
  ShieldCheck,
  CheckCircle2,
  Clock,
  ArrowUpDown,
  Eye,
  IndianRupee,
} from 'lucide-react';

export default function TransactionTable({
  transactions = [],
  analyzedMap = {},
  reviews = {},
  onSelectTransaction,
}) {
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL'); // ALL, TRIGGERED, MITIGATED, NORMAL, REVIEWED
  const [sortField, setSortField] = useState('timestamp');
  const [sortAsc, setSortAsc] = useState(false);
  const [page, setPage] = useState(1);
  const pageSize = 15;

  // Filter & Search Logic
  const filteredTransactions = useMemo(() => {
    return transactions.filter((t) => {
      const txnId = t.transaction_id || '';
      const custId = t.customer_id || '';
      const merchant = t.merchant || '';
      const location = t.location_name || '';
      const channel = t.channel || '';

      const searchMatch =
        searchTerm === '' ||
        txnId.toLowerCase().includes(searchTerm.toLowerCase()) ||
        custId.toLowerCase().includes(searchTerm.toLowerCase()) ||
        merchant.toLowerCase().includes(searchTerm.toLowerCase()) ||
        location.toLowerCase().includes(searchTerm.toLowerCase()) ||
        channel.toLowerCase().includes(searchTerm.toLowerCase());

      if (!searchMatch) return false;

      // Status Filter logic
      const analyzed = analyzedMap[txnId];
      const rules = analyzed?.rule_results || t.rule_results || [];
      const hasTriggered = rules.some((r) => r.status === 'TRIGGERED');
      const hasMitigated = rules.some((r) => r.status === 'MITIGATED');
      const hasNormal = rules.length > 0 && !hasTriggered && !hasMitigated;
      const reviewStatus = reviews[txnId]?.status;

      if (statusFilter === 'TRIGGERED') return hasTriggered;
      if (statusFilter === 'MITIGATED') return hasMitigated;
      if (statusFilter === 'NORMAL') return hasNormal;
      if (statusFilter === 'REVIEWED') return Boolean(reviewStatus);

      return true;
    });
  }, [transactions, analyzedMap, reviews, searchTerm, statusFilter]);

  // Sort Logic
  const sortedTransactions = useMemo(() => {
    return [...filteredTransactions].sort((a, b) => {
      let valA = a[sortField];
      let valB = b[sortField];

      if (sortField === 'amount') {
        valA = parseFloat(valA) || 0;
        valB = parseFloat(valB) || 0;
      } else if (sortField === 'timestamp') {
        valA = new Date(valA).getTime() || 0;
        valB = new Date(valB).getTime() || 0;
      }

      if (valA < valB) return sortAsc ? -1 : 1;
      if (valA > valB) return sortAsc ? 1 : -1;
      return 0;
    });
  }, [filteredTransactions, sortField, sortAsc]);

  const totalPages = Math.ceil(sortedTransactions.length / pageSize) || 1;
  const paginatedTransactions = useMemo(() => {
    const start = (page - 1) * pageSize;
    return sortedTransactions.slice(start, start + pageSize);
  }, [sortedTransactions, page, pageSize]);

  const handleSort = (field) => {
    if (sortField === field) {
      setSortAsc(!sortAsc);
    } else {
      setSortField(field);
      setSortAsc(false);
    }
  };

  const renderRuleBadges = (txn) => {
    const txnId = txn.transaction_id;
    const analyzed = analyzedMap[txnId];
    const rules = analyzed?.rule_results || txn.rule_results || [];

    if (!rules || rules.length === 0) {
      return (
        <span className="badge badge-neutral" style={{ fontSize: '0.675rem' }}>
          Historical Basline
        </span>
      );
    }

    const triggeredRules = rules.filter((r) => r.status === 'TRIGGERED');
    const mitigatedRules = rules.filter((r) => r.status === 'MITIGATED');

    if (triggeredRules.length > 0) {
      return (
        <div style={{ display: 'flex', gap: '0.3rem', flexWrap: 'wrap' }}>
          {triggeredRules.map((r) => (
            <span
              key={r.rule_name}
              className="badge badge-triggered"
              style={{ fontSize: '0.65rem', padding: '0.15rem 0.45rem' }}
              title={r.reason}
            >
              <AlertOctagon size={10} />
              {r.rule_name.replace('Rule', '')}
            </span>
          ))}
        </div>
      );
    }

    if (mitigatedRules.length > 0) {
      return (
        <div style={{ display: 'flex', gap: '0.3rem', flexWrap: 'wrap' }}>
          {mitigatedRules.map((r) => (
            <span
              key={r.rule_name}
              className="badge badge-mitigated"
              style={{ fontSize: '0.65rem', padding: '0.15rem 0.45rem' }}
              title={r.mitigation}
            >
              <ShieldCheck size={10} />
              Mitigated
            </span>
          ))}
        </div>
      );
    }

    return (
      <span
        className="badge badge-normal"
        style={{ fontSize: '0.65rem', padding: '0.15rem 0.45rem' }}
      >
        <CheckCircle2 size={10} />
        Clean Pass
      </span>
    );
  };

  const renderReviewBadge = (txnId) => {
    const review = reviews[txnId];
    if (!review) {
      return (
        <span
          style={{
            fontSize: '0.725rem',
            color: 'var(--text-muted)',
            display: 'flex',
            alignItems: 'center',
            gap: '0.25rem',
          }}
        >
          <Clock size={11} /> Unreviewed
        </span>
      );
    }

    switch (review.status) {
      case 'APPROVED':
        return (
          <span className="badge badge-normal" style={{ fontSize: '0.65rem' }}>
            Approved
          </span>
        );
      case 'ESCALATED':
        return (
          <span
            className="badge"
            style={{
              background: 'rgba(245, 158, 11, 0.15)',
              color: '#fbbf24',
              borderColor: 'rgba(245, 158, 11, 0.3)',
              fontSize: '0.65rem',
            }}
          >
            Escalated
          </span>
        );
      case 'DECLINED':
        return (
          <span className="badge badge-triggered" style={{ fontSize: '0.65rem' }}>
            Declined
          </span>
        );
      default:
        return (
          <span className="badge badge-neutral" style={{ fontSize: '0.65rem' }}>
            Pending
          </span>
        );
    }
  };

  return (
    <div className="glass-card" id="transactions-section">
      {/* Table Toolbar */}
      <div className="toolbar-card">
        <div className="search-input-wrap">
          <Search size={15} className="search-icon-slot" />
          <input
            id="table-search-input"
            type="text"
            placeholder="Search by Txn ID, customer (C101), merchant, or location..."
            value={searchTerm}
            onChange={(e) => {
              setSearchTerm(e.target.value);
              setPage(1);
            }}
          />
        </div>

        <div className="filter-pills" id="table-filter-pills">
          <button
            id="filter-all"
            className={`filter-btn ${statusFilter === 'ALL' ? 'active' : ''}`}
            onClick={() => {
              setStatusFilter('ALL');
              setPage(1);
            }}
          >
            All ({transactions.length})
          </button>
          <button
            id="filter-triggered"
            className={`filter-btn ${statusFilter === 'TRIGGERED' ? 'active' : ''}`}
            onClick={() => {
              setStatusFilter('TRIGGERED');
              setPage(1);
            }}
          >
            Triggered Anomalies
          </button>
          <button
            id="filter-mitigated"
            className={`filter-btn ${statusFilter === 'MITIGATED' ? 'active' : ''}`}
            onClick={() => {
              setStatusFilter('MITIGATED');
              setPage(1);
            }}
          >
            Mitigated Profiles
          </button>
          <button
            id="filter-normal"
            className={`filter-btn ${statusFilter === 'NORMAL' ? 'active' : ''}`}
            onClick={() => {
              setStatusFilter('NORMAL');
              setPage(1);
            }}
          >
            Clean Evaluated
          </button>
          <button
            id="filter-reviewed"
            className={`filter-btn ${statusFilter === 'REVIEWED' ? 'active' : ''}`}
            onClick={() => {
              setStatusFilter('REVIEWED');
              setPage(1);
            }}
          >
            Reviewed
          </button>
        </div>
      </div>

      {/* Table Data */}
      <div className="table-wrapper">
        <table className="data-table" id="transactions-data-table">
          <thead>
            <tr>
              <th onClick={() => handleSort('transaction_id')} style={{ cursor: 'pointer' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                  <span>Transaction ID</span>
                  <ArrowUpDown size={12} />
                </div>
              </th>
              <th onClick={() => handleSort('timestamp')} style={{ cursor: 'pointer' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                  <span>Timestamp</span>
                  <ArrowUpDown size={12} />
                </div>
              </th>
              <th onClick={() => handleSort('customer_id')} style={{ cursor: 'pointer' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                  <span>Customer</span>
                  <ArrowUpDown size={12} />
                </div>
              </th>
              <th onClick={() => handleSort('amount')} style={{ cursor: 'pointer' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                  <span>Amount (INR)</span>
                  <ArrowUpDown size={12} />
                </div>
              </th>
              <th>Merchant</th>
              <th>Location & Channel</th>
              <th>Rule Engine Signals</th>
              <th>Review Status</th>
              <th style={{ textAlign: 'right' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {paginatedTransactions.length === 0 ? (
              <tr>
                <td colSpan={9} style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
                  No transactions match the selected filters.
                </td>
              </tr>
            ) : (
              paginatedTransactions.map((txn) => {
                const txnId = txn.transaction_id;
                const fullAnalyzed = analyzedMap[txnId] || { transaction: txn };

                return (
                  <tr
                    key={txnId}
                    id={`txn-row-${txnId}`}
                    onClick={() => onSelectTransaction(fullAnalyzed)}
                  >
                    <td className="mono-cell" style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                      {txnId}
                    </td>
                    <td style={{ fontSize: '0.775rem', color: 'var(--text-secondary)' }}>
                      {new Date(txn.timestamp).toLocaleString('en-IN', {
                        month: 'short',
                        day: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </td>
                    <td className="mono-cell">
                      <span
                        style={{
                          background: 'rgba(99, 102, 241, 0.12)',
                          color: '#818cf8',
                          padding: '0.2rem 0.5rem',
                          borderRadius: 'var(--radius-sm)',
                          fontWeight: 700,
                        }}
                      >
                        {txn.customer_id}
                      </span>
                    </td>
                    <td className="amount-cell">
                      ₹{(parseFloat(txn.amount) || 0).toLocaleString('en-IN', {
                        minimumFractionDigits: 2,
                        maximumFractionDigits: 2,
                      })}
                    </td>
                    <td style={{ fontWeight: 500 }}>{txn.merchant}</td>
                    <td>
                      <div style={{ display: 'flex', flexDirection: 'column' }}>
                        <span style={{ fontSize: '0.8rem', color: 'var(--text-primary)' }}>
                          {txn.location_name}
                        </span>
                        <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                          {txn.channel} • {txn.transaction_type}
                        </span>
                      </div>
                    </td>
                    <td>{renderRuleBadges(txn)}</td>
                    <td>{renderReviewBadge(txnId)}</td>
                    <td style={{ textAlign: 'right' }}>
                      <button
                        className="btn btn-secondary btn-sm"
                        id={`inspect-btn-${txnId}`}
                        onClick={(e) => {
                          e.stopPropagation();
                          onSelectTransaction(fullAnalyzed);
                        }}
                        title="Open explainability & review panel"
                      >
                        <Eye size={13} />
                        <span>Inspect</span>
                      </button>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination Footer */}
      <div
        style={{
          padding: '0.85rem 1.25rem',
          borderTop: '1px solid var(--border-subtle)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          fontSize: '0.775rem',
          color: 'var(--text-muted)',
        }}
      >
        <div>
          Showing {paginatedTransactions.length} of {sortedTransactions.length} transactions
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <button
            className="btn btn-secondary btn-sm"
            disabled={page <= 1}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            id="table-prev-page-btn"
          >
            Previous
          </button>
          <span>
            Page {page} of {totalPages}
          </span>
          <button
            className="btn btn-secondary btn-sm"
            disabled={page >= totalPages}
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            id="table-next-page-btn"
          >
            Next
          </button>
        </div>
      </div>
    </div>
  );
}
