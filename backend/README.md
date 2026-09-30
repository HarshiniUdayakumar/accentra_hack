# Hybrid Explainable Fraud Risk Detection & Review Platform - Backend

This backend provides a modular FastAPI architecture for hybrid fraud risk detection combining rule-based heuristics and behavioral anomaly detection (Isolation Forest).

## Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                     # FastAPI application entry point
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes/                 # API route handlers
│   │       └── __init__.py
│   ├── database/                   # Database connection and sessions
│   │   ├── __init__.py
│   │   └── connection.py
│   ├── models/                     # Data and domain models
│   │   └── __init__.py
│   ├── schemas/                    # Pydantic validation schemas
│   │   └── __init__.py
│   ├── rules/                      # Modular rule engine
│   │   ├── __init__.py
│   │   ├── base.py                 # Abstract BaseRule & RuleResult interfaces
│   │   ├── velocity.py             # VelocityRule component
│   │   ├── amount.py               # AmountRule component
│   │   ├── location.py             # LocationRule component
│   │   └── engine.py               # RuleEngine runner
│   ├── ml/                         # ML models module
│   │   ├── __init__.py
│   │   └── anomaly.py              # Isolation Forest detector placeholder
│   └── services/                   # Business and orchestration services
│       ├── __init__.py
│       ├── transaction_service.py  # Ingestion & evaluation orchestration
│       └── risk_fusion.py          # Rule + ML score fusion & explainability
├── .env
├── .env.example
├── requirements.txt
└── README.md
```

## Modular Rule Engine Architecture

The rule engine strictly decouples individual detection rules from the execution engine:
- `BaseRule` (`app/rules/base.py`) defines the contract (`evaluate(transaction, context) -> RuleResult`).
- Concrete rules (`VelocityRule`, `AmountRule`, `LocationRule`) encapsulate their own logic and thresholds.
- `RuleEngine` (`app/rules/engine.py`) orchestrates registration and execution across rules without knowing their internal heuristics.
- Future rules (e.g., `DeviceRule`, `MerchantRule`) can be plugged in by subclassing `BaseRule` and registering with `RuleEngine.register_rule()`.

## Running the Server

Activate the virtual environment and start Uvicorn:

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- API Root: http://127.0.0.1:8000
- Health Check: http://127.0.0.1:8000/health
- Interactive Docs (Swagger UI): http://127.0.0.1:8000/docs
