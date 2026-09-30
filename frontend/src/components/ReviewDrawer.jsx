import React, { useState } from 'react';
import {
  X,
  User,
  MapPin,
  Calendar,
  CreditCard,
  Building,
  CheckCircle,
  AlertTriangle,
  XCircle,
  Shield,
  Clock,
  History,
  Send,
} from 'lucide-react';
import RuleCard from './RuleCard';

export default function ReviewDrawer({
  transaction,
  onClose,
  onSaveReview,
  currentReview,
}) {
  if (!transaction) return null;

  const [decision, setDecision] = useState(currentReview?.status || 'PENDING');
  const [analystNotes, setAnalystNotes] = useState(currentReview?.notes || '');
  const [savedSuccess, setSavedSuccess] = useState(false);

  const txn = transaction.transaction || transaction;
  const history = transaction.customer_history?.transactions || [];
  const rules = transaction.rule_results || [];

  const handleDecisionSubmit = (status) => {
    setDecision(status);
    const reviewData = {
      status,
      notes: analystNotes,
      reviewedAt: new Date().toISOString(),
      analyst: 'Security Analyst (Tier 2)',
    };
    onSaveReview(txn.transaction_id, reviewData);
    setSavedSuccess(true);
    setTimeout(() => setSavedSuccess(false), 2500);
  };

  const getStatusBadge = (status) => {
    switch (status) {
      case 'APPROVED':
        return (
          <span className="badge badge-normal">
            <CheckCircle size={12} /> Approved
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
            }}
          >
            <AlertTriangle size={12} /> Escalated
          </span>
        );
      case 'DECLINED':
        return (
          <span className="badge badge-triggered">
            <XCircle size={12} /> Declined
          </span>
        );
      default:
        return (
          <span className="badge badge-neutral">
            <Clock size={12} /> Pending Review
          </span>
        );
    }
  };

  return (
    <div className="drawer-overlay" onClick={onClose}>
      <div
        className="drawer-panel"
        id="transaction-review-drawer"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Drawer Header */}
        <div className="drawer-header">
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
              <h2 style={{ fontSize: '1.15rem', fontWeight: 800 }}>
                {txn.transaction_id}
              </h2>
              {getStatusBadge(decision)}
            </div>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Evaluated on {new Date(txn.timestamp).toLocaleString()}
            </span>
          </div>

          <button
            className="btn btn-secondary btn-sm"
            onClick={onClose}
            id="close-drawer-btn"
          >
            <X size={16} />
          </button>
        </div>

        {/* Drawer Content */}
        <div className="drawer-content">
          {/* Quick Summary Card */}
          <div className="glass-card" style={{ padding: '1.25rem' }}>
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'flex-start',
                marginBottom: '1rem',
              }}
            >
              <div>
                <span
                  style={{
                    fontSize: '0.725rem',
                    textTransform: 'uppercase',
                    color: 'var(--text-muted)',
                    fontWeight: 600,
                  }}
                >
                  Transaction Amount
                </span>
                <div
                  style={{
                    fontSize: '2rem',
                    fontWeight: 800,
                    fontFamily: 'var(--font-mono)',
                    color: '#ffffff',
                  }}
                >
                  ₹{(parseFloat(txn.amount) || 0).toLocaleString('en-IN', {
                    minimumFractionDigits: 2,
                  })}
                </div>
              </div>

              <div style={{ textAlign: 'right' }}>
                <span
                  style={{
                    fontSize: '0.725rem',
                    textTransform: 'uppercase',
                    color: 'var(--text-muted)',
                    fontWeight: 600,
                  }}
                >
                  Customer ID
                </span>
                <div
                  style={{
                    fontSize: '1.15rem',
                    fontWeight: 700,
                    fontFamily: 'var(--font-mono)',
                    color: '#818cf8',
                  }}
                >
                  {txn.customer_id}
                </div>
              </div>
            </div>

            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(2, 1fr)',
                gap: '0.75rem',
                fontSize: '0.8rem',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: 'var(--text-secondary)' }}>
                <Building size={14} color="var(--text-muted)" />
                <span>{txn.merchant}</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: 'var(--text-secondary)' }}>
                <CreditCard size={14} color="var(--text-muted)" />
                <span>
                  {txn.channel} • {txn.transaction_type}
                </span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: 'var(--text-secondary)' }}>
                <MapPin size={14} color="var(--text-muted)" />
                <span>
                  {txn.location_name} ({txn.latitude?.toFixed(2)}, {txn.longitude?.toFixed(2)})
                </span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: 'var(--text-secondary)' }}>
                <History size={14} color="var(--text-muted)" />
                <span>{history.length} Previous Txns</span>
              </div>
            </div>
          </div>

          {/* Human Review Action Box */}
          <div className="human-review-box" id="human-review-panel">
            <div className="human-review-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Shield size={16} color="#818cf8" />
                <span style={{ fontWeight: 700, fontSize: '0.9rem' }}>
                  Analyst Human Review
                </span>
              </div>
              {savedSuccess && (
                <span style={{ fontSize: '0.75rem', color: '#34d399', fontWeight: 600 }}>
                  ✓ Review decision recorded
                </span>
              )}
            </div>

            <div className="review-action-btns">
              <button
                id="btn-review-approve"
                className={`btn btn-sm ${decision === 'APPROVED' ? 'btn-success' : 'btn-secondary'}`}
                onClick={() => handleDecisionSubmit('APPROVED')}
              >
                <CheckCircle size={14} />
                <span>Approve</span>
              </button>

              <button
                id="btn-review-escalate"
                className={`btn btn-sm ${decision === 'ESCALATED' ? 'btn-warning' : 'btn-secondary'}`}
                onClick={() => handleDecisionSubmit('ESCALATED')}
              >
                <AlertTriangle size={14} />
                <span>Escalate</span>
              </button>

              <button
                id="btn-review-decline"
                className={`btn btn-sm ${decision === 'DECLINED' ? 'btn-danger' : 'btn-secondary'}`}
                onClick={() => handleDecisionSubmit('DECLINED')}
              >
                <XCircle size={14} />
                <span>Decline</span>
              </button>
            </div>

            <div className="form-group" style={{ marginTop: '0.4rem' }}>
              <label htmlFor="analyst-notes-input">Analyst Notes & Rationale</label>
              <textarea
                id="analyst-notes-input"
                rows={2}
                placeholder="Enter justification, customer verification confirmation, or fraud notes..."
                value={analystNotes}
                onChange={(e) => setAnalystNotes(e.target.value)}
              />
            </div>
          </div>

          {/* Rule Evidence Breakdown Section */}
          <div>
            <h3
              style={{
                fontSize: '0.85rem',
                textTransform: 'uppercase',
                color: 'var(--text-muted)',
                letterSpacing: '0.05em',
                marginBottom: '0.85rem',
              }}
            >
              Independent Fraud Rule Evidence
            </h3>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
              {rules.length > 0 ? (
                rules.map((rule, idx) => (
                  <RuleCard key={rule.rule_name || idx} ruleResult={rule} />
                ))
              ) : (
                <div
                  className="glass-card"
                  style={{ padding: '1.25rem', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.825rem' }}
                >
                  No rule evaluation signals available for this historical record.
                </div>
              )}
            </div>
          </div>

          {/* Customer Historical Timeline */}
          {history.length > 0 && (
            <div>
              <h3
                style={{
                  fontSize: '0.85rem',
                  textTransform: 'uppercase',
                  color: 'var(--text-muted)',
                  letterSpacing: '0.05em',
                  marginBottom: '0.85rem',
                }}
              >
                Recent Customer History ({history.length} records)
              </h3>

              <div
                className="glass-card"
                style={{ maxHeight: '240px', overflowY: 'auto' }}
              >
                <div style={{ display: 'flex', flexDirection: 'column' }}>
                  {history.slice(0, 10).map((h, i) => (
                    <div
                      key={h.transaction_id || i}
                      style={{
                        padding: '0.65rem 1rem',
                        borderBottom: '1px solid var(--border-subtle)',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        fontSize: '0.775rem',
                      }}
                    >
                      <div>
                        <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                          {h.merchant} • {h.location_name}
                        </div>
                        <div style={{ color: 'var(--text-muted)', fontSize: '0.7rem' }}>
                          {new Date(h.timestamp).toLocaleString()} ({h.channel})
                        </div>
                      </div>

                      <div
                        style={{
                          fontWeight: 700,
                          fontFamily: 'var(--font-mono)',
                          color: '#ffffff',
                        }}
                      >
                        ₹{(parseFloat(h.amount) || 0).toLocaleString('en-IN', {
                          maximumFractionDigits: 2,
                        })}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
