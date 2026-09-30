import React, { useState, useEffect, useCallback } from 'react';
import Header from './components/Header';
import MetricCards from './components/MetricCards';
import TransactionTable from './components/TransactionTable';
import NewTransactionModal from './components/NewTransactionModal';
import ReviewDrawer from './components/ReviewDrawer';
import { AlertCircle, CheckCircle2, ShieldAlert, Sparkles, X } from 'lucide-react';

// Fallback initial demonstration transactions in case database query is loading
const INITIAL_DEMO_DATA = [
  {
    transaction_id: 'TXN-DEMO-001',
    customer_id: 'C101',
    amount: 90000.0,
    timestamp: '2026-03-24T15:15:00',
    latitude: 13.0827,
    longitude: 80.2707,
    location_name: 'Chennai, TN',
    merchant: 'Reliance Digital Flagship',
    transaction_type: 'POS',
    channel: 'CREDIT_CARD',
    rule_results: [
      {
        rule_name: 'VelocityRule',
        status: 'NORMAL',
        risk_points: 0.0,
        reason: 'Transaction count (1 txns in 5m, 1 txns in 1h, 1 txns today) is within safe operational thresholds.',
        evidence: {
          transactions_last_5_minutes: 1,
          threshold_5_minutes: 3,
          transactions_last_1_hour: 1,
          threshold_1_hour: 10,
          transactions_today: 1,
          threshold_today: 20,
        },
        mitigation: null,
      },
      {
        rule_name: 'AmountRule',
        status: 'TRIGGERED',
        risk_points: 95.0,
        reason: 'Current transaction amount (₹90,000.00) exceeds historical average by 78.2x (34.5 std deviations).',
        evidence: {
          current_amount: 90000.0,
          historical_average: 1150.2,
          historical_maximum: 2594.83,
          historical_minimum: 150.0,
          historical_std_dev: 680.12,
          amount_deviation: 88849.8,
          multiplier_of_average: 78.25,
          z_score: 34.52,
        },
        mitigation: null,
      },
      {
        rule_name: 'LocationRule',
        status: 'NORMAL',
        risk_points: 0.0,
        reason: 'Movement distance (0.0 km) and implied travel speed (0.0 km/h) are within plausible thresholds.',
        evidence: {
          distance_km: 0.0,
          time_difference_minutes: 120.0,
          implied_speed_kmh: 0.0,
          speed_threshold_kmh: 800.0,
          previous_location: 'Chennai, TN',
          current_location: 'Chennai, TN',
        },
        mitigation: null,
      },
    ],
  },
  {
    transaction_id: 'TXN-DEMO-002',
    customer_id: 'C102',
    amount: 2500.0,
    timestamp: '2026-03-24T09:35:00',
    latitude: 12.9716,
    longitude: 77.5946,
    location_name: 'Indiranagar, Bangalore',
    merchant: 'Taj West End',
    transaction_type: 'POS',
    channel: 'CREDIT_CARD',
    rule_results: [
      {
        rule_name: 'VelocityRule',
        status: 'NORMAL',
        risk_points: 0.0,
        reason: 'Velocity is within safe thresholds.',
        evidence: {
          transactions_last_5_minutes: 1,
          threshold_5_minutes: 3,
        },
        mitigation: null,
      },
      {
        rule_name: 'AmountRule',
        status: 'NORMAL',
        risk_points: 0.0,
        reason: 'Transaction amount conforms with historical spending bounds.',
        evidence: {
          current_amount: 2500.0,
          historical_average: 2450.0,
        },
        mitigation: null,
      },
      {
        rule_name: 'LocationRule',
        status: 'MITIGATED',
        risk_points: 15.0,
        reason: 'Customer C102 is an established multi-city corporate traveler with documented activity across Chennai & Bangalore.',
        evidence: {
          distance_km: 290.4,
          time_difference_minutes: 35.0,
          implied_speed_kmh: 497.8,
          speed_threshold_kmh: 800.0,
          previous_location: 'Chennai, TN',
          current_location: 'Bangalore, KA',
        },
        mitigation: 'C102 whitelisted in verified corporate travel registry with regular Chennai-Bangalore business presence.',
      },
    ],
  },
];

export default function App() {
  const [transactions, setTransactions] = useState([]);
  const [analyzedMap, setAnalyzedMap] = useState({
    'TXN-DEMO-001': {
      transaction: INITIAL_DEMO_DATA[0],
      rule_results: INITIAL_DEMO_DATA[0].rule_results,
      customer_history: { transactions: [] },
    },
    'TXN-DEMO-002': {
      transaction: INITIAL_DEMO_DATA[1],
      rule_results: INITIAL_DEMO_DATA[1].rule_results,
      customer_history: { transactions: [] },
    },
  });
  const [reviews, setReviews] = useState({});
  const [activeTransaction, setActiveTransaction] = useState(null);
  const [isNewModalOpen, setIsNewModalOpen] = useState(false);
  const [backendOnline, setBackendOnline] = useState(false);
  const [loading, setLoading] = useState(false);
  const [toast, setToast] = useState(null);

  // Show Toast
  const triggerToast = (type, title, message) => {
    setToast({ type, title, message });
    setTimeout(() => {
      setToast(null);
    }, 5000);
  };

  // Fetch transactions from FastAPI backend
  const fetchTransactions = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/transactions?limit=100');
      if (res.ok) {
        const data = await res.json();
        const records = data.transactions || [];
        setTransactions(records);
        setBackendOnline(true);
      } else {
        // Fallback demo records if backend endpoint fails
        setBackendOnline(false);
        if (transactions.length === 0) {
          setTransactions(INITIAL_DEMO_DATA);
        }
      }
    } catch (err) {
      console.warn('Backend unavailable, using fallback records:', err);
      setBackendOnline(false);
      if (transactions.length === 0) {
        setTransactions(INITIAL_DEMO_DATA);
      }
    } finally {
      setLoading(false);
    }
  }, [transactions.length]);

  useEffect(() => {
    fetchTransactions();
    // Poll backend health every 15 seconds
    const interval = setInterval(() => {
      fetch('/health')
        .then((r) => r.ok && setBackendOnline(true))
        .catch(() => setBackendOnline(false));
    }, 15000);
    return () => clearInterval(interval);
  }, [fetchTransactions]);

  // Handle new transaction evaluation result from NewTransactionModal
  const handleTransactionAnalyzed = (response) => {
    const txn = response.transaction;
    const ruleResults = response.rule_results || [];

    // Store in analyzed map for quick explainability lookup
    setAnalyzedMap((prev) => ({
      ...prev,
      [txn.transaction_id]: response,
    }));

    // Prepend to transaction stream
    setTransactions((prev) => [
      txn,
      ...prev.filter((t) => t.transaction_id !== txn.transaction_id),
    ]);

    // Open detail review drawer immediately
    setActiveTransaction(response);

    // Trigger feedback notification
    const triggered = ruleResults.filter((r) => r.status === 'TRIGGERED');
    const mitigated = ruleResults.filter((r) => r.status === 'MITIGATED');

    if (triggered.length > 0) {
      triggerToast(
        'danger',
        `Anomaly Flagged (${triggered.length} Rules)`,
        `Transaction ${txn.transaction_id} triggered ${triggered.map((r) => r.rule_name).join(', ')}!`
      );
    } else if (mitigated.length > 0) {
      triggerToast(
        'info',
        'Profile Exception Mitigated',
        `Transaction ${txn.transaction_id} matched customer whitelist: ${mitigated[0].mitigation}`
      );
    } else {
      triggerToast(
        'success',
        'Clean Evaluation',
        `Transaction ${txn.transaction_id} passed all rules safely.`
      );
    }
  };

  // Handle human review submission
  const handleSaveReview = (txnId, reviewData) => {
    setReviews((prev) => ({
      ...prev,
      [txnId]: reviewData,
    }));

    triggerToast(
      'success',
      'Review Decision Recorded',
      `${txnId} marked as ${reviewData.status} by analyst.`
    );
  };

  // Extract analyzed items for MetricCards
  const analyzedTransactionsList = Object.values(analyzedMap);

  return (
    <div className="app-layout" id="fraud-shield-root">
      {/* Top Application Navigation */}
      <Header
        backendOnline={backendOnline}
        onOpenNewModal={() => setIsNewModalOpen(true)}
        onRefresh={fetchTransactions}
        loading={loading}
      />

      {/* Notification Toast */}
      {toast && (
        <div
          id="toast-notification"
          style={{
            position: 'fixed',
            top: '80px',
            right: '24px',
            zIndex: 60,
            background:
              toast.type === 'danger'
                ? '#1e111a'
                : toast.type === 'info'
                ? '#081a24'
                : '#0b1d19',
            border: `1px solid ${
              toast.type === 'danger'
                ? 'rgba(244, 63, 94, 0.4)'
                : toast.type === 'info'
                ? 'rgba(6, 182, 212, 0.4)'
                : 'rgba(16, 185, 129, 0.4)'
            }`,
            borderRadius: 'var(--radius-md)',
            padding: '0.85rem 1.25rem',
            boxShadow: 'var(--shadow-lg)',
            display: 'flex',
            alignItems: 'center',
            gap: '0.75rem',
            maxWidth: '420px',
            animation: 'fadeIn 0.2s ease-out',
          }}
        >
          {toast.type === 'danger' && <AlertCircle size={20} color="#f43f5e" />}
          {toast.type === 'info' && <ShieldAlert size={20} color="#06b6d4" />}
          {toast.type === 'success' && <CheckCircle2 size={20} color="#10b981" />}

          <div style={{ flex: 1 }}>
            <div style={{ fontWeight: 700, fontSize: '0.825rem', color: '#ffffff' }}>
              {toast.title}
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
              {toast.message}
            </div>
          </div>

          <button
            onClick={() => setToast(null)}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--text-muted)',
              cursor: 'pointer',
            }}
          >
            <X size={14} />
          </button>
        </div>
      )}

      {/* Main Content Area */}
      <main className="main-content">
        {/* Metric Cards Banner */}
        <MetricCards
          transactions={transactions}
          analyzedTransactions={analyzedTransactionsList}
        />

        {/* Real-time Transactions Table */}
        <TransactionTable
          transactions={transactions}
          analyzedMap={analyzedMap}
          reviews={reviews}
          onSelectTransaction={(txnData) => setActiveTransaction(txnData)}
        />
      </main>

      {/* New Transaction Processing & Presets Modal */}
      <NewTransactionModal
        isOpen={isNewModalOpen}
        onClose={() => setIsNewModalOpen(false)}
        onSubmitSuccess={handleTransactionAnalyzed}
      />

      {/* Transaction Details & Human Review Slide-out Drawer */}
      {activeTransaction && (
        <ReviewDrawer
          transaction={activeTransaction}
          currentReview={
            reviews[
              activeTransaction.transaction_id ||
                activeTransaction.transaction?.transaction_id
            ]
          }
          onClose={() => setActiveTransaction(null)}
          onSaveReview={handleSaveReview}
        />
      )}
    </div>
  );
}
