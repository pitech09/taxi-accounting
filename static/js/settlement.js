/**
 * settlement.js – Real-time settlement calculation for the Taxi Accounting System
 * 
 * Calculates totals, gross profit, driver pay, and owner collection
 * based on the selected vehicle/driver operating model.
 */

(function () {
    'use strict';

    const AMOUNT_CLASS = 'amount-input';
    const TOTALS_CLASS = 'auto-calc';

    function initSettlementCalculator() {
        const form = document.querySelector('.settlement-form');
        if (!form) return;

        const inputs = form.querySelectorAll('.' + AMOUNT_CLASS);
        inputs.forEach(input => {
            input.addEventListener('input', recalculateTotals);
            input.addEventListener('change', recalculateTotals);
        });

        // Watch for vehicle/driver changes
        const vehicleSelect = form.querySelector('#id_vehicle');
        const driverSelect = form.querySelector('#id_driver');
        if (vehicleSelect) {
            vehicleSelect.addEventListener('change', function () {
                loadVehicleDetails(this.value);
                recalculateTotals();
            });
        }
        if (driverSelect) {
            driverSelect.addEventListener('change', function () {
                loadDriverDetails(this.value);
                recalculateTotals();
            });
        }

        // Initial calculation
        recalculateTotals();
    }

    function getValue(selector) {
        const el = document.querySelector(selector);
        return el ? parseFloat(el.value) || 0 : 0;
    }

    function setValue(selector, value) {
        const el = document.querySelector(selector);
        if (el) {
            el.textContent = 'M ' + (value || 0).toFixed(2);
        }
    }

    function recalculateTotals() {
        const cash = getValue('#id_cash_collected');
        const mobile = getValue('#id_mobile_collected');
        const card = getValue('#id_card_collected');
        const fuel = getValue('#id_fuel_expense');
        const maintenance = getValue('#id_maintenance_expense');
        const toll = getValue('#id_toll_expense');
        const other = getValue('#id_other_expense');

        const totalIncome = cash + mobile + card;
        const totalExpenses = fuel + maintenance + toll + other;
        const grossProfit = totalIncome - totalExpenses;

        setValue('.calc-total-income', totalIncome);
        setValue('.calc-total-expenses', totalExpenses);
        setValue('.calc-gross-profit', grossProfit);

        // Update hidden fields if they exist
        const hiddenIncome = document.querySelector('#id_total_income');
        const hiddenExpenses = document.querySelector('#id_total_expenses');
        const hiddenGross = document.querySelector('#id_gross_profit');
        if (hiddenIncome) hiddenIncome.value = totalIncome.toFixed(2);
        if (hiddenExpenses) hiddenExpenses.value = totalExpenses.toFixed(2);
        if (hiddenGross) hiddenGross.value = grossProfit.toFixed(2);

        // Trigger model-specific calculation
        const modelEl = document.querySelector('.calc-operating-model');
        const model = modelEl ? modelEl.textContent.trim().toLowerCase() : 'quota';

        switch (model) {
            case 'quota':
                calcQuota(grossProfit);
                break;
            case 'salary':
                calcSalary(grossProfit);
                break;
            case 'percentage':
                calcPercentage(grossProfit);
                break;
            case 'contract':
                calcContract(grossProfit);
                break;
        }
    }

    function calcQuota(grossProfit) {
        const dailyQuota = parseFloat(document.querySelector('.calc-daily-quota')?.textContent) || 250;
        const previousDebt = parseFloat(document.querySelector('.calc-previous-debt')?.textContent) || 0;

        let driverPay = 0;
        let ownerCollection = 0;
        let debtRepaid = 0;
        let newDebt = previousDebt;
        let surplusShortfall = 0;

        // If the driver has previous debt, repayment applies
        if (grossProfit >= dailyQuota) {
            const surplus = grossProfit - dailyQuota;
            surplusShortfall = surplus;
            if (previousDebt > 0) {
                debtRepaid = Math.min(surplus, previousDebt);
                newDebt = Math.max(0, previousDebt - debtRepaid);
                driverPay = debtRepaid + (surplus - debtRepaid);
            } else {
                driverPay = surplus;
                newDebt = 0;
            }
            ownerCollection = dailyQuota;
        } else {
            surplusShortfall = grossProfit - dailyQuota;
            const shortfall = dailyQuota - grossProfit;
            newDebt = previousDebt + shortfall;
            ownerCollection = grossProfit;
            driverPay = 0;
        }

        setValue('.calc-surplus-shortfall', surplusShortfall);
        setValue('.calc-debt-repaid', debtRepaid);
        setValue('.calc-new-debt', newDebt);
        setValue('.calc-driver-pay', driverPay);
        setValue('.calc-owner-collection', ownerCollection + totalExpenses());
    }

    function calcSalary(grossProfit) {
        const dailyRate = parseFloat(document.querySelector('.calc-daily-rate')?.textContent) || 100;
        const driverPay = dailyRate;
        const ownerCollection = grossProfit - dailyRate + totalExpenses();
        setValue('.calc-driver-pay', driverPay);
        setValue('.calc-owner-collection', Math.max(0, ownerCollection));
    }

    function calcPercentage(grossProfit) {
        const percentage = parseFloat(document.querySelector('.calc-driver-percentage')?.textContent) || 30;
        const driverAmount = (percentage / 100) * grossProfit;
        const ownerAmount = grossProfit - driverAmount;
        setValue('.calc-driver-percentage-amount', driverAmount);
        setValue('.calc-owner-percentage-amount', ownerAmount);
        setValue('.calc-driver-pay', driverAmount);
        setValue('.calc-owner-collection', ownerAmount + totalExpenses());
    }

    function calcContract(grossProfit) {
        const target = parseFloat(document.querySelector('.calc-contract-target')?.textContent) || 15000;
        const monthlyGross = parseFloat(document.querySelector('.calc-monthly-gross')?.textContent) || 0;
        const remaining = Math.max(0, target - monthlyGross);
        setValue('.calc-remaining-target', remaining);
    }

    function totalExpenses() {
        return getValue('#id_fuel_expense') + getValue('#id_maintenance_expense') +
            getValue('#id_toll_expense') + getValue('#id_other_expense');
    }

    function loadVehicleDetails(vehicleId) {
        if (!vehicleId) return;
        fetch('/api/vehicle/' + vehicleId + '/details/')
            .then(r => r.json())
            .then(data => {
                const el = document.querySelector('.calc-operating-model');
                if (el) el.textContent = data.operating_model_display;

                const qEl = document.querySelector('.calc-daily-quota');
                if (qEl) qEl.textContent = data.daily_quota;

                const sEl = document.querySelector('.calc-daily-rate');
                if (sEl && data.operating_model === 'salary') {
                    sEl.textContent = (parseFloat(data.monthly_salary) / 30).toFixed(2);
                }

                const pEl = document.querySelector('.calc-driver-percentage');
                if (pEl) pEl.textContent = data.driver_percentage;

                const tEl = document.querySelector('.calc-contract-target');
                if (tEl) tEl.textContent = data.contract_target;
            })
            .catch(console.error);
    }

    function loadDriverDetails(driverId) {
        if (!driverId) return;
        fetch('/api/driver/' + driverId + '/details/')
            .then(r => r.json())
            .then(data => {
                const el = document.querySelector('.calc-previous-debt');
                if (el) el.textContent = data.debt_balance;
            })
            .catch(console.error);
    }

    // Initialize on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initSettlementCalculator);
    } else {
        initSettlementCalculator();
    }
})();