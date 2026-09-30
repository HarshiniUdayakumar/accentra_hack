import React from 'react';
import { Gauge, Clock, IndianRupee, MapPin, ShieldCheck, AlertOctagon, CheckCircle2, Info } from 'lucide-react';

const RULE_CONFIG = {
  VelocityRule: {
    title: 'Velocity Anomaly Rule',
    icon: Clock,
    color: '#818cf8',
    description: 'Monitors transaction frequency across rolling 5-minute, 1-hour, and daily windows.',
  },
  AmountRule: {
    title: 'Unusual Amount Rule',
    icon: IndianRupee,
    color: '#ec4899',
    description: 'Compares transaction value against customer historical spending average, maximum, and statistical bounds.',
  },
  LocationRule: {
    title: 'Geographical Movement Rule',
    icon: MapPin,
    color: '#06b6d4',
    description: 'Calculates Haversine distance, elapsed time, and implied physical travel speed between consecutive locations.',
  },
};

const FORMAT_LABELS = {
  transactions_last_5_minutes: 'Txns (Last 5m)',
  threshold_5_minutes: '5m Threshold',
  transactions_last_1_hour: 'Txns (Last 1h)',
  threshold_1_hour: '1h Threshold',
  transactions_today: 'Txns Today',
  threshold_today: 'Today Threshold',
  current_amount: 'Amount',
  historical_average: 'Hist. Average',
  historical_maximum: 'Hist. Maximum',
  historical_minimum: 'Hist. Minimum',
  historical_std_dev: 'Hist. Std Dev',
  amount_deviation: 'Amount Deviation',
  multiplier_of_average: 'Multiplier',
  z_score: 'Z-Score',
  distance_km: 'Distance',
  time_difference_minutes: 'Elapsed Time',
  implied_speed_kmh: 'Implied Speed',
  speed_threshold_kmh: 'Speed Limit',
  previous_location: 'Previous Location',
  current_location: 'Current Location',
};

export default function RuleCard({ ruleResult }) {
  if (!ruleResult) return null;

  const {
    rule_name,
    status = 'NORMAL',
    risk_points = 0.0,
    reason = '',
    evidence = {},
    mitigation = null,
  } = ruleResult;

  const config = RULE_CONFIG[rule_name] || {
    title: rule_name,
    icon: Gauge,
    color: '#94a3b8',
    description: 'Rule evaluation',
  };

  const IconComponent = config.icon;

  const getStatusBadge = () => {
    switch (status) {
      case 'TRIGGERED':
        return (
          <span className="badge badge-triggered" id={`badge-${rule_name}`}>
            <AlertOctagon size={12} />
            TRIGGERED
          </span>
        );
      case 'MITIGATED':
        return (
          <span className="badge badge-mitigated" id={`badge-${rule_name}`}>
            <ShieldCheck size={12} />
            MITIGATED
          </span>
        );
      case 'NORMAL':
      default:
        return (
          <span className="badge badge-normal" id={`badge-${rule_name}`}>
            <CheckCircle2 size={12} />
            NORMAL
          </span>
        );
    }
  };

  // Filter out nested object details for cleaner evidence pills
  const evidenceEntries = Object.entries(evidence).filter(
    ([k, v]) =>
      typeof v !== 'object' &&
      !['error', 'customer_id', 'threshold'].includes(k)
  );

  return (
    <div
      className={`rule-card ${status.toLowerCase()}`}
      id={`rule-card-${rule_name}`}
    >
      <div className="rule-header">
        <div className="rule-title-group">
          <div
            className="metric-icon-box"
            style={{ background: 'rgba(255, 255, 255, 0.05)', color: config.color }}
          >
            <IconComponent size={16} />
          </div>
          <div>
            <div className="rule-name">{config.title}</div>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
              {rule_name}
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
          <div
            className="risk-points-pill"
            style={{
              color:
                risk_points > 50
                  ? '#fb7185'
                  : risk_points > 0
                  ? '#67e8f9'
                  : '#94a3b8',
            }}
          >
            {risk_points.toFixed(1)} pts
          </div>
          {getStatusBadge()}
        </div>
      </div>

      <div className="rule-reason">{reason}</div>

      {/* Mitigation Banner if applied */}
      {mitigation && (
        <div className="mitigation-banner" id={`mitigation-${rule_name}`}>
          <ShieldCheck size={16} style={{ flexShrink: 0, marginTop: '2px' }} />
          <div>
            <strong>Legitimate Exception Mitigated:</strong> {mitigation}
          </div>
        </div>
      )}

      {/* Numerical Evidence Breakdown */}
      {evidenceEntries.length > 0 && (
        <div className="evidence-box">
          {evidenceEntries.map(([key, val]) => {
            let displayVal = val;
            if (typeof val === 'number') {
              if (['current_amount', 'historical_average', 'historical_maximum', 'historical_minimum', 'amount_deviation'].includes(key)) {
                displayVal = `₹${val.toLocaleString('en-IN', { maximumFractionDigits: 2 })}`;
              } else if (key === 'distance_km') {
                displayVal = `${val.toFixed(1)} km`;
              } else if (key === 'implied_speed_kmh') {
                displayVal = `${val.toFixed(1)} km/h`;
              } else if (key === 'time_difference_minutes') {
                displayVal = `${val.toFixed(1)} min`;
              } else if (key === 'multiplier_of_average') {
                displayVal = `${val.toFixed(2)}x`;
              } else if (key === 'z_score') {
                displayVal = `${val.toFixed(2)}σ`;
              }
            }

            return (
              <div key={key} className="evidence-item">
                <span className="evidence-label">
                  {FORMAT_LABELS[key] || key.replace(/_/g, ' ')}
                </span>
                <span className="evidence-value">{String(displayVal)}</span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
