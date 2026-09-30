import React from 'react';
import { ShieldCheck, PlusCircle, RefreshCw, Activity, Terminal } from 'lucide-react';

export default function Header({
  backendOnline,
  onOpenNewModal,
  onRefresh,
  loading,
}) {
  return (
    <header className="app-header">
      <div className="header-container">
        <div className="logo-brand">
          <div className="logo-icon" id="brand-logo-icon">
            <ShieldCheck size={22} color="#ffffff" />
          </div>
          <div className="logo-text">
            <h1>Argus Fraud Shield</h1>
            <span>Hybrid Explainable Fraud Risk & Review Intelligence</span>
          </div>
        </div>

        <div className="header-actions">
          <div className="system-status-pill" id="system-status-pill">
            <span className={`pulse-dot ${backendOnline ? '' : 'offline'}`} />
            <span>
              {backendOnline ? 'FastAPI & Rules Online' : 'Connecting to API...'}
            </span>
          </div>

          <button
            id="refresh-transactions-btn"
            className="btn btn-secondary btn-sm"
            onClick={onRefresh}
            disabled={loading}
            title="Refresh database records"
          >
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            <span>Refresh</span>
          </button>

          <button
            id="open-new-transaction-btn"
            className="btn btn-primary"
            onClick={onOpenNewModal}
          >
            <PlusCircle size={16} />
            <span>New Transaction Analysis</span>
          </button>
        </div>
      </div>
    </header>
  );
}
