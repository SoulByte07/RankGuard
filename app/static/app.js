document.addEventListener('DOMContentLoaded', () => {
    // Elements
    const txForm = document.getElementById('transaction-form');
    const txUserIdInput = document.getElementById('tx-user-id');
    const btnGenUser = document.getElementById('btn-generate-user');
    const txTypeSelect = document.getElementById('tx-type');
    const txAmountInput = document.getElementById('tx-amount');
    const txIdempotencyInput = document.getElementById('tx-idempotency');
    const btnGenIdempotency = document.getElementById('btn-generate-idempotency');
    const txExtraDataInput = document.getElementById('tx-extra-data');

    const summaryForm = document.getElementById('summary-form');
    const lookupUserIdInput = document.getElementById('lookup-user-id');
    const summaryResultContainer = document.getElementById('summary-result-container');
    const summaryEmptyState = document.getElementById('summary-empty');
    
    const summaryRank = document.getElementById('summary-rank');
    const summaryBalance = document.getElementById('summary-balance');
    const summaryEarned = document.getElementById('summary-earned');
    const summarySpent = document.getElementById('summary-spent');
    const summaryTxCount = document.getElementById('summary-tx-count');
    const summaryLastActivity = document.getElementById('summary-last-activity');

    const btnRefreshLeaderboard = document.getElementById('btn-refresh-leaderboard');
    const btnComputeLeaderboard = document.getElementById('btn-compute-leaderboard');
    const leaderboardBody = document.getElementById('leaderboard-body');
    const leaderboardEmptyState = document.getElementById('leaderboard-empty');
    const toastContainer = document.getElementById('toast-container');

    // State
    let activeLookupUserId = null;

    // Toast Notification System
    function showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        
        let iconSvg = '';
        if (type === 'success') {
            iconSvg = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" class="toast-icon"><polyline points="20 6 9 17 4 12"></polyline></svg>`;
        } else if (type === 'error') {
            iconSvg = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" class="toast-icon"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg>`;
        } else {
            iconSvg = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" class="toast-icon"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>`;
        }

        toast.innerHTML = `
            ${iconSvg}
            <span class="toast-message">${message}</span>
        `;
        
        toastContainer.appendChild(toast);
        
        // Remove after duration
        setTimeout(() => {
            toast.style.animation = 'slideIn 0.3s cubic-bezier(0.16, 1, 0.3, 1) reverse forwards';
            setTimeout(() => {
                toast.remove();
            }, 300);
        }, 4000);
    }

    // UUID Generator v4
    function generateUUID() {
        return ([1e7]+-1e3+-4e3+-8e3+-1e11).replace(/[018]/g, c =>
            (c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> c / 4).toString(16)
        );
    }

    // Populate Fields
    function refreshIdempotencyKey() {
        txIdempotencyInput.value = generateUUID();
    }

    btnGenUser.addEventListener('click', () => {
        txUserIdInput.value = generateUUID();
        showToast('Generated new user UUID', 'info');
    });

    btnGenIdempotency.addEventListener('click', () => {
        refreshIdempotencyKey();
        showToast('Generated new idempotency key', 'info');
    });

    // Format numbers to currency
    const formatCurrency = (val) => {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD'
        }).format(val);
    };

    // Parse extra data safely
    function getExtraData() {
        const raw = txExtraDataInput.value.trim();
        if (!raw) return null;
        try {
            return JSON.parse(raw);
        } catch (e) {
            throw new Error('Invalid JSON format in Extra Data');
        }
    }

    // POST /transaction
    txForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const userId = txUserIdInput.value.trim();
        const type = txTypeSelect.value;
        const amountStr = txAmountInput.value.trim();
        const idempotencyKey = txIdempotencyInput.value.trim();
        
        if (!userId || !amountStr || !idempotencyKey) {
            showToast('Please fill out all required fields', 'error');
            return;
        }

        let extraData = null;
        try {
            extraData = getExtraData();
        } catch (err) {
            showToast(err.message, 'error');
            return;
        }

        const payload = {
            idempotency_key: idempotencyKey,
            user_id: userId,
            type: type,
            amount: parseFloat(amountStr),
            extra_data: extraData
        };

        try {
            const res = await fetch('/transaction', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            const data = await res.json();

            if (res.status === 201) {
                showToast('Transaction processed successfully! (201 Created)', 'success');
                // Refresh views
                fetchLeaderboard();
                if (activeLookupUserId === userId) {
                    fetchUserSummary(userId);
                }
                // Cycle key to prevent accidental immediate double clicks, but retain user ID for speed
                refreshIdempotencyKey();
            } else if (res.status === 200) {
                showToast('Duplicate transaction detected. Returned original state. (200 OK)', 'info');
                refreshIdempotencyKey();
            } else {
                // Handle 400 or 422
                let errMsg = data.detail || 'Error processing transaction';
                if (Array.isArray(data.detail)) {
                    errMsg = data.detail.map(d => `${d.loc.join('.')}: ${d.msg}`).join(', ');
                }
                showToast(errMsg, 'error');
            }
        } catch (err) {
            showToast('Network error processing transaction', 'error');
            console.error(err);
        }
    });

    // GET /summary/{userId}
    async function fetchUserSummary(userId) {
        if (!userId) return;
        
        try {
            const res = await fetch(`/summary/${userId}`);
            
            if (res.status === 404) {
                showToast(`User ${userId.substring(0, 8)}... not found`, 'error');
                summaryResultContainer.style.display = 'none';
                summaryEmptyState.style.display = 'flex';
                activeLookupUserId = null;
                return;
            }

            if (!res.ok) {
                showToast('Error retrieving user summary', 'error');
                return;
            }

            const data = await res.json();
            
            // Populate and show
            activeLookupUserId = userId;
            summaryRank.textContent = data.rank !== null ? `#${data.rank}` : 'Unranked';
            summaryBalance.textContent = formatCurrency(data.net_balance);
            summaryEarned.textContent = formatCurrency(data.total_earned);
            summarySpent.textContent = formatCurrency(data.total_spent);
            summaryTxCount.textContent = data.transaction_count + (data.bonus_count > 0 ? ` (+${data.bonus_count} bonus)` : '');
            
            const lastActiveDate = new Date(data.last_activity);
            summaryLastActivity.textContent = `Last Active: ${lastActiveDate.toLocaleString()}`;
            
            summaryEmptyState.style.display = 'none';
            summaryResultContainer.style.display = 'flex';
        } catch (err) {
            showToast('Network error fetching summary', 'error');
            console.error(err);
        }
    }

    summaryForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const userId = lookupUserIdInput.value.trim();
        if (!userId) {
            showToast('Please enter a User ID', 'error');
            return;
        }
        fetchUserSummary(userId);
    });

    // GET /ranking
    async function fetchLeaderboard() {
        try {
            const res = await fetch('/ranking?limit=50&offset=0');
            if (!res.ok) {
                showToast('Error loading leaderboard data', 'error');
                return;
            }

            const data = await res.json();
            const results = data.results || [];
            
            leaderboardBody.innerHTML = '';
            
            if (results.length === 0) {
                leaderboardEmptyState.style.display = 'flex';
                return;
            }

            leaderboardEmptyState.style.display = 'none';
            
            results.forEach((entry) => {
                const tr = document.createElement('tr');
                
                // Rank styling badge
                let rankClass = 'rank-other';
                if (entry.rank === 1) rankClass = 'rank-1';
                else if (entry.rank === 2) rankClass = 'rank-2';
                else if (entry.rank === 3) rankClass = 'rank-3';
                
                tr.innerHTML = `
                    <td><span class="rank-badge ${rankClass}">${entry.rank}</span></td>
                    <td><a class="user-link" data-user-id="${entry.user_id}">${entry.user_id}</a></td>
                    <td class="score-cell">${parseFloat(entry.score).toFixed(2)}</td>
                    <td class="earn">${formatCurrency(entry.total_earned)}</td>
                    <td class="spend">${formatCurrency(entry.total_spent)}</td>
                    <td>${entry.transaction_count}</td>
                `;
                
                leaderboardBody.appendChild(tr);
            });

            // Wire up user links click
            document.querySelectorAll('.user-link').forEach(link => {
                link.addEventListener('click', (e) => {
                    const uid = e.target.getAttribute('data-user-id');
                    lookupUserIdInput.value = uid;
                    fetchUserSummary(uid);
                    showToast(`Loading summary for ${uid.substring(0, 8)}...`, 'info');
                });
            });

        } catch (err) {
            showToast('Network error loading leaderboard', 'error');
            console.error(err);
        }
    }

    // POST /ranking/compute
    async function computeLeaderboard() {
        btnComputeLeaderboard.disabled = true;
        btnComputeLeaderboard.querySelector('span').textContent = 'Computing...';
        
        try {
            const res = await fetch('/ranking/compute', { method: 'POST' });
            if (res.ok) {
                showToast('Ranking cache computed successfully', 'success');
                await fetchLeaderboard();
                if (activeLookupUserId) {
                    await fetchUserSummary(activeLookupUserId);
                }
            } else {
                showToast('Failed to compute ranking cache', 'error');
            }
        } catch (err) {
            showToast('Network error computing ranking cache', 'error');
            console.error(err);
        } finally {
            btnComputeLeaderboard.disabled = false;
            btnComputeLeaderboard.querySelector('span').textContent = 'Recompute Cache';
        }
    }

    // Refresh and auto timers
    btnRefreshLeaderboard.addEventListener('click', () => {
        fetchLeaderboard();
        showToast('Leaderboard refreshed', 'info');
    });

    btnComputeLeaderboard.addEventListener('click', () => {
        computeLeaderboard();
    });

    // Initialize Page
    refreshIdempotencyKey();
    fetchLeaderboard();
    
    // Auto refresh every 10s
    setInterval(fetchLeaderboard, 10000);
});
