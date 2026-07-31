/**
 * cashbook.js – Cash Book UI interactions for the Taxi Accounting System
 * 
 * Shows projected balances when entering amounts, validates forms,
 * and provides real-time feedback.
 */

(function () {
    'use strict';

    function initCashBook() {
        const amountInput = document.querySelector('#id_amount');
        if (!amountInput) return;

        const cashBalanceEl = document.querySelector('.cash-balance');
        const bankBalanceEl = document.querySelector('.bank-balance');
        const projectedEl = document.querySelector('.projected-balance');
        const transactionTypeEl = document.querySelector('#id_transaction_type');
        const bankAccountEl = document.querySelector('#id_bank_account');

        function updateProjectedBalance() {
            const amount = parseFloat(amountInput.value) || 0;
            const cashBalance = parseFloat(cashBalanceEl?.dataset.balance || 0);
            const bankBalance = parseFloat(bankBalanceEl?.dataset.balance || 0);
            const transactionType = transactionTypeEl?.value || '';
            const bankId = bankAccountEl?.value || '';

            let projectedCash = cashBalance;
            let projectedBank = bankBalance;

            switch (transactionType) {
                // Cash additions
                case 'addition':
                case 'settlement_collection':
                    projectedCash += amount;
                    break;

                // Cash deductions
                case 'withdrawal':
                case 'expense_cash':
                case 'petty_cash':
                case 'salary_payment':
                case 'commission_payment':
                case 'bonus_payment':
                case 'loan_repayment':
                    projectedCash -= amount;
                    break;

                // Transfer to bank: cash decreases, bank increases
                case 'transfer_to_bank':
                    projectedCash -= amount;
                    if (bankId) projectedBank += amount;
                    break;

                // Transfer from bank: cash increases, bank decreases
                case 'transfer_from_bank':
                    projectedCash += amount;
                    if (bankId) projectedBank -= amount;
                    break;

                // Bank expense
                case 'expense_bank':
                    if (bankId) projectedBank -= amount;
                    break;
            }

            // Update projected balance display
            if (projectedEl) {
                projectedEl.textContent = 'M ' + projectedCash.toFixed(2);
                projectedEl.className = 'projected-balance ' +
                    (projectedCash < 0 ? 'amount-negative' : 'amount-positive');
            }

            // Highlight low balance warnings
            const cashWarning = document.querySelector('.cash-warning');
            if (cashWarning) {
                const threshold = parseFloat(cashWarning.dataset.threshold || 1000);
                if (projectedCash < threshold) {
                    cashWarning.style.display = 'block';
                } else {
                    cashWarning.style.display = 'none';
                }
            }
        }

        // Listen for changes
        amountInput.addEventListener('input', updateProjectedBalance);
        amountInput.addEventListener('change', updateProjectedBalance);

        if (transactionTypeEl) {
            transactionTypeEl.addEventListener('change', function () {
                // Show/hide bank account field based on transaction type
                const bankGroup = document.querySelector('.field-bank_account');
                if (bankGroup) {
                    const val = this.value;
                    if (['transfer_to_bank', 'transfer_from_bank', 'expense_bank'].includes(val)) {
                        bankGroup.style.display = 'block';
                    } else {
                        bankGroup.style.display = 'none';
                    }
                }
                updateProjectedBalance();
            });
            // Trigger initial state
            transactionTypeEl.dispatchEvent(new Event('change'));
        }

        if (bankAccountEl) {
            bankAccountEl.addEventListener('change', updateProjectedBalance);
        }

        // Initial calculation
        updateProjectedBalance();
    }

    // Initialise on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initCashBook);
    } else {
        initCashBook();
    }
})();