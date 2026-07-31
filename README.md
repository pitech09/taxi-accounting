# Taxi Accounting System

A comprehensive Django web application for managing taxi fleet finances in Lesotho. Supports four operating models (Quota, Salary, Percentage, Contract) with driver/owner portals, settlement approval workflows, integrated cash book, and real-time financial reporting.

**Currency:** Maloti (M), pegged 1:1 with ZAR.

## Features

- **Vehicle Management** – Register vehicles with type, operating model, and financial parameters
- **Driver Management** – Manage drivers with portal access, operating model overrides, and debt tracking
- **Four Operating Models:**
  - **Quota** – Driver pays daily fixed quota; keeps surplus; debt on shortfall
  - **Monthly Salary** – Driver receives fixed salary; owner keeps gross profit
  - **Percentage** – Driver receives percentage of gross income
  - **Contract** – Target-based with success bonus or failure percentage
- **Owner Portal** – Full management (vehicles, drivers, settlements, approvals, cash book, reports, settings)
- **Driver Portal** – Submit settlements, view history, track debt/contract progress, manage profile
- **Cash Book** – Track cash in hand and bank accounts with running balances, automatic settlement collection on approval
- **Approval Workflow** – Drivers submit settlements; owners approve (auto-calculates) or reject
- **Reports** – Daily fleet summary, Monthly P&L, Cash Book Ledger, Bank Reconciliation, Expense Report, Cash Flow Statement, Contract Progress, Tax Report
- **Export** – CSV export for settlements and cash book ledger
- **Charts** – Chart.js visualizations on dashboards and reports
- **REST API** – JSON endpoints for AJAX and external integrations

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | Django 5.0+ (Python 3.13) |
| Database | PostgreSQL (production) / SQLite (dev) |
| Frontend | Django Templates + Bootstrap 5 |
| Charts | Chart.js |
| Reports | CSV (built-in), PDF/Excel (via reportlab/openpyxl) |
| Auth | Django built-in (owner), custom phone+password (driver) |
| Static | WhiteNoise |
| Media | Cloudinary (optional, falls back to local) |
| Server | Gunicorn |

## Quick Start (Development)

### Prerequisites

- Python 3.13+
- pip (Python package manager)

### Setup

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/taxi-accounting.git
cd taxi-accounting

# 2. Create a virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run migrations
python manage.py migrate

# 5. Create a superuser (owner)
python manage.py createsuperuser

# 6. Run the development server
python manage.py runserver

# 7. Open in browser
# Owner portal: http://localhost:8000/accounts/login/
# Driver portal: http://localhost:8000/driver/login/
```

### Seed Data (Optional)

```bash
python manage.py seed_data
```

This creates sample vehicles, drivers, and settlements for testing.

## Project Structure

```
taxi_accounting/
├── manage.py
├── taxiaccounting/          # Django project settings
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── accounts/                # Authentication & system settings
├── vehicles/                # Vehicle models
├── drivers/                 # Driver models
├── settlements/             # Settlement models & forms
├── cashbook/                # Cash book models & views
├── contracts/               # Contract management
├── reports/                 # Report views
├── owner/                   # Owner portal views
├── driver_portal/           # Driver portal views
├── api/                     # REST API endpoints
├── static/                  # Static files (CSS, JS)
├── templates/               # Django templates
│   ├── base.html
│   ├── owner/               # Owner portal templates
│   ├── driver_portal/       # Driver portal templates
│   └── reports/             # Report templates
├── media/                   # User-uploaded media (receipts)
├── requirements.txt
├── Procfile
├── build.sh
├── render.yaml
├── USER_MANUAL.md
└── README.md
```

## Deployment (Render)

### One-Click Deploy

1. Push to GitHub
2. Create a new Web Service on Render
3. Connect your repository
4. Render will auto-detect `render.yaml` and configure the service

### Manual Deploy

1. Create a PostgreSQL database on Render
2. Set the following environment variables:

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | Django secret key (auto-generated) |
| `DEBUG` | Set to `False` in production |
| `ALLOWED_HOSTS` | Comma-separated list of allowed hosts |
| `DATABASE_URL` | PostgreSQL connection string |
| `CLOUDINARY_CLOUD_NAME` | (Optional) Cloudinary cloud name |
| `CLOUDINARY_API_KEY` | (Optional) Cloudinary API key |
| `CLOUDINARY_API_SECRET` | (Optional) Cloudinary API secret |

3. Build command: `./build.sh`
4. Start command: `gunicorn taxiaccounting.wsgi:application --log-file -`

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | `django-insecure-dev-key-...` | Django secret key (change in production) |
| `DEBUG` | `True` | Debug mode (set `False` in production) |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | Comma-separated allowed hosts |
| `DATABASE_URL` | (empty → SQLite) | PostgreSQL connection string |

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/vehicles/` | GET/POST | List/create vehicles |
| `/api/drivers/` | GET/POST | List/create drivers |
| `/api/settlements/` | GET/POST | List/create settlements |
| `/api/contract-summaries/` | GET/POST | List/create contract summaries |
| `/api/vehicle/<id>/details/` | GET | Vehicle details with model parameters |
| `/api/vehicle/<id>/drivers/` | GET | Active drivers for a vehicle |
| `/api/driver/<id>/details/` | GET | Driver details with debt/contract info |
| `/api/driver/<id>/contract/` | GET | Contract progress for a driver |
| `/api/driver/login/` | POST | Driver login API |
| `/api/contract-summary/` | GET | All contract drivers' progress |

## URLs

### Owner Portal (`/owner/`)

| URL | Description |
|-----|-------------|
| `/owner/dashboard/` | Dashboard with summary cards and charts |
| `/owner/vehicles/` | Vehicle list |
| `/owner/vehicles/add/` | Add vehicle |
| `/owner/vehicles/<id>/edit/` | Edit vehicle |
| `/owner/drivers/` | Driver list |
| `/owner/drivers/add/` | Add driver |
| `/owner/drivers/<id>/edit/` | Edit driver |
| `/owner/drivers/<id>/settlements/` | Driver's settlement history |
| `/owner/settlements/` | Settlement list |
| `/owner/settlements/add/` | Add settlement |
| `/owner/approvals/` | Pending approvals |
| `/owner/approvals/<id>/review/` | Approve/reject settlement |
| `/owner/cashbook/` | Cash book dashboard |
| `/owner/cashbook/ledger/` | Transaction ledger |
| `/owner/cashbook/add/` | Add transaction |
| `/owner/contract/` | Contract dashboard |
| `/owner/contract/<id>/settle/` | Month-end contract settlement |
| `/owner/settings/` | System settings |
| `/owner/reports/` | Reports index |

### Driver Portal (`/driver/`)

| URL | Description |
|-----|-------------|
| `/driver/login/` | Driver login |
| `/driver/dashboard/` | Driver dashboard |
| `/driver/settlements/` | Settlement history |
| `/driver/settlements/create/` | Submit new settlement |
| `/driver/settlements/<id>/view/` | View settlement |
| `/driver/settlements/<id>/edit/` | Edit settlement (draft/rejected) |
| `/driver/settlements/<id>/print/` | Printable settlement slip |
| `/driver/contract/` | Contract progress |
| `/driver/debt/` | Debt ledger |
| `/driver/profile/` | Profile view |
| `/driver/change-password/` | Change portal password |

## Testing

Run the test suite:

```bash
python manage.py test
```

### Manual Testing Checklist

- [ ] Vehicle CRUD (create, list, edit, delete)
- [ ] Driver CRUD; portal access toggle works
- [ ] Driver can log in and see their dashboard
- [ ] Driver can submit a settlement (daily & weekly)
- [ ] Settlement appears in Owner approvals
- [ ] Owner can approve – calculations correct per model, cash added to Cash in Hand
- [ ] Owner can reject – settlement status changes, driver can edit/resubmit
- [ ] Cash Book: record transactions, balances update correctly
- [ ] Bank accounts: add, transfer to/from bank, balances update
- [ ] Expenses: record with cash/bank, receipt upload works
- [ ] Reports generate correctly with filters
- [ ] Exports (CSV) produce valid files
- [ ] Contract model: progress tracking works, month-end settlement works
- [ ] Quota model: debt accumulates and repays
- [ ] Salary model: daily salary accrues correctly
- [ ] Percentage model: correct split

## License

This project is licensed under the MIT License.