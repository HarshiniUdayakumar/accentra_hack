import React from 'react';
import { Activity, AlertTriangle, ShieldCheck, CheckCircle2, IndianRupee } from 'lucide-react';

export default function MetricCards({ transactions = [], analyzedTransactions = [] }) {
  const allTxns = [...analyzedTransactions, ...transactions];

  const totalCount = allTxns.length;
  const totalVolume = allTxns.reduce((acc, t) => acc + (parseFloat(t.amount) || 0), 0);

  // Count alerts
  let triggeredCount = 0;
  let mitigatedCount = 0;

  analyzedTransactions.forEach((t) => {
    const rules = t.rule_results || [];
    const hasTriggered = rules.some((r) => r.status === 'TRIGGERED');
    const hasMitigated = rules.some((r) => r.status === 'MITIGATED');

    if (hasTriggered) triggeredCount++;
    else if (hasMitigated) mitigatedCount++;
  });

  return (
    <div className="metrics-grid" id="dashboard-metrics-grid">
      {/* Total Volume */}
      <div className="glass-card metric-card alert-primary" id="metric-total-volume">
        <div className="metric-header">
          <span>Total Monitored Volume</span>
          <div className="metric-icon-box">
            <IndianRupee size={16} color="#818cf8" />
          </div>
        </div>
        <div className="metric-value">
          ₹{totalVolume.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
        </div>
        <div className="metric-footer">
          <span>Across {totalCount} monitored transactions</span>
        </div>
      </div>

      {/* Total Records */}
      <div className="glass-card metric-card alert-normal" id="metric-total-txns">
        <div className="metric-header">
          <span>Monitored Transactions</span>
          <div className="metric-icon-box">
            <Activity size={16} color="#34d399" />
          </div>
        </div>
        <div className="metric-value">{totalCount.toLocaleString()}</div>
        <div className="metric-footer">
          <span>Historical & Live API Stream</span>
        </div>
      </div>

      {/* Triggered Anomalies */}
      <div className="glass-card metric-card alert-high" id="metric-triggered-alerts">
        <div className="metric-header">
          <span>High Risk Anomaly Signals</span>
          <div className="metric-icon-box">
            <AlertTriangle size={16} color="#f43f5e" />
          </div>
        </div>
        <div className="metric-value" style={{ color: '#fb7185' }}>
          {triggeredCount}
        </div>
        <div className="metric-footer">
          <span>Velocity, Amount, or Location triggered</span>
        </div>
      </div>

      {/* Mitigated Exceptions */}
      <div className="glass-card metric-card alert-mitigated" id="metric-mitigated-exceptions">
        <div className="metric-header">
          <span>Mitigated Profile Exceptions</span>
          <div className="metric-icon-box">
            <ShieldCheck size={16} color="#06b6d4" />
          </div>
        </div>
        <div className="metric-value" style={{ color: '#67e8f9' }}>
          {mitigatedCount}
        </div>
        <div className="metric-footer">
          <span>Known multi-location business travelers</span>
        </div>
      </div>
    </div>
  );
}
