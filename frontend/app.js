// ===== Configuration =====
const API_BASE = "http://localhost:5000/api";
let token = localStorage.getItem('access_token');
let currentUser = null;
let currentScanId = null;
let remainingFreeScans = -1;

// ===== Currency Detection =====
function getUserCurrencySymbol() {
    try {
        const manualOverride = localStorage.getItem('preferred_currency');
        if (manualOverride) return manualOverride;

        const lang = navigator.language || navigator.languages?.[0] || 'en-US';
        const country = lang.split('-')[1]?.toUpperCase() || '';

        const currencyMap = {
            'NG': '₦', 'US': '$', 'GB': '£', 'EU': '€',
            'KE': 'KES', 'ZA': 'ZAR', 'GH': 'GH₵', 'EG': 'EGP',
            'IN': '₹', 'AU': 'A$', 'CA': 'C$', 'SG': 'S$',
            'MY': 'RM', 'PH': '₱'
        };

        if (country && currencyMap[country]) return currencyMap[country];
        return '₦';
    } catch { return '₦'; }
}

function formatPrice(amount, currencySymbol) {
    return `${currencySymbol}${amount.toLocaleString()}`;
}

function updatePaymentPrices() {
    const symbol = getUserCurrencySymbol();
    const monthlyPrice = 1000;
    const yearlyPrice = 12000;

    document.querySelectorAll('[data-price-monthly]').forEach(el => {
        el.textContent = formatPrice(monthlyPrice, symbol);
    });
    document.querySelectorAll('[data-price-yearly]').forEach(el => {
        el.textContent = formatPrice(yearlyPrice, symbol);
    });
}

// ===== DOM Refs =====
const mainContent = document.getElementById('main-content');
const authModal = document.getElementById('auth-modal');
const authForm = document.getElementById('auth-form');
const authSubmit = document.getElementById('auth-submit');
const authToggleBtn = document.getElementById('auth-toggle-btn');
const authToggleText = document.getElementById('auth-toggle-text');
const modalTitle = document.getElementById('modal-title');
const modalSubtitle = document.getElementById('modal-subtitle');
const emailGroup = document.getElementById('email-group');
const newsletterGroup = document.getElementById('newsletter-group');
const authError = document.getElementById('auth-error');
const usernameInput = document.getElementById('auth-username');
const emailInput = document.getElementById('auth-email');
const passwordInput = document.getElementById('auth-password');
const modalClose = document.getElementById('modal-close');
const scanForm = document.getElementById('scan-form');
const targetInput = document.getElementById('target-input');
const scanBtn = document.getElementById('scan-btn');
const scanMessage = document.getElementById('scan-message');
const scanList = document.getElementById('scan-list');
const greeting = document.getElementById('greeting');
const usernameDisplay = document.getElementById('username-display');
const totalScansEl = document.getElementById('total-scans');
const safeTargetsEl = document.getElementById('safe-targets');
const totalFindingsEl = document.getElementById('total-findings');
const backBtn = document.getElementById('back-to-dashboard');
const resultContainer = document.getElementById('result-container');
const logoutLink = document.getElementById('logout-link');
const upgradeHeaderBtn = document.getElementById('upgrade-header-btn');
const upgradeSidebarBtn = document.getElementById('upgrade-btn');
const paywallMessage = document.getElementById('paywall-message');
const paywallUpgradeBtn = document.getElementById('paywall-upgrade-btn');
const historyUpgrade = document.getElementById('history-upgrade');
const historyUpgradeBtn = document.getElementById('history-upgrade-btn');
const resultUpgrade = document.getElementById('result-upgrade');
const resultUpgradeBtn = document.getElementById('result-upgrade-btn');
const freeRemaining = document.getElementById('free-remaining');
const paymentModal = document.getElementById('payment-modal');
const paymentClose = document.getElementById('payment-close');
const checkoutBtn = document.getElementById('checkout-btn');
const emailPdfBtn = document.getElementById('email-pdf-btn');
const pdfEmailInput = document.getElementById('pdf-email-input');
const emailPdfMessage = document.getElementById('email-pdf-message');

let authMode = 'login';
let selectedPlan = 'monthly';

// ===== Init =====
document.addEventListener('DOMContentLoaded', () => {
    updatePaymentPrices();
    mainContent.style.display = 'block';
    fetchFreeRemaining();

    if (token) fetchMe();
    else { updateAuthUI(); showUpgradePrompts(false); }

    authForm.addEventListener('submit', handleAuth);
    authToggleBtn.addEventListener('click', toggleAuthMode);
    modalClose.addEventListener('click', () => authModal.classList.add('hidden'));
    authModal.addEventListener('click', (e) => {
        if (e.target === authModal) authModal.classList.add('hidden');
    });

    document.querySelectorAll('.sidebar nav a').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const view = link.dataset.view;
            if (view === 'dashboard') showDashboard();
            else if (view === 'history') { showDashboard(); loadScans(); }
            else if (view === 'new-scan') { showDashboard(); targetInput.focus(); }
        });
    });

    scanForm.addEventListener('submit', startScan);
    backBtn.addEventListener('click', showDashboard);
    logoutLink.addEventListener('click', logout);

    upgradeHeaderBtn.addEventListener('click', showPaymentModal);
    upgradeSidebarBtn.addEventListener('click', showPaymentModal);
    paywallUpgradeBtn.addEventListener('click', showPaymentModal);
    historyUpgradeBtn.addEventListener('click', showPaymentModal);
    resultUpgradeBtn.addEventListener('click', showPaymentModal);

    paymentClose.addEventListener('click', () => paymentModal.classList.add('hidden'));
    paymentModal.addEventListener('click', (e) => {
        if (e.target === paymentModal) paymentModal.classList.add('hidden');
    });
    document.querySelectorAll('.plan-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.plan-btn').forEach(b => b.classList.remove('selected'));
            btn.classList.add('selected');
            selectedPlan = btn.dataset.plan;
        });
    });
    checkoutBtn.addEventListener('click', handleCheckout);

    emailPdfBtn.addEventListener('click', sendPdfToEmail);
});

// ===== Auth Functions =====
function showAuthModal() {
    authModal.classList.remove('hidden');
    authError.style.display = 'none';
    authSubmit.disabled = false;
    usernameInput.focus();
}

function updateAuthUI() {
    if (token && currentUser) {
        usernameDisplay.textContent = currentUser.username;
    }
}

function toggleAuthMode() {
    if (authMode === 'login') {
        authMode = 'register';
        modalTitle.textContent = 'Create Account';
        modalSubtitle.textContent = 'Start assessing security today';
        authSubmit.textContent = 'Create Account';
        authToggleText.textContent = 'Already have an account?';
        authToggleBtn.textContent = 'Sign in';
        emailGroup.style.display = 'block';
        newsletterGroup.style.display = 'block';
    } else {
        authMode = 'login';
        modalTitle.textContent = 'Sign In';
        modalSubtitle.textContent = 'Access your security dashboard';
        authSubmit.textContent = 'Sign In';
        authToggleText.textContent = "Don't have an account?";
        authToggleBtn.textContent = 'Create one';
        emailGroup.style.display = 'none';
        newsletterGroup.style.display = 'none';
    }
    authError.style.display = 'none';
}

async function handleAuth(e) {
    e.preventDefault();
    const username = usernameInput.value.trim();
    const password = passwordInput.value.trim();
    const email = emailInput.value.trim();
    const subscribe = document.getElementById('subscribe-newsletter')?.checked || false;

    if (!username || !password) {
        showAuthError('Please fill in all fields.');
        return;
    }
    if (authMode === 'register' && !email) {
        showAuthError('Please enter your email.');
        return;
    }

    const body = { username, password };
    if (authMode === 'register') {
        body.email = email;
        body.subscribe_newsletter = subscribe;
    }

    authSubmit.disabled = true;
    authSubmit.textContent = 'Processing...';
    authError.style.display = 'none';

    try {
        const res = await fetch(`${API_BASE}/auth/${authMode}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        const data = await res.json();

        if (data.access_token) {
            localStorage.setItem('access_token', data.access_token);
            token = data.access_token;
            authModal.classList.add('hidden');
            await fetchMe();
        } else {
            showAuthError(data.msg || 'Authentication failed.');
            authSubmit.disabled = false;
            authSubmit.textContent = authMode === 'login' ? 'Sign In' : 'Create Account';
        }
    } catch (err) {
        showAuthError('Network error. Please try again.');
        authSubmit.disabled = false;
        authSubmit.textContent = authMode === 'login' ? 'Sign In' : 'Create Account';
    }
}

function showAuthError(msg) {
    authError.textContent = msg;
    authError.style.display = 'block';
}

async function fetchMe() {
    try {
        const res = await fetch(`${API_BASE}/auth/me`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) {
            currentUser = await res.json();
            updateAuthUI();
            const hour = new Date().getHours();
            const timeGreeting = hour < 12 ? 'Good morning' : hour < 18 ? 'Good afternoon' : 'Good evening';
            greeting.textContent = `${timeGreeting}, ${currentUser.username}.`;
            loadScans();
            fetchFreeRemaining();
        } else {
            logout();
        }
    } catch { logout(); }
}

function logout() {
    localStorage.removeItem('access_token');
    token = null;
    currentUser = null;
    updateAuthUI();
    loadScans();
    fetchFreeRemaining();
}

// ===== Free scan counter =====
async function fetchFreeRemaining() {
    try {
        const headers = token ? { 'Authorization': `Bearer ${token}` } : {};
        const res = await fetch(`${API_BASE}/scans/free-remaining`, { headers });
        if (res.ok) {
            const data = await res.json();
            remainingFreeScans = data.remaining;
            freeRemaining.textContent = remainingFreeScans;
            if (remainingFreeScans === 0 && !token) {
                freeRemaining.style.color = '#EF4444';
                paywallMessage.classList.add('visible');
                scanBtn.disabled = true;
                scanBtn.style.opacity = '0.5';
                document.querySelector('.quick-scan .scan-input-group').style.display = 'none';
            } else {
                freeRemaining.style.color = '#22C55E';
                paywallMessage.classList.remove('visible');
                scanBtn.disabled = false;
                scanBtn.style.opacity = '1';
                document.querySelector('.quick-scan .scan-input-group').style.display = 'flex';
            }
            showUpgradePrompts(!!token);
        }
    } catch (err) {
        console.error('Failed to fetch free remaining:', err);
    }
}

function showUpgradePrompts(isLoggedIn) {
    if (isLoggedIn) {
        historyUpgrade.classList.add('visible');
        resultUpgrade.classList.add('visible');
    } else {
        if (remainingFreeScans === 0) {
            historyUpgrade.classList.add('visible');
            resultUpgrade.classList.add('visible');
        } else {
            historyUpgrade.classList.remove('visible');
            resultUpgrade.classList.remove('visible');
        }
    }
}

// ===== Dashboard =====
function showDashboard() {
    document.getElementById('view-dashboard').style.display = 'block';
    document.getElementById('view-result').style.display = 'none';
    document.querySelectorAll('.sidebar nav a').forEach(a => a.classList.remove('active'));
    document.querySelector('[data-view="dashboard"]').classList.add('active');
    loadScans();
    fetchFreeRemaining();
}

function showResult() {
    document.getElementById('view-dashboard').style.display = 'none';
    document.getElementById('view-result').style.display = 'block';
}

// ===== Load Scans =====
async function loadScans() {
    if (!token) {
        scanList.innerHTML = '<p style="color:#94A3B8;font-size:0.85rem;">Login to see your scan history.</p>';
        totalScansEl.textContent = '-';
        safeTargetsEl.textContent = '-';
        totalFindingsEl.textContent = '-';
        return;
    }
    try {
        const res = await fetch(`${API_BASE}/scans`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!res.ok) throw new Error('Unauthorized');
        const scans = await res.json();
        renderScanList(scans);
        updateStats(scans);
    } catch (err) {
        scanList.innerHTML = '<p style="color:#94A3B8;font-size:0.85rem;">Could not load scans.</p>';
    }
}

function renderScanList(scans) {
    if (!scans || scans.length === 0) {
        scanList.innerHTML = '<p style="color:#94A3B8;font-size:0.85rem;">No scans yet. Run your first assessment above.</p>';
        return;
    }
    scanList.innerHTML = scans.map(s => {
        const score = s.results?.score || 0;
        let verdict = s.status === 'completed' ?
            (score >= 80 ? 'Excellent' : score >= 60 ? 'Good' : 'Warning') :
            s.status;
        let cls = s.status === 'completed' ?
            (score >= 80 ? 'excellent' : score >= 60 ? 'good' : 'warning') :
            '';
        return `
            <div class="scan-item" data-id="${s.id}">
                <span class="target">${s.target}</span>
                <span class="score ${cls}">${s.status === 'completed' ? score+'/100 · '+verdict : verdict}</span>
                <span class="date">${new Date(s.created_at).toLocaleString()}</span>
            </div>
        `;
    }).join('');

    document.querySelectorAll('.scan-item').forEach(el => {
        el.addEventListener('click', () => showScanDetail(el.dataset.id));
    });
}

function updateStats(scans) {
    const total = scans.length;
    const safe = scans.filter(s => s.status === 'completed' && s.results?.score >= 60).length;
    const findings = scans.reduce((acc, s) => acc + (s.results?.findings?.length || 0), 0);
    totalScansEl.textContent = total;
    safeTargetsEl.textContent = safe;
    totalFindingsEl.textContent = findings;
}

// ===== Start Scan =====
async function startScan(e) {
    e.preventDefault();
    const target = targetInput.value.trim();
    if (!target) { scanMessage.textContent = 'Please enter a target.'; return; }

    scanBtn.disabled = true;
    scanMessage.textContent = '⏳ Queuing scan...';

    try {
        const headers = { 'Content-Type': 'application/json' };
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        const res = await fetch(`${API_BASE}/scans`, {
            method: 'POST',
            headers: headers,
            body: JSON.stringify({ target, authorized: true })
        });
        const data = await res.json();

        if (res.status === 429 && data.requires_auth) {
            scanMessage.innerHTML = '';
            paywallMessage.classList.add('visible');
            document.querySelector('.quick-scan .scan-input-group').style.display = 'none';
            scanBtn.disabled = true;
            scanBtn.style.opacity = '0.5';
            fetchFreeRemaining();
            return;
        }

        if (res.ok) {
            const remaining = data.remaining_free;
            if (remaining !== undefined) {
                scanMessage.innerHTML = `
                    ✅ Scan queued!
                    <br>
                    <small style="color:#94A3B8;">Free scans remaining this month: ${remaining}/${data.max_free || 3}</small>
                    <br>
                    <a href="#" onclick="showScanDetail('${data.scan_id}'); return false;">View progress →</a>
                `;
                freeRemaining.textContent = remaining;
                if (remaining === 0 && !token) {
                    freeRemaining.style.color = '#EF4444';
                }
            } else {
                scanMessage.innerHTML = `
                    ✅ Scan queued.
                    <a href="#" onclick="showScanDetail('${data.scan_id}'); return false;">View progress →</a>
                `;
            }
            loadScans();
            pollScan(data.scan_id);
            fetchFreeRemaining();
        } else {
            scanMessage.textContent = '❌ ' + (data.msg || 'Error');
        }
    } catch (err) {
        scanMessage.textContent = '❌ Network error';
    }
    scanBtn.disabled = false;
}

// ===== Show Scan Detail =====
async function showScanDetail(scanId) {
    if (!token) {
        showAuthModal();
        return;
    }
    showResult();
    resultContainer.innerHTML = '<p style="color:#94A3B8;">Loading...</p>';

    try {
        const res = await fetch(`${API_BASE}/scans/${scanId}?include_results=true`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!res.ok) throw new Error('Not found');
        const scan = await res.json();
        currentScanId = scan.id;
        renderResult(scan);
        if (scan.status === 'queued' || scan.status === 'running') {
            pollScan(scanId);
        }
        if (!currentUser?.is_paid_user) {
            resultUpgrade.classList.add('visible');
        } else {
            resultUpgrade.classList.remove('visible');
        }
    } catch (err) {
        resultContainer.innerHTML = '<p style="color:#EF4444;">Could not load scan details.</p>';
    }
}

function renderResult(scan) {
    const r = scan.results || {};
    const score = r.score || 0;
    const verdict = score >= 80 ? 'Excellent' : score >= 60 ? 'Good' : score >= 40 ? 'Warning' : 'Critical';
    const color = score >= 80 ? '#22C55E' : score >= 60 ? '#38BDF8' : score >= 40 ? '#F59E0B' : '#EF4444';
    const findings = r.findings || [];

    let html = `
        <h2>Assessment: ${scan.target}</h2>
        <div class="score-ring">
            <div class="circle" style="background: conic-gradient(${color} 0% ${score}%, #1E293B ${score}% 100%);">
                <div class="inner">
                    <span class="number">${score}</span>
                    <span class="total">/100</span>
                </div>
            </div>
            <div class="verdict" style="color:${color};">${verdict}</div>
            <div class="subtext">${r.summary || 'Assessment complete.'}</div>
        </div>
        <button class="download-pdf" onclick="downloadReport()">↓ Download Security Report</button>
    `;

    if (r.breakdown) {
        html += `<div class="breakdown"><table>`;
        for (const [cat, sc] of Object.entries(r.breakdown)) {
            html += `<tr><td class="cat-name">${cat}</td><td class="cat-score">${sc}/100</td></tr>`;
        }
        html += `</table></div>`;
    }

    if (findings.length) {
        html += `<div class="findings"><h3>Security Findings</h3>`;
        findings.forEach(f => {
            const severity = f.severity || 'Info';
            const cls = severity.toLowerCase();
            html += `
                <div class="finding ${cls}">
                    <div class="severity">${severity}</div>
                    <div class="title">${f.title}</div>
                    <div class="detail">${f.detail}</div>
                    ${f.evidence ? `<div class="evidence">${f.evidence}</div>` : ''}
                    ${f.recommendation ? `<div class="recommendation"><strong>→</strong> ${f.recommendation}</div>` : ''}
                </div>
            `;
        });
        html += `</div>`;
    }

    html += `
        <details class="tech-details">
            <summary>🔧 Technical Details</summary>
            <pre>${JSON.stringify(r, null, 2)}</pre>
        </details>
    `;

    resultContainer.innerHTML = html;

    const emailSection = document.getElementById('email-pdf-section');
    if (scan.status === 'completed') {
        emailSection.style.display = 'block';
    } else {
        emailSection.style.display = 'none';
    }
}

function downloadReport() {
    if (currentScanId) {
        window.open(`${API_BASE}/scans/${currentScanId}/report?token=${token}`, '_blank');
    }
}

// ===== Polling =====
function pollScan(scanId) {
    const interval = setInterval(async () => {
        try {
            const res = await fetch(`${API_BASE}/scans/${scanId}?include_results=true`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (!res.ok) throw new Error();
            const scan = await res.json();

            if (scan.status === 'completed' || scan.status === 'failed') {
                clearInterval(interval);
                renderResult(scan);
                loadScans();
                fetchFreeRemaining();
            } else {
                const subtext = document.querySelector('#result-container .subtext');
                if (subtext) subtext.textContent = `⏳ ${scan.status}...`;
            }
        } catch (err) {
            // silent fail
        }
    }, 3000);
}

// ===== Email PDF =====
async function sendPdfToEmail() {
    const email = pdfEmailInput.value.trim();
    if (!email) {
        emailPdfMessage.textContent = 'Please enter your email address.';
        emailPdfMessage.style.color = '#EF4444';
        return;
    }
    if (!currentScanId) {
        emailPdfMessage.textContent = 'No scan selected.';
        return;
    }

    const btn = emailPdfBtn;
    btn.disabled = true;
    btn.textContent = 'Sending...';
    emailPdfMessage.textContent = '';

    try {
        const headers = { 'Content-Type': 'application/json' };
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        const res = await fetch(`${API_BASE}/scans/${currentScanId}/email-pdf`, {
            method: 'POST',
            headers: headers,
            body: JSON.stringify({ email })
        });

        const data = await res.json();

        if (res.ok) {
            emailPdfMessage.textContent = '✅ PDF sent! Check your inbox (and spam folder).';
            emailPdfMessage.style.color = '#22C55E';
        } else {
            emailPdfMessage.textContent = '❌ ' + (data.msg || 'Failed to send PDF');
            emailPdfMessage.style.color = '#EF4444';
        }
    } catch (err) {
        emailPdfMessage.textContent = '❌ Network error. Please try again.';
        emailPdfMessage.style.color = '#EF4444';
    }

    btn.disabled = false;
    btn.textContent = 'Send PDF';
}

// ===== Payment Modal =====
function showPaymentModal() {
    if (!token) {
        showAuthModal();
        return;
    }
    paymentModal.classList.remove('hidden');
    document.querySelector('[data-plan="monthly"]')?.classList.add('selected');
    selectedPlan = 'monthly';
    document.getElementById('payment-error').style.display = 'none';
}

async function handleCheckout() {
    const symbol = getUserCurrencySymbol();
    alert(`Payment integration coming soon! You will be able to subscribe for ${symbol}1,000/month.`);
}