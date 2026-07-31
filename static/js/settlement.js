/**
 * settlement.js – Real-time settlement calculation
 * Uses business rules from the Django models.
 */

(function () {
    'use strict';

    const AMOUNT_CLASS = 'amount-input';

    function initSettlementCalculator() {
        const form = document.querySelector('.settlement-form');
        if (!form) return;

        // All input fields that affect calculations
        const inputs = form.querySelectorAll('.' + AMOUNT_CLASS);
        inputs.forEach(input => {
            input.addEventListener('input', recalculate);
            input.addEventListener('change', recalculate);
        });

        // Vehicle/driver changes
        const vehicleSelect = form.querySelector('#id_vehicle');
        const driverSelect = form.querySelector('#id_driver');
        if (vehicleSelect) vehicleSelect.addEventListener('change', function () {
            loadVehicleDetails(this.value);
            recalculate();
        });
        if (driverSelect) driverSelect.addEventListener('change', function () {
            loadDriverDetails(this.value);
            recalculate();
        });

        // Initial calculation
        recalculate();
    }

    function getVal(selector) {
        const el = document.querySelector(selector);
        return el ? parseFloat(el.value) || 0 : 0;
    }

    function setText(selector, value, prefix = 'M ') {
        const el = document.querySelector(selector);
        if (el) el.textContent = prefix + value.toFixed(2);
    }

    function recalculate() {
        // 1. Income & expenses
        const cash = getVal('#id_cash_collected');
        const mobile = getVal('#id_mobile_collected');
        const card = getVal('#id_card_collected');
        const totalIncome = cash + mobile + card;

        const fuel = getVal('#id_fuel_expense');
        const maintenance = getVal('#id_maintenance_expense');
        const toll = getVal('#id_toll_expense');
        const other = getVal('#id_other_expense');
        const totalExpenses = fuel + maintenance + toll + other;

        const grossProfit = totalIncome - totalExpenses;

        // 2. Update common fields
        setText('.calc-total-income', totalIncome);
        setText('.calc-total-expenses', totalExpenses);
        setText('.calc-gross-profit', grossProfit);

        // 3. Determine operating model
        const modelEl = document.querySelector('.calc-operating-model');
        const model = modelEl ? modelEl.textContent.trim().toLowerCase() : 'quota';

        // 4. Model-specific calculations
        let driverPay = 0;
        let ownerCollection = 0;

        // Show/hide model sections
        document.querySelectorAll('.model-specific').forEach(el => el.style.display = 'none');
        const sectionId = model + 'Calculations';
        const section = document.getElementById(sectionId);
        if (section) section.style.display = 'block';

        if (model === 'quota') {
            // Read quota and previous debt from data attributes or hidden fields
            const quota = parseFloat(document.querySelector('.calc-daily-quota')?.dataset.value) || 250;
            const previousDebt = parseFloat(document.querySelector('.calc-previous-debt')?.dataset.value) || 0;

            let surplus = grossProfit - quota;
            let debtRepaid = 0;
            let newDebt = previousDebt;

            if (grossProfit >= quota) {
                // Surplus case
                if (previousDebt > 0) {
                    debtRepaid = Math.min(surplus, previousDebt);
                    newDebt = previousDebt - debtRepaid;
                    driverPay = surplus - debtRepaid;
                } else {
                    driverPay = surplus;
                    newDebt = 0;
                }
                ownerCollection = quota; // owner gets quota
            } else {
                // Shortfall case
                const shortfall = quota - grossProfit;
                newDebt = previousDebt + shortfall;
                driverPay = 0;
                ownerCollection = Math.max(0, grossProfit); // owner gets all, but not negative
            }

            setText('.calc-surplus-shortfall', surplus);
            setText('.calc-debt-repaid', debtRepaid);
            setText('.calc-new-debt', newDebt);
            // Debt status badge update
            const debtStatusEl = document.querySelector('.calc-debt-status');
            if (debtStatusEl) {
                let text, cls;
                if (newDebt === 0) { text = 'No Debt'; cls = 'bg-success'; }
                else if (debtRepaid > 0 && newDebt > 0) { text = 'Partial'; cls = 'bg-warning'; }
                else if (newDebt > 0) { text = 'Debt: M ' + newDebt.toFixed(2); cls = 'bg-danger'; }
                debtStatusEl.textContent = text;
                debtStatusEl.className = 'badge ' + cls;
            }

        } else if (model === 'salary') {
            const monthlySalary = parseFloat(document.querySelector('.calc-daily-rate')?.dataset.value) || 3000;
            const days = 30; // can be read from settings
            const dailyRate = monthlySalary / days;
            setText('.calc-daily-salary', dailyRate);
            // Salary accrued – simplified, we don't have month-to-date here
            setText('.calc-salary-accrued', dailyRate); // placeholder

            driverPay = dailyRate;
            ownerCollection = grossProfit - dailyRate;
            if (ownerCollection < 0) ownerCollection = 0; // owner can't lose money in UI? But accounting allows negative.

        } else if (model === 'percentage') {
            const percentage = parseFloat(document.querySelector('.calc-driver-percentage')?.dataset.value) || 30;
            const driverAmount = (percentage / 100) * totalIncome; // based on total income, not gross
            const ownerAmount = totalIncome - driverAmount;

            setText('.calc-driver-share', driverAmount);
            setText('.calc-owner-share', ownerAmount);

            driverPay = driverAmount;
            ownerCollection = ownerAmount;

        } else if (model === 'contract') {
            // For live preview: we show a simple estimate based on failure percentage
            const target = parseFloat(document.querySelector('.calc-contract-target')?.dataset.value) || 15000;
            const failurePct = parseFloat(document.querySelector('.calc-failure-percentage')?.dataset.value) || 20;
            // Assume we don't know month-to-date gross, so we use current totalIncome as daily income
            const dailyIncome = totalIncome;
            // If we had month-to-date, we could compute progress, but for now show placeholder
            setText('.calc-contract-remaining', target - dailyIncome);
            // Driver pay = failure percentage of daily income (assuming not reached target)
            const failureAmount = (failurePct / 100) * dailyIncome;
            driverPay = failureAmount;
            ownerCollection = dailyIncome - driverPay;
            // Progress bar – we can't compute without month-to-date, so we set to 0
            const progressBar = document.getElementById('contractProgressBar');
            if (progressBar) {
                const progress = Math.min(100, (dailyIncome / target) * 100);
                progressBar.style.width = progress + '%';
                progressBar.textContent = progress.toFixed(0) + '%';
            }
        }

        // 5. Update final payouts
        setText('.calc-driver-pay', driverPay);
        setText('.calc-owner-collection', ownerCollection);

        // Optionally update hidden fields if they exist
        const hiddenIncome = document.querySelector('#id_total_income');
        const hiddenExpenses = document.querySelector('#id_total_expenses');
        const hiddenGross = document.querySelector('#id_gross_profit');
        const hiddenDriverPay = document.querySelector('#id_driver_pay');
        const hiddenOwnerCol = document.querySelector('#id_total_owner_collected');
        if (hiddenIncome) hiddenIncome.value = totalIncome.toFixed(2);
        if (hiddenExpenses) hiddenExpenses.value = totalExpenses.toFixed(2);
        if (hiddenGross) hiddenGross.value = grossProfit.toFixed(2);
        if (hiddenDriverPay) hiddenDriverPay.value = driverPay.toFixed(2);
        if (hiddenOwnerCol) hiddenOwnerCol.value = ownerCollection.toFixed(2);
    }

    // Load vehicle details from API and update data attributes
    function loadVehicleDetails(vehicleId) {
        if (!vehicleId) return;
        fetch('/api/vehicle/' + vehicleId + '/details/')
            .then(r => r.json())
            .then(data => {
                const modelEl = document.querySelector('.calc-operating-model');
                if (modelEl) modelEl.textContent = data.operating_model_display;

                const qEl = document.querySelector('.calc-daily-quota');
                if (qEl) qEl.dataset.value = data.daily_quota;

                const sEl = document.querySelector('.calc-daily-rate');
                if (sEl) sEl.dataset.value = data.monthly_salary;

                const pEl = document.querySelector('.calc-driver-percentage');
                if (pEl) pEl.dataset.value = data.driver_percentage;

                const tEl = document.querySelector('.calc-contract-target');
                if (tEl) tEl.dataset.value = data.contract_target;

                const fEl = document.querySelector('.calc-failure-percentage');
                if (fEl) fEl.dataset.value = data.contract_failure_percentage;
            })
            .catch(console.error);
    }

    function loadDriverDetails(driverId) {
        if (!driverId) return;
        fetch('/api/driver/' + driverId + '/details/')
            .then(r => r.json())
            .then(data => {
                const debtEl = document.querySelector('.calc-previous-debt');
                if (debtEl) debtEl.dataset.value = data.debt_balance;
            })
            .catch(console.error);
    }

    // Initialize
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initSettlementCalculator);
    } else {
        initSettlementCalculator();
    }
})();