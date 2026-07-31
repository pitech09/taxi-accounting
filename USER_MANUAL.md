# Taxi Accounting System – User Manual

## 1. System Overview

The Taxi Accounting System is a comprehensive web-based application designed for Lesotho transport businesses operating taxi fleets. It supports four operating models (Quota, Salary, Percentage, and Contract) and provides complete financial management including driver settlements, cash book tracking, and reporting.

**Currency:** All amounts are in Maloti (M), pegged 1:1 with the South African Rand (ZAR).

**Vehicle Types:**
- Sedan (4-seater)
- Minivan (6–8 seater)
- Minibus (14-seater)
- Bus (30–50 seater)

---

## 2. Getting Started (For Owners)

### 2.1 Accessing the System

1. Navigate to your system URL (e.g., `https://your-app.onrender.com`)
2. Click "Login" or navigate to `/accounts/login/`
3. Enter your username and password (provided by the system administrator)
4. You will be redirected to the Owner Dashboard

### 2.2 System Setup Checklist

1. **Configure System Settings** – Go to *Settings* to set your company name, debt cap, and alert thresholds
2. **Add Vehicles** – Register each vehicle with its type, plate number, and operating model
3. **Add Drivers** – Register drivers and assign them to vehicles
4. **Enable Driver Portal** – For each driver, enable portal access and set a password
5. **Add Bank Accounts** – Set up your bank accounts in the Cash Book section
6. **Record Initial Cash** – Add the opening cash balance in Cash Book

---

## 3. Owner Portal Guide

### 3.1 Dashboard

The dashboard provides a quick overview of your business:
- **Cash in Hand** – Current physical cash balance
- **Bank Total** – Sum of all bank account balances
- **Pending Approvals** – Number of settlements waiting for your review
- **Approved Today** – Settlements approved today
- **Monthly Summary** – Total income, owner collection, and driver pay for the month
- **Recent Settlements** – Last 5 approved settlements

### 3.2 Vehicles

**Navigation:** Sidebar → Vehicles

**Features:**
- **List View** – See all vehicles with their type, plate, and operating model
- **Add Vehicle** – Register a new vehicle with:
  - Name, type, seats, plate number
  - Operating model (Quota, Salary, Percentage, or Contract)
  - Model-specific parameters (quota amount, salary, percentage, contract target)
  - Fixed costs (insurance, permit, loan payment)
  - Settlement frequency (Daily or Weekly)
- **Edit Vehicle** – Modify any vehicle details
- **Delete Vehicle** – Remove a vehicle (no associated settlements)

### 3.3 Drivers

**Navigation:** Sidebar → Drivers

**Features:**
- **List View** – See all drivers with their vehicle, phone, and portal status
- **Add Driver** – Register a new driver with:
  - Personal details (name, phone, email, address, ID number)
  - License information (type, number, expiry)
  - Vehicle assignment
  - Settlement frequency (overrides vehicle default)
  - Operating model overrides (optional)
  - Portal access (enable/disable, set password)
- **Edit Driver** – Modify any driver details
- **View Settlements** – Click "View Settlements" to see a driver's settlement history
- **Delete Driver** – Remove a driver

### 3.4 Settlements

**Navigation:** Sidebar → Settlements

**Features:**
- **List View** – All settlements with filters (status, vehicle, driver)
- **Add Settlement** – Create a settlement directly (auto-approved for owner)
- **View Details** – See full settlement breakdown
- **Edit Settlement** – Modify settlement details
- **Delete Settlement** – Remove a settlement
- **Export CSV** – Download all settlements as a CSV file

### 3.5 Approvals

**Navigation:** Sidebar → Approvals

When a driver submits a settlement through the Driver Portal, it appears here for your review.

**Review Process:**
1. Click on a pending settlement to review it
2. Review all income and expense entries
3. See the auto-calculated totals and driver pay
4. **Approve** – The settlement is finalized:
   - Calculations are applied based on the operating model
   - The owner's collection amount is automatically added to Cash in Hand
   - A CashTransaction is created for the settlement collection
5. **Reject** – The settlement is returned to the driver:
   - Add notes explaining why it was rejected
   - The driver can edit and resubmit

### 3.6 Cash Book

**Navigation:** Sidebar → Cash Book

The Cash Book tracks all cash and bank transactions with a running balance.

**Dashboard:**
- Current Cash in Hand balance
- Bank account balances
- Recent transactions
- Low balance alerts

**Features:**
- **Transaction Ledger** – Full list of all transactions with filters
- **Add Transaction** – Record any transaction type:
  - Cash Addition / Withdrawal
  - Transfer to/from Bank
  - Expense (Cash or Bank)
  - Petty Cash
  - Salary / Commission / Bonus Payment
  - Loan Repayment
- **Deposit to Bank** – Quick form to transfer cash to a bank account
- **Withdraw from Bank** – Quick form to transfer from bank to cash
- **Record Expense** – Quick form for expenses with receipt upload
- **Bank Accounts** – Add, edit, delete bank accounts
- **Export CSV** – Download the ledger as CSV

**Important:** When a settlement is approved, the owner's collection is automatically added to Cash in Hand. No manual entry is needed.

### 3.7 Contracts

**Navigation:** Sidebar → Contracts

**Features:**
- **Contract Dashboard** – See all contract-model drivers with progress:
  - Monthly target vs. actual gross income
  - Progress percentage
  - Days remaining in the month
  - Daily average needed to meet target
- **Driver Detail** – Detailed view of a driver's contract progress
- **Month-End Settlement** – Finalise a contract at month end:
  - Calculates success/failure bonus
  - Creates a MonthlyContractSummary record
  - Records driver and owner payouts

### 3.8 Reports

**Navigation:** Sidebar → Reports

**Available Reports:**
1. **Daily Fleet Summary** – Income, expenses, and profit for all vehicles on a specific day
2. **Monthly P&L** – Profit & Loss breakdown per vehicle for a date range
3. **Cash Book Ledger** – Full transaction ledger with filters
4. **Bank Reconciliation** – Reconcile bank account transactions
5. **Expense Report** – Categorised expense breakdown
6. **Cash Flow Statement** – Cash inflows and outflows over a period
7. **Contract Progress** – Monitor contract driver progress
8. **Contract Settlements** – Historical contract settlement summaries
9. **Contract Analytics** – Analytics and charts for contract performance
10. **Tax Report** – Taxable income and expense summary

**Features:**
- Date range filters
- Vehicle/Driver filters
- Print-friendly views
- Export to CSV (where available)

### 3.9 Settings

**Navigation:** Sidebar → Settings

**Configuration Options:**
- Company name, phone, email, address
- Debt cap (maximum debt a driver can accumulate)
- Repayment percentage (% of surplus used to repay debt)
- Minimum driver take
- Days in month for salary calculation
- Contract settlement day
- Default bank account
- Cash and bank alert thresholds

---

## 4. Driver Portal Guide

### 4.1 Accessing the Driver Portal

1. Your owner must enable portal access and provide you with:
   - A 4-digit driver code
   - A portal password
2. Navigate to `/driver/login/` or click "Driver Login" on the main page
3. Enter your 4-digit driver code and password
4. Click "Login"

### 4.2 Dashboard

The driver dashboard shows:
- Your assigned vehicle and operating model
- Recent settlements (last 5)
- Pending approval count
- Current debt balance (for Quota model)
- Contract progress (for Contract model)

### 4.3 Submitting a Settlement

**Navigation:** Settlements → Create Settlement

1. Select the date (and week start/end for weekly settlements)
2. Enter your income:
   - Cash collected
   - Mobile money collected
   - Card collected
3. Enter your expenses:
   - Fuel
   - Maintenance/Repairs
   - Tolls
   - Other (with description)
4. Add any notes for the owner
5. Click "Submit" – the settlement is sent to the owner for approval

**Note:** You can only submit one settlement per day (or per week for weekly settlements).

### 4.4 Settlement History

**Navigation:** Settlements

View all your submitted settlements with their status:
- **Draft** – Not yet submitted
- **Submitted** – Waiting for owner approval
- **Approved** – Accepted by the owner (calculations applied)
- **Rejected** – Returned by the owner (you can edit and resubmit)

### 4.5 Editing a Settlement

Only settlements with status **Draft** or **Rejected** can be edited:
1. Find the settlement in your history
2. Click "Edit"
3. Make your changes
4. Click "Submit" to resubmit for approval

### 4.6 Printing a Settlement Slip

Click "Print" on any settlement to view a print-friendly settlement slip.

### 4.7 Contract Progress (Contract Model Only)

**Navigation:** Contract

If you are on a Contract operating model, this page shows:
- Your monthly target
- Current gross income
- Progress percentage
- Days remaining
- Daily average needed to meet the target

### 4.8 Debt Ledger (Quota Model Only)

**Navigation:** Debt

If you are on a Quota operating model, this page shows:
- Current debt balance
- History of all settlements with surplus/shortfall, debt repaid, and new debt

### 4.9 Profile & Password

**Navigation:** Profile

- View your personal details and vehicle assignment
- **Change Password** – Update your portal password

---

## 5. Operating Model Explanations

### 5.1 Quota System

**How it works:**
- The driver pays a fixed daily quota to the owner
- The driver keeps all surplus income after expenses and quota
- If the driver's gross profit is less than the quota, the shortfall becomes debt

**Example:**
- Daily quota: M 250
- Driver's gross profit: M 400
- Surplus: M 400 - M 250 = M 150 (driver keeps this)
- Owner collects: M 250

**Debt Example:**
- Daily quota: M 250
- Driver's gross profit: M 180
- Shortfall: M 250 - M 180 = M 70 (added to debt)
- Previous debt: M 100
- New debt: M 100 + M 70 = M 170

**Debt Repayment:**
- When there is a surplus, it is first used to repay any outstanding debt
- The remaining surplus goes to the driver

### 5.2 Monthly Salary System

**How it works:**
- The driver receives a fixed monthly salary
- The owner keeps all gross profit after paying the driver's salary
- Daily salary rate = Monthly salary ÷ Days in month

**Example:**
- Monthly salary: M 3,000
- Days in month: 30
- Daily rate: M 3,000 ÷ 30 = M 100
- Driver's gross profit: M 500
- Driver pay: M 100
- Owner collects: M 500 - M 100 = M 400

### 5.3 Percentage System

**How it works:**
- The driver receives a fixed percentage of the gross profit
- The owner keeps the remaining percentage

**Example:**
- Driver percentage: 30%
- Gross profit: M 500
- Driver pay: 30% of M 500 = M 150
- Owner collects: 70% of M 500 = M 350

### 5.4 Contract System

**How it works:**
- The driver and owner agree on a monthly target
- **If target is achieved:** Driver receives a bonus (fixed amount, percentage of gross, or hybrid)
- **If target is NOT achieved:** Driver receives a failure percentage of gross income

**Bonus Types:**
1. **Fixed** – Driver receives a fixed bonus amount (e.g., M 2,000)
2. **Percentage** – Driver receives a percentage of gross income (e.g., 10%)
3. **Hybrid** – Driver receives fixed bonus + percentage of gross

**Example (Success):**
- Monthly target: M 15,000
- Actual gross: M 18,000
- Bonus type: Fixed (M 2,000)
- Driver pay: M 2,000
- Owner collects: M 18,000 - M 2,000 = M 16,000

**Example (Failure):**
- Monthly target: M 15,000
- Actual gross: M 10,000
- Failure percentage: 20%
- Driver pay: 20% of M 10,000 = M 2,000
- Owner collects: M 10,000 - M 2,000 = M 8,000

---

## 6. Cash Book Walkthrough

### 6.1 Understanding the Cash Book

The Cash Book tracks two types of balances:
1. **Cash in Hand** – Physical cash you have on hand
2. **Bank Accounts** – Money in your bank accounts

### 6.2 Recording Transactions

**Cash Addition:**
- Use when you add physical cash to the business (e.g., owner's capital injection)
- Cash in Hand increases

**Cash Withdrawal:**
- Use when you remove physical cash from the business (e.g., owner's drawings)
- Cash in Hand decreases

**Deposit to Bank:**
- Transfer cash from your hand to the bank
- Cash in Hand decreases, Bank balance increases

**Withdraw from Bank:**
- Transfer money from the bank to cash
- Cash in Hand increases, Bank balance decreases

**Expense:**
- Record business expenses (fuel, maintenance, insurance, etc.)
- Choose Cash or Bank as the payment method
- Can upload receipts

**Settlement Collection:**
- **Automatic** – Created when a settlement is approved
- The owner's collection amount is added to Cash in Hand
- No manual entry needed

### 6.3 Viewing the Ledger

The transaction ledger shows all transactions with:
- Date, type, category, amount
- Bank account (if applicable)
- Cash and bank balances after each transaction
- Reference and notes

### 6.4 Exporting

You can export the ledger to CSV for analysis in Excel or other tools.

---

## 7. Troubleshooting & FAQ

### 7.1 Common Issues

**Q: I can't log in to the driver portal.**
A: Check that your driver code is correct and that the owner has enabled portal access. If you forgot your password, ask the owner to reset it.

**Q: The settlement calculations look wrong.**
A: Check that your vehicle is assigned the correct operating model and parameters. The calculation uses the effective values from the vehicle or driver overrides.

**Q: The cash balance doesn't match.**
A: Review the transaction ledger for any missing or incorrect entries. Check that settlement collections were automatically added when you approved settlements.

**Q: I can't edit a settlement.**
A: Only settlements with status "Draft" or "Rejected" can be edited. Submit a new settlement if you need to make changes to an approved one.

### 7.2 Best Practices

- **Daily Settlements** – Submit settlements daily for accurate tracking
- **Receipts** – Upload receipts for expenses whenever possible
- **Regular Reconciliation** – Reconcile your cash book with actual cash on hand regularly
- **Backup** – Export reports regularly for record-keeping

### 7.3 Support

If you encounter issues or need assistance:
- Contact your system administrator
- Refer to the README.md for technical setup and deployment information

---

## 8. Glossary

| Term | Definition |
|------|------------|
| **Maloti (M)** | The currency of Lesotho, pegged 1:1 with the South African Rand |
| **Quota** | A daily fixed amount a driver must pay to the owner |
| **Settlement** | A driver's daily or weekly income and expense report |
| **Gross Profit** | Total income minus total expenses |
| **Surplus** | Gross profit minus quota (positive) |
| **Shortfall** | Quota minus gross profit (negative) |
| **Debt** | Accumulated shortfall that a driver owes |
| **Contract Target** | Monthly gross income target agreed between driver and owner |
| **Cash in Hand** | Physical cash available |
| **P&L** | Profit and Loss statement |
| **CSV** | Comma-Separated Values file format |
| **PDF** | Portable Document Format |

---

*Document Version 1.0 – Taxi Accounting System*