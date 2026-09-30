import React, { useState } from 'react';
import { X, Sparkles, Send, ShieldAlert, AlertTriangle, CheckCircle, RefreshCw } from 'lucide-react';

const PRESETS = [
  {
    id: 'preset-normal',
    name: '1. Normal (C101)',
    description: 'Typical spending: ₹850 in Chennai, consistent with history',
    badge: 'NORMAL',
    data: {
      transaction_id: `TXN-NORM-${Date.now().toString().slice(-6)}`,
      customer_id: 'C101',
      amount: 850.0,
      timestamp: '2026-03-24T14:30:00',
      latitude: 13.0827,
      longitude: 80.2707,
      location_name: 'Chennai, TN',
      merchant: 'Swiggy Food',
      transaction_type: 'PAYMENT',
      channel: 'UPI',
    },
  },
  {
    id: 'preset-high-amount',
    name: '2. High Amount (C101)',
    description: '₹90,000 electronics purchase (78x avg ₹1,150) -> AmountRule TRIGGERED',
    badge: 'AMOUNT SPIKE',
    data: {
      transaction_id: `TXN-AMT-${Date.now().toString().slice(-6)}`,
      customer_id: 'C101',
      amount: 90000.0,
      timestamp: '2026-03-24T15:15:00',
      latitude: 13.0827,
      longitude: 80.2707,
      location_name: 'Chennai, TN',
      merchant: 'Reliance Digital Flagship',
      transaction_type: 'POS',
      channel: 'CREDIT_CARD',
    },
  },
  {
    id: 'preset-velocity',
    name: '3. Rapid Velocity (C101)',
    description: 'Rapid transactions within 2 minutes -> VelocityRule TRIGGERED',
    badge: 'VELOCITY SPIKE',
    data: {
      transaction_id: `TXN-VEL-${Date.now().toString().slice(-6)}`,
      customer_id: 'C101',
      amount: 450.0,
      timestamp: '2026-03-24T10:02:00',
      latitude: 13.0827,
      longitude: 80.2707,
      location_name: 'Chennai, TN',
      merchant: 'QuickPay Recharge',
      transaction_type: 'PAYMENT',
      channel: 'UPI',
    },
  },
  {
    id: 'preset-impossible-travel',
    name: '4. Impossible Travel (C101)',
    description: 'Delhi 20 mins after Chennai (1,760 km at ~5,280 km/h) -> LocationRule TRIGGERED',
    badge: 'LOCATION SPIKE',
    data: {
      transaction_id: `TXN-LOC-${Date.now().toString().slice(-6)}`,
      customer_id: 'C101',
      amount: 1200.0,
      timestamp: '2026-03-24T10:20:00',
      latitude: 28.6139,
      longitude: 77.209,
      location_name: 'Connaught Place, New Delhi',
      merchant: 'Delhi Duty Free',
      transaction_type: 'POS',
      channel: 'DEBIT_CARD',
    },
  },
  {
    id: 'preset-multi-location',
    name: '5. Multi-Location Mitigated (C102)',
    description: 'C102 Bangalore 35m after Chennai (whitelisted traveler) -> Location MITIGATED',
    badge: 'MITIGATED EXCEPTION',
    data: {
      transaction_id: `TXN-MIT-${Date.now().toString().slice(-6)}`,
      customer_id: 'C102',
      amount: 2500.0,
      timestamp: '2026-03-24T09:35:00',
      latitude: 12.9716,
      longitude: 77.5946,
      location_name: 'Indiranagar, Bangalore',
      merchant: 'Taj West End',
      transaction_type: 'POS',
      channel: 'CREDIT_CARD',
    },
  },
];

export default function NewTransactionModal({
  isOpen,
  onClose,
  onSubmitSuccess,
}) {
  if (!isOpen) return null;

  const [formData, setFormData] = useState({
    transaction_id: `TXN-${Date.now().toString().slice(-6)}`,
    customer_id: 'C101',
    amount: 1200.0,
    timestamp: new Date().toISOString().slice(0, 19),
    latitude: 13.0827,
    longitude: 80.2707,
    location_name: 'Chennai, TN',
    merchant: 'Amazon India',
    transaction_type: 'PAYMENT',
    channel: 'UPI',
  });

  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  const handleApplyPreset = (preset) => {
    setFormData({
      ...preset.data,
      transaction_id: `TXN-${preset.data.customer_id}-${Date.now().toString().slice(-5)}`,
    });
    setErrorMsg('');
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: ['amount', 'latitude', 'longitude'].includes(name)
        ? parseFloat(value) || 0
        : value,
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setErrorMsg('');

    try {
      const payload = {
        ...formData,
        amount: Number(formData.amount),
        latitude: Number(formData.latitude),
        longitude: Number(formData.longitude),
      };

      const res = await fetch('/api/transactions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        throw new Error(
          errorData.detail || `Server returned error ${res.status}: ${res.statusText}`
        );
      }

      const data = await res.json();
      onSubmitSuccess(data);
      onClose();
    } catch (err) {
      setErrorMsg(err.message || 'Failed to submit transaction to backend.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div
        className="modal-dialog"
        id="new-transaction-modal-dialog"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <Sparkles size={18} color="#818cf8" />
            <h2 id="modal-title">New Transaction Analysis</h2>
          </div>
          <button
            className="btn btn-secondary btn-sm"
            onClick={onClose}
            id="close-modal-btn"
          >
            <X size={16} />
          </button>
        </div>

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column' }}>
          <div className="modal-body">
            {/* Quick Test Presets Bar */}
            <div className="presets-container" id="presets-container">
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                }}
              >
                <span
                  style={{
                    fontSize: '0.725rem',
                    fontWeight: 700,
                    textTransform: 'uppercase',
                    color: 'var(--text-muted)',
                  }}
                >
                  Quick Test Presets (Rule & Mitigation Demos)
                </span>
                <span style={{ fontSize: '0.7rem', color: 'var(--accent-primary)' }}>
                  Click to populate
                </span>
              </div>

              <div className="preset-buttons">
                {PRESETS.map((p) => (
                  <button
                    key={p.id}
                    type="button"
                    className="btn-preset"
                    id={p.id}
                    title={p.description}
                    onClick={() => handleApplyPreset(p)}
                  >
                    {p.name}
                  </button>
                ))}
              </div>
            </div>

            {errorMsg && (
              <div
                style={{
                  padding: '0.75rem 1rem',
                  borderRadius: 'var(--radius-md)',
                  background: 'rgba(244, 63, 94, 0.15)',
                  border: '1px solid rgba(244, 63, 94, 0.35)',
                  color: '#fb7185',
                  fontSize: '0.8rem',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                }}
              >
                <AlertTriangle size={16} />
                <span>{errorMsg}</span>
              </div>
            )}

            {/* Form Fields */}
            <div className="form-grid">
              <div className="form-group">
                <label htmlFor="input-transaction-id">Transaction ID</label>
                <input
                  id="input-transaction-id"
                  name="transaction_id"
                  type="text"
                  required
                  value={formData.transaction_id}
                  onChange={handleChange}
                />
              </div>

              <div className="form-group">
                <label htmlFor="input-customer-id">Customer ID</label>
                <select
                  id="input-customer-id"
                  name="customer_id"
                  value={formData.customer_id}
                  onChange={handleChange}
                >
                  <option value="C101">C101 (Baseline Consumer - 35 txns)</option>
                  <option value="C102">C102 (Multi-Location Whitelisted)</option>
                  <option value="C103">C103 (Active Consumer)</option>
                  <option value="C104">C104 (Active Consumer)</option>
                  <option value="C105">C105 (Active Consumer)</option>
                </select>
              </div>

              <div className="form-group">
                <label htmlFor="input-amount">Amount (INR ₹)</label>
                <input
                  id="input-amount"
                  name="amount"
                  type="number"
                  step="0.01"
                  required
                  value={formData.amount}
                  onChange={handleChange}
                />
              </div>

              <div className="form-group">
                <label htmlFor="input-timestamp">Timestamp (ISO 8601)</label>
                <input
                  id="input-timestamp"
                  name="timestamp"
                  type="text"
                  required
                  value={formData.timestamp}
                  onChange={handleChange}
                  placeholder="YYYY-MM-DDTHH:MM:SS"
                />
              </div>

              <div className="form-group">
                <label htmlFor="input-location-name">Location Name</label>
                <input
                  id="input-location-name"
                  name="location_name"
                  type="text"
                  required
                  value={formData.location_name}
                  onChange={handleChange}
                />
              </div>

              <div className="form-group">
                <label htmlFor="input-merchant">Merchant Name</label>
                <input
                  id="input-merchant"
                  name="merchant"
                  type="text"
                  required
                  value={formData.merchant}
                  onChange={handleChange}
                />
              </div>

              <div className="form-group">
                <label htmlFor="input-latitude">Latitude</label>
                <input
                  id="input-latitude"
                  name="latitude"
                  type="number"
                  step="0.0001"
                  required
                  value={formData.latitude}
                  onChange={handleChange}
                />
              </div>

              <div className="form-group">
                <label htmlFor="input-longitude">Longitude</label>
                <input
                  id="input-longitude"
                  name="longitude"
                  type="number"
                  step="0.0001"
                  required
                  value={formData.longitude}
                  onChange={handleChange}
                />
              </div>

              <div className="form-group">
                <label htmlFor="input-channel">Channel</label>
                <select
                  id="input-channel"
                  name="channel"
                  value={formData.channel}
                  onChange={handleChange}
                >
                  <option value="UPI">UPI</option>
                  <option value="CREDIT_CARD">CREDIT_CARD</option>
                  <option value="DEBIT_CARD">DEBIT_CARD</option>
                  <option value="NET_BANKING">NET_BANKING</option>
                </select>
              </div>

              <div className="form-group">
                <label htmlFor="input-txn-type">Transaction Type</label>
                <select
                  id="input-txn-type"
                  name="transaction_type"
                  value={formData.transaction_type}
                  onChange={handleChange}
                >
                  <option value="PAYMENT">PAYMENT</option>
                  <option value="POS">POS</option>
                  <option value="TRANSFER">TRANSFER</option>
                  <option value="ATM_WITHDRAWAL">ATM_WITHDRAWAL</option>
                </select>
              </div>
            </div>
          </div>

          <div className="modal-footer">
            <button
              type="button"
              className="btn btn-secondary"
              onClick={onClose}
              disabled={loading}
              id="cancel-modal-btn"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={loading}
              id="submit-transaction-btn"
            >
              {loading ? (
                <>
                  <RefreshCw size={14} className="animate-spin" />
                  <span>Evaluating Rules...</span>
                </>
              ) : (
                <>
                  <Send size={14} />
                  <span>Process & Analyze</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
