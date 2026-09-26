// Master Dashboard State
const DEFAULT_BINANCE_SYMBOLS = [
    { symbol: 'BTCUSDT', baseAsset: 'BTC' },
    { symbol: 'ETHUSDT', baseAsset: 'ETH' },
    { symbol: 'SOLUSDT', baseAsset: 'SOL' },
    { symbol: 'SYNUSDT', baseAsset: 'SYN' },
    { symbol: 'DOGEUSDT', baseAsset: 'DOGE' },
    { symbol: 'PEPEUSDT', baseAsset: 'PEPE' },
    { symbol: '1000PEPEUSDT', baseAsset: 'PEPE' },
    { symbol: 'XRPUSDT', baseAsset: 'XRP' },
    { symbol: 'BNBUSDT', baseAsset: 'BNB' },
    { symbol: 'SUIUSDT', baseAsset: 'SUI' },
    { symbol: 'NEARUSDT', baseAsset: 'NEAR' },
    { symbol: 'AVAXUSDT', baseAsset: 'AVAX' },
    { symbol: 'LINKUSDT', baseAsset: 'LINK' },
    { symbol: 'ADAUSDT', baseAsset: 'ADA' },
    { symbol: 'DOTUSDT', baseAsset: 'DOT' },
    { symbol: 'APTUSDT', baseAsset: 'APT' },
    { symbol: 'ARBUSDT', baseAsset: 'ARB' },
    { symbol: 'OPUSDT', baseAsset: 'OP' },
    { symbol: 'LDOUSDT', baseAsset: 'LDO' },
    { symbol: 'TIAUSDT', baseAsset: 'TIA' },
    { symbol: 'SEIUSDT', baseAsset: 'SEI' },
    { symbol: 'WIFUSDT', baseAsset: 'WIF' },
    { symbol: 'FETUSDT', baseAsset: 'FET' },
    { symbol: 'INJUSDT', baseAsset: 'INJ' },
    { symbol: 'PENDLEUSDT', baseAsset: 'PENDLE' },
    { symbol: 'TAOUSDT', baseAsset: 'TAO' },
    { symbol: 'AAVEUSDT', baseAsset: 'AAVE' },
    { symbol: 'UNIUSDT', baseAsset: 'UNI' },
    { symbol: 'FILUSDT', baseAsset: 'FIL' },
    { symbol: 'LTCUSDT', baseAsset: 'LTC' },
    { symbol: 'BCHUSDT', baseAsset: 'BCH' },
    { symbol: 'TRXUSDT', baseAsset: 'TRX' },
    { symbol: 'ATOMUSDT', baseAsset: 'ATOM' },
    { symbol: 'FTMUSDT', baseAsset: 'FTM' },
    { symbol: 'SHIBUSDT', baseAsset: 'SHIB' },
    { symbol: '1000SHIBUSDT', baseAsset: 'SHIB' }
];

const state = {
    activeTab: 'matrix', // 'matrix' or 'funding'
    strategies: [],
    selectedStrategy: 'trend_rider_supertrend',
    selectedTimeframe: '1h',
    selectedPairScope: 'top_10_pnl',
    pairPresets: {
        top_12: [],
        top_25: [],
        top_50: [],
        top_100: [],
        all_coins: []
    },
    allSymbols: [...DEFAULT_BINANCE_SYMBOLS],
    botWatchlist: ['XTZUSDT'],
    chartFocusSymbol: 'XTZUSDT',
    watchlistMode: 'multi', // 'single' or 'multi'
    selectedRisk: 'fixed_250',
    selectedLeverage: 3.0,
    selectedYear: 'ALL',
    matrixData: null,
    fundingData: [],
    filteredFundingData: [],
    fundingFilter: 'positive',
    fundingFilterSpot: 'spot_only',
    fundingSearch: '',
    isLoading: false
};

// --- INSTANT 0-MS CLIENT HYDRATION FOR TAB DUPLICATION & RELOAD ---
function fastHydrateBotState() {
    try {
        const cachedRaw = localStorage.getItem('bot_active_state');
        if (!cachedRaw) return;
        const cached = JSON.parse(cachedRaw);
        if (!cached) return;

        if (Array.isArray(cached.watchlist) && cached.watchlist.length > 0) {
            state.botWatchlist = [...cached.watchlist];
            if (cached.watchlist.length > 1) {
                state.watchlistMode = 'multi';
            }
            if (!state.chartFocusSymbol || !cached.watchlist.includes(state.chartFocusSymbol)) {
                state.chartFocusSymbol = cached.watchlist[0];
            }
        }
        if (cached.active_strategy_id) {
            state.selectedStrategy = cached.active_strategy_id;
        }
        if (cached.timeframe) {
            state.selectedTimeframe = cached.timeframe;
        }
        if (cached.leverage) {
            state.selectedLeverage = cached.leverage;
        }

        // Synchronously update DOM elements if available
        const statusBadge = document.getElementById('bot-status-badge');
        const statusText = document.getElementById('bot-status-text');
        const btnStart = document.getElementById('btn-start-bot');
        const btnStop = document.getElementById('btn-stop-bot');
        const botStratSelect = document.getElementById('bot-strategy-select');
        const botTfSelect = document.getElementById('bot-timeframe-select');
        const botLevSelect = document.getElementById('bot-leverage-select');
        const btnSingle = document.getElementById('mode-single-coin');
        const btnMulti = document.getElementById('mode-multi-coin');

        if (state.watchlistMode === 'multi' && btnMulti && btnSingle) {
            btnMulti.classList.add('active');
            btnSingle.classList.remove('active');
        } else if (state.watchlistMode === 'single' && btnSingle && btnMulti) {
            btnSingle.classList.add('active');
            btnMulti.classList.remove('active');
        }

        if (botStratSelect && cached.active_strategy_id && document.activeElement !== botStratSelect) {
            const stratId = (cached.active_strategy_id === 'price_ema_7') ? 'price_ema_crossover' : cached.active_strategy_id;
            const hasOption = Array.from(botStratSelect.options).some(o => o.value === stratId);
            if (hasOption) botStratSelect.value = stratId;
        }
        if (botTfSelect && cached.timeframe && document.activeElement !== botTfSelect) {
            botTfSelect.value = cached.timeframe;
        }
        if (botLevSelect && cached.leverage && document.activeElement !== botLevSelect) {
            botLevSelect.value = String(cached.leverage);
        }

        if (cached.is_running) {
            if (statusBadge) statusBadge.className = 'bot-status-badge running';
            const wl = state.botWatchlist || ['BTCUSDT'];
            const wlText = wl.length > 8 ? `${wl.length} PAIRS AUTO-HUNT (${wl.slice(0, 5).join(', ')} +${wl.length - 5} lainnya)` : `${wl.length} PAIR: ${wl.join(', ')}`;
            if (statusText) statusText.innerHTML = `<span class="pulse-dot green"></span> BOT ACTIVE (SCANNING ${wlText})`;
            if (btnStart) btnStart.style.display = 'none';
            if (btnStop) btnStop.style.display = 'inline-flex';
        } else {
            if (statusBadge) statusBadge.className = 'bot-status-badge';
            if (statusText) statusText.innerHTML = `<span class="pulse-dot"></span> BOT STANDBY / READY`;
            if (btnStart) btnStart.style.display = 'inline-flex';
            if (btnStop) btnStop.style.display = 'none';
        }

        if (typeof renderWatchlistChips === 'function') {
            renderWatchlistChips();
        }
    } catch (e) {
        console.error('fastHydrateBotState error:', e);
    }
}

// Preload state into memory immediately at script load
try {
    const cachedRaw = localStorage.getItem('bot_active_state');
    if (cachedRaw) {
        const cached = JSON.parse(cachedRaw);
        if (cached && Array.isArray(cached.watchlist) && cached.watchlist.length > 0) {
            state.botWatchlist = [...cached.watchlist];
            state.chartFocusSymbol = cached.watchlist[0];
            if (cached.watchlist.length > 1) state.watchlistMode = 'multi';
        }
        if (cached && cached.active_strategy_id) state.selectedStrategy = cached.active_strategy_id;
        if (cached && cached.timeframe) state.selectedTimeframe = cached.timeframe;
        if (cached && cached.leverage) state.selectedLeverage = cached.leverage;
    }
} catch (e) {}

// Global formatters with Binance thousand separators and exact Futures tick precision
function formatCleanPrice(val, customPrecision) {
    if (val === undefined || val === null || isNaN(val)) return '0.0';
    const num = Number(val);
    if (num === 0) return '0.0';
    
    let decimals = 2;
    if (customPrecision !== undefined && customPrecision !== null) {
        decimals = customPrecision;
    } else {
        const sym = (state && state.chartFocusSymbol) ? state.chartFocusSymbol.toUpperCase() : '';
        if (sym.includes('BTC') || num >= 20000) {
            decimals = 1; // Binance Futures BTCUSDT tickSize is 0.1 (1 decimal place)
        } else if (sym.includes('ETH') || sym.includes('BNB') || sym.includes('SOL') || num >= 50.0) {
            decimals = 2;
        } else if (sym.includes('NEAR') || sym.includes('SUI')) {
            decimals = 3;
        } else if (num < 0.0001) {
            decimals = 8;
        } else if (num < 0.01) {
            decimals = 6;
        } else if (num < 0.1) {
            decimals = 5;
        } else if (num < 50.0) {
            decimals = 4;
        } else {
            decimals = 2;
        }
    }

    return num.toLocaleString('en-US', { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
}

function formatExactPrice(val) {
    return formatCleanPrice(val);
}
window.formatCleanPrice = formatCleanPrice;
window.formatExactPrice = formatExactPrice;


// DOM Elements
const tabBtnMatrix = document.getElementById('tab-btn-matrix');
const tabBtnFunding = document.getElementById('tab-btn-funding');
const tabBtnBot = document.getElementById('tab-btn-bot');
const viewMatrix = document.getElementById('view-matrix');
const viewFunding = document.getElementById('view-funding');
const viewBot = document.getElementById('view-bot');
const navMatrixControls = document.getElementById('nav-matrix-controls');
const btnRunMatrix = document.getElementById('btn-run-matrix');
const btnRefreshFunding = document.getElementById('btn-refresh-funding');
const liveWibClock = document.getElementById('live-wib-clock');

// Matrix Controls
const strategySelect = document.getElementById('strategy-select');
const pairScopeSelect = document.getElementById('pair-scope-select');
const riskSelect = document.getElementById('risk-select');
const leverageSelect = document.getElementById('leverage-select');
const yearSelect = document.getElementById('year-select');
const timeframeGroup = document.getElementById('timeframe-group');
const btnToggleGlossary = document.getElementById('btn-toggle-glossary');
const glossaryBody = document.getElementById('glossary-body');
const btnExportMatrix = document.getElementById('btn-export-matrix');
const matrixTbody = document.getElementById('matrix-tbody');
const matrixThead = document.getElementById('matrix-thead');
const matrixTfoot = document.getElementById('matrix-tfoot');

// Trade Modal Elements
const tradeModal = document.getElementById('trade-modal');
const btnCloseModal = document.getElementById('btn-close-modal');
const modalPairTitle = document.getElementById('modal-pair-title');
const modalTradesTbody = document.getElementById('modal-trades-tbody');

// Funding Elements
const fundingNextTime = document.getElementById('funding-next-time');
const fundingCountdown = document.getElementById('funding-countdown');
const topTargetSymbol = document.getElementById('top-target-symbol');
const topTargetRate = document.getElementById('top-target-rate');
const topTargetPayout = document.getElementById('top-target-payout');
const btnQuickSimulate = document.getElementById('btn-quick-simulate');
const fundingSearchInput = document.getElementById('funding-search');
const fundingFilterRate = document.getElementById('funding-filter-rate');
const fundingFilterSpot = document.getElementById('funding-filter-spot');
const fundingPairsCount = document.getElementById('funding-pairs-count');
const fundingTbody = document.getElementById('funding-tbody');

// Simulator Modal Elements
const simulatorModal = document.getElementById('simulator-modal');
const btnCloseSimModal = document.getElementById('btn-close-sim-modal');
const simModalTitle = document.getElementById('sim-modal-title');
const simInputSymbol = document.getElementById('sim-input-symbol');
const simInputRate = document.getElementById('sim-input-rate');
const simInputCapital = document.getElementById('sim-input-capital');
const simInputIntervals = document.getElementById('sim-input-intervals');
const simGrossPayout = document.getElementById('sim-gross-payout');
const simFeeCost = document.getElementById('sim-fee-cost');
const simNetProfit = document.getElementById('sim-net-profit');
const simApyVal = document.getElementById('sim-apy-val');

// --- 1. INITIALIZATION ---
document.addEventListener('DOMContentLoaded', async () => {
    // 0-ms instant hydration from cache
    try { fastHydrateBotState(); } catch(e) { console.error('fastHydrate error:', e); }

    try { initClock(); } catch(e) { console.error('initClock error:', e); }
    try { setupEventListeners(); } catch(e) { console.error('setupEventListeners error:', e); }
    try { initBinanceLiveTickerStream(); } catch(e) { console.error('initTicker error:', e); }
    try { await loadPairs(); } catch(e) { console.error('loadPairs error:', e); }
    try { await loadStrategies(); } catch(e) { console.error('loadStrategies error:', e); }
    try { await loadAllFuturesSymbols(); } catch(e) { console.error('loadSymbols error:', e); }
    try { renderWatchlistChips(); } catch(e) { console.error('renderWatchlist error:', e); }
    try { loadBotStatus(); } catch(e) { console.error('loadBotStatus error:', e); }
    try { await runMasterMatrix(); } catch(e) { console.error('runMasterMatrix error:', e); }
    // Preload funding data in background
    try { loadLiveFundingRates(); } catch(e) { console.error('loadFunding error:', e); }

    // Multi-tab instant sync listener
    window.addEventListener('storage', (e) => {
        if (e.key === 'bot_active_state') {
            fastHydrateBotState();
        }
    });

    // Continuous 2s bot status polling
    setInterval(loadBotStatus, 2000);
});

// --- 2. LIVE WIB CLOCK & COUNTDOWN ---
function initClock() {
    function updateClock() {
        const now = new Date();
        const utc = now.getTime() + (now.getTimezoneOffset() * 60000);
        const wib = new Date(utc + (3600000 * 7));
        
        const hours = String(wib.getHours()).padStart(2, '0');
        const minutes = String(wib.getMinutes()).padStart(2, '0');
        const seconds = String(wib.getSeconds()).padStart(2, '0');
        liveWibClock.textContent = `${hours}:${minutes}:${seconds} WIB`;

        // Update funding countdown
        updateFundingCountdown(wib);
    }
    updateClock();
    setInterval(updateClock, 1000);
}

function updateFundingCountdown(wibDate) {
    const currentHour = wibDate.getHours();
    const settlementHours = [7, 15, 23];
    let nextHour = settlementHours.find(h => h > currentHour);
    let isNextDay = false;
    
    if (nextHour === undefined) {
        nextHour = 7;
        isNextDay = true;
    }

    const nextSettle = new Date(wibDate);
    if (isNextDay) {
        nextSettle.setDate(nextSettle.getDate() + 1);
    }
    nextSettle.setHours(nextHour, 0, 0, 0);

    const diffMs = nextSettle - wibDate;
    if (diffMs > 0) {
        const totalSec = Math.floor(diffMs / 1000);
        const h = Math.floor(totalSec / 3600);
        const m = Math.floor((totalSec % 3600) / 60);
        const s = totalSec % 60;
        const countdownText = `${String(h).padStart(2, '0')}h ${String(m).padStart(2, '0')}m ${String(s).padStart(2, '0')}s`;
        
        if (fundingCountdown) fundingCountdown.textContent = countdownText;
        if (fundingNextTime) fundingNextTime.textContent = `${String(nextHour).padStart(2, '0')}:00:00 WIB`;
    }
}

// --- 3. EVENT LISTENERS ---
function setupEventListeners() {
    // Tab switching
    tabBtnMatrix.addEventListener('click', () => switchTab('matrix'));
    tabBtnFunding.addEventListener('click', () => switchTab('funding'));
    if (tabBtnBot) tabBtnBot.addEventListener('click', () => switchTab('bot'));

    // Bot Controls
    const btnStartBot = document.getElementById('btn-start-bot');
    const btnStopBot = document.getElementById('btn-stop-bot');
    const botStratSelectEl = document.getElementById('bot-strategy-select');
    const botTfSelectEl = document.getElementById('bot-timeframe-select');
    if (btnStartBot) btnStartBot.addEventListener('click', startBotAutomation);
    if (btnStopBot) btnStopBot.addEventListener('click', stopBotAutomation);
    if (botStratSelectEl) {
        botStratSelectEl.addEventListener('change', (e) => {
            const stratVal = e.target.value;
            state.selectedStrategy = stratVal;
            // Sinkronisasi otomatis ke dropdown Tab Backtest Matriks
            if (strategySelect && strategySelect.value !== stratVal) {
                strategySelect.value = stratVal;
                updateGlossaryCard();
                runMasterMatrix();
            }
            const overlay = document.getElementById('chart-loading-overlay');
            if (overlay) overlay.style.display = 'flex';
            updateLiveBotChart();
        });
    }
    if (botTfSelectEl) {
        botTfSelectEl.addEventListener('change', (e) => {
            const tfVal = e.target.value;
            state.selectedTimeframe = tfVal;
            // Sinkronisasi otomatis ke tombol Timeframe Tab Backtest Matriks
            if (timeframeGroup) {
                timeframeGroup.querySelectorAll('.tf-btn').forEach(b => {
                    if (b.getAttribute('data-tf') === tfVal) b.classList.add('active');
                    else b.classList.remove('active');
                });
            }
            changeChartTimeframe(tfVal);
            runMasterMatrix();
        });
    }

    // Matrix Controls (Tab Backtest)
    strategySelect.addEventListener('change', (e) => {
        const stratVal = e.target.value;
        state.selectedStrategy = stratVal;
        // Sinkronisasi otomatis ke dropdown Tab Live Bot
        if (botStratSelectEl && botStratSelectEl.value !== stratVal) {
            botStratSelectEl.value = stratVal;
            updateLiveBotChart();
        }
        updateGlossaryCard();
        runMasterMatrix();
    });

    timeframeGroup.querySelectorAll('.tf-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            timeframeGroup.querySelectorAll('.tf-btn').forEach(b => b.classList.remove('active'));
            e.target.classList.add('active');
            const tfVal = e.target.getAttribute('data-tf');
            state.selectedTimeframe = tfVal;
            // Sinkronisasi otomatis ke dropdown Timeframe Tab Live Bot
            if (botTfSelectEl && botTfSelectEl.value !== tfVal) {
                botTfSelectEl.value = tfVal;
            }
            changeChartTimeframe(tfVal);
            runMasterMatrix();
        });
    });

    pairScopeSelect.addEventListener('change', (e) => {
        state.selectedPairScope = e.target.value;
        runMasterMatrix();
    });

    riskSelect.addEventListener('change', (e) => {
        const val = e.target.value;
        state.selectedRisk = val.startsWith('fixed_') ? val : parseFloat(val);
        runMasterMatrix();
    });

    if (leverageSelect) {
        leverageSelect.addEventListener('change', (e) => {
            state.selectedLeverage = parseFloat(e.target.value);
            runMasterMatrix();
        });
    }

    if (yearSelect) {
        yearSelect.addEventListener('change', (e) => {
            state.selectedYear = e.target.value;
            if (state.matrixData) renderMatrixTable(state.matrixData);
        });
    }

    if (btnRunMatrix) btnRunMatrix.addEventListener('click', () => runMasterMatrix());
    if (btnRefreshFunding) btnRefreshFunding.addEventListener('click', () => loadLiveFundingRates());

    if (btnToggleGlossary && glossaryBody) {
        btnToggleGlossary.addEventListener('click', () => {
            const isHidden = glossaryBody.style.display === 'none';
            glossaryBody.style.display = isHidden ? 'block' : 'none';
            btnToggleGlossary.innerHTML = isHidden ? '<i class="fa-solid fa-chevron-up"></i>' : '<i class="fa-solid fa-chevron-down"></i>';
        });
    }

    if (btnExportMatrix) btnExportMatrix.addEventListener('click', () => exportMatrixToCSV());

    // Modals
    if (btnCloseModal && tradeModal) {
        btnCloseModal.addEventListener('click', () => tradeModal.style.display = 'none');
        tradeModal.addEventListener('click', (e) => {
            if (e.target === tradeModal) tradeModal.style.display = 'none';
        });
    }

    if (btnCloseSimModal && simulatorModal) {
        btnCloseSimModal.addEventListener('click', () => simulatorModal.style.display = 'none');
        simulatorModal.addEventListener('click', (e) => {
            if (e.target === simulatorModal) simulatorModal.style.display = 'none';
        });
    }

    // Funding Filters
    if (fundingSearchInput) {
        fundingSearchInput.addEventListener('input', (e) => {
            state.fundingSearch = e.target.value.toLowerCase().trim();
            filterAndRenderFundingTable();
        });
    }

    if (fundingFilterRate) {
        fundingFilterRate.addEventListener('change', (e) => {
            state.fundingFilter = e.target.value;
            filterAndRenderFundingTable();
        });
    }

    if (fundingFilterSpot) {
        fundingFilterSpot.addEventListener('change', (e) => {
            state.fundingFilterSpot = e.target.value;
            filterAndRenderFundingTable();
        });
    }
    if (btnQuickSimulate) {
        btnQuickSimulate.addEventListener('click', () => {
            if (state.fundingData.length > 0) {
                openFundingSimulator(state.fundingData[0]);
            }
        });
    }

    // Simulator input change listeners
    [simInputRate, simInputCapital, simInputIntervals].forEach(input => {
        input.addEventListener('input', calculateSimulationLive);
        input.addEventListener('change', calculateSimulationLive);
    });
}

// --- 4. TAB SWITCHING ---
let botPollInterval = null;

function switchTab(tab) {
    state.activeTab = tab;
    
    // Reset tabs
    tabBtnMatrix.classList.remove('active');
    tabBtnFunding.classList.remove('active');
    if (tabBtnBot) tabBtnBot.classList.remove('active');

    viewMatrix.style.display = 'none';
    viewFunding.style.display = 'none';
    if (viewBot) viewBot.style.display = 'none';

    if (botPollInterval) {
        clearInterval(botPollInterval);
        botPollInterval = null;
    }

    if (tab === 'matrix') {
        tabBtnMatrix.classList.add('active');
        viewMatrix.style.display = 'block';
        if (navMatrixControls) navMatrixControls.style.display = 'block';
    } else if (tab === 'funding') {
        tabBtnFunding.classList.add('active');
        viewFunding.style.display = 'block';
        loadLiveFundingRates();
    } else if (tab === 'bot') {
        if (tabBtnBot) tabBtnBot.classList.add('active');
        if (viewBot) viewBot.style.display = 'block';
        loadAllFuturesSymbols();
        renderWatchlistChips();
        loadBotStatus();
        botPollInterval = setInterval(loadBotStatus, 3000);
        setTimeout(initLiveBotChart, 150);
    }
}
window.switchTab = switchTab;

// --- 5. LOAD STRATEGIES & PAIRS ---
async function loadStrategies() {
    try {
        const res = await fetch('/api/strategies');
        const strats = await res.json();
        if (strats && Array.isArray(strats) && strats.length > 0) {
            state.strategies = strats;
            const currentVal = strategySelect.value || state.selectedStrategy || 'price_ema_7';
            strategySelect.innerHTML = '';
            const botStratSelect = document.getElementById('bot-strategy-select');
            if (botStratSelect) botStratSelect.innerHTML = '';

            state.strategies.forEach(s => {
                const opt = document.createElement('option');
                opt.value = s.id;
                opt.textContent = `[${s.style}] ${s.name}`;
                if (s.id === currentVal) opt.selected = true;
                strategySelect.appendChild(opt);

                if (botStratSelect) {
                    const optBot = document.createElement('option');
                    optBot.value = s.id;
                    optBot.textContent = `[${s.style}] ${s.name}`;
                    if (s.id === currentVal || s.id === 'trend_rider_supertrend') optBot.selected = true;
                    botStratSelect.appendChild(optBot);
                }
            });
            state.selectedStrategy = strategySelect.value;
            updateGlossaryCard();
        }
    } catch (e) {
        console.error('Failed loading strategies:', e);
    }
}

async function loadPairs() {
    try {
        const res = await fetch('/api/pairs');
        const data = await res.json();
        state.pairPresets = data;
    } catch (e) {
        console.error('Failed loading pairs:', e);
    }
}

// --- 5.5. BINANCE FUTURES COIN SEARCH & WATCHLIST MANAGER ---
async function loadAllFuturesSymbols() {
    try {
        const res = await fetch('/api/symbols');
        const data = await res.json();
        if (data && data.success && Array.isArray(data.symbols) && data.symbols.length > 0) {
            state.allSymbols = data.symbols;
        }
    } catch (e) {
        console.error('Failed loading symbols:', e);
    }
}

function setWatchlistMode(mode) {
    state.watchlistMode = mode;
    const btnSingle = document.getElementById('mode-single-coin');
    const btnMulti = document.getElementById('mode-multi-coin');
    if (btnSingle && btnMulti) {
        if (mode === 'single') {
            btnSingle.classList.add('active');
            btnMulti.classList.remove('active');
            const focus = state.chartFocusSymbol || (state.botWatchlist && state.botWatchlist.length > 0 ? state.botWatchlist[0] : 'BTCUSDT');
            state.botWatchlist = [focus];
            state.chartFocusSymbol = focus;
            state.activePreset = null;
        } else {
            btnMulti.classList.add('active');
            btnSingle.classList.remove('active');
        }
    }
    renderWatchlistChips();
    syncWatchlistWithBot();
    if (typeof updateLiveBotChart === 'function') updateLiveBotChart();
}

function updatePresetButtonStyles() {
    const presetBtns = document.querySelectorAll('.btn-preset-scanner');
    presetBtns.forEach(btn => {
        const p = btn.getAttribute('data-preset');
        if (state.watchlistMode === 'multi' && p && p === state.activePreset) {
            btn.classList.add('active-preset');
        } else {
            btn.classList.remove('active-preset');
        }
    });

    const quickCoinBtns = document.querySelectorAll('.btn-quick-coin');
    quickCoinBtns.forEach(btn => {
        const c = btn.getAttribute('data-coin');
        if (c && c === state.chartFocusSymbol) {
            btn.classList.add('active-coin');
        } else {
            btn.classList.remove('active-coin');
        }
    });
}
window.updatePresetButtonStyles = updatePresetButtonStyles;

function setChartFocus(symbol) {
    const sym = (symbol || '').toUpperCase().trim();
    if (!sym) return;
    state.chartFocusSymbol = sym;
    if (state.watchlistMode === 'single') {
        state.botWatchlist = [sym];
        state.activePreset = null;
        syncWatchlistWithBot();
    }
    renderWatchlistChips();
    if (typeof updateLiveBotChart === 'function') updateLiveBotChart();
}
window.setChartFocus = setChartFocus;

function renderWatchlistChips() {
    const container = document.getElementById('active-coins-list');
    const badge = document.getElementById('watchlist-count-badge');
    const btnStart = document.getElementById('btn-start-bot');

    if (!container) return;

    container.innerHTML = '';
    const count = state.botWatchlist.length;

    if (count === 0) {
        container.innerHTML = `<span style="font-size: 0.8rem; color: #94A3B8; font-style: italic;">Belum ada koin dipilih. Cari atau klik koin di bawah...</span>`;
    } else if (state.watchlistMode === 'single') {
        const sym = state.botWatchlist[0] || state.chartFocusSymbol || 'BTCUSDT';
        state.chartFocusSymbol = sym;
        const pill = document.createElement('div');
        pill.className = `coin-tag-pill focus-single active-chart`;
        pill.innerHTML = `
            <span style="display: inline-flex; align-items: center; gap: 6px; color: #FFFFFF;">
                <i class="fa-solid fa-chart-line" style="color: #FFFFFF;"></i> <strong>${sym}</strong>
                <span style="font-size: 0.7rem; background: rgba(255,255,255,0.25); color: #FFFFFF; font-weight: 700; padding: 2px 6px; border-radius: 4px;">Fokus Single Pair & Chart</span>
            </span>
        `;
        container.appendChild(pill);
    } else {
        // Multi-pair Mode
        if (count > 25) {
            // High-Performance Universe Mode Summary View (e.g. 368 coins)
            const summaryBox = document.createElement('div');
            summaryBox.style.cssText = 'display: flex; flex-direction: column; gap: 8px; width: 100%; background: #F8FAFC; border: 1px solid #CBD5E1; border-radius: 8px; padding: 10px 14px;';
            
            const activeChartSym = state.chartFocusSymbol || state.botWatchlist[0] || 'BTCUSDT';
            
            summaryBox.innerHTML = `
                <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px;">
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <span style="background: linear-gradient(135deg, #FF6A00 0%, #EA580C 100%); color: #FFFFFF; padding: 3px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 800;"><i class="fa-solid fa-bolt"></i> AUTO-HUNT UNIVERSE</span>
                        <strong style="color: #0F172A; font-size: 0.88rem;">${count} Koin Binance Perpetual Aktif Di-Scan (Maks 10 Posisi Simultan)</strong>
                    </div>
                    <div style="display: flex; align-items: center; gap: 6px; font-size: 0.78rem; color: #475569;">
                        <span>Chart Focus:</span>
                        <span style="background: #0F172A; color: #FFFFFF; padding: 2px 8px; border-radius: 4px; font-weight: 800;"><i class="fa-solid fa-eye" style="color: #FF6A00;"></i> ${activeChartSym}</span>
                    </div>
                </div>
                <div style="display: flex; align-items: center; gap: 6px; flex-wrap: wrap; margin-top: 4px;">
                    <span style="font-size: 0.72rem; color: #475569; font-weight: 700;">Ganti Chart:</span>
                    ${state.botWatchlist.slice(0, 10).map(s => `
                        <button type="button" onclick="setChartFocus('${s}')" class="btn-quick-coin ${s === activeChartSym ? 'active-coin' : ''}" style="font-size: 0.72rem; padding: 2px 6px;">${s}</button>
                    `).join('')}
                    <span style="font-size: 0.72rem; color: #64748B; font-weight: 700; background: #FFFFFF; border: 1px solid #CBD5E1; padding: 2px 8px; border-radius: 4px;">+${count - 10} koin lainnya dipindai di background</span>
                </div>
            `;
            container.appendChild(summaryBox);
        } else {
            // Standard Multi-pair Chips (up to 25 coins)
            state.botWatchlist.forEach(sym => {
                const isChartFocus = (sym === state.chartFocusSymbol);
                const pill = document.createElement('div');
                pill.className = `coin-tag-pill ${isChartFocus ? 'active-chart' : ''}`;
                pill.innerHTML = `
                    <span onclick="setChartFocus('${sym}')" style="cursor: pointer; display: inline-flex; align-items: center; gap: 5px;" title="Klik untuk fokus chart pada ${sym}">
                        ${isChartFocus ? '<i class="fa-solid fa-eye" style="color: #FFFFFF;"></i> ' : ''}<strong>${sym}</strong>
                        ${isChartFocus ? '<span style="font-size: 0.68rem; background: rgba(255,255,255,0.28); color: #FFFFFF; font-weight: 800; padding: 1px 5px; border-radius: 4px;">Chart</span>' : ''}
                    </span>
                    <button type="button" class="coin-tag-remove" onclick="removeCoinFromWatchlist('${sym}')" title="Hapus ${sym}">×</button>
                `;
                container.appendChild(pill);
            });
        }
    }

    if (badge) {
        if (state.watchlistMode === 'single') {
            badge.textContent = `1 Koin Terpilih (${state.chartFocusSymbol || state.botWatchlist[0] || 'BTCUSDT'})`;
        } else {
            badge.textContent = `${count} Koin Terpilih (Multi-Pair)`;
        }
    }

    if (btnStart) {
        if (state.watchlistMode === 'single' || count === 1) {
            const sym = state.botWatchlist[0] || state.chartFocusSymbol || 'BTCUSDT';
            btnStart.innerHTML = `<i class="fa-solid fa-play"></i> START BOT AUTOMATION (${sym})`;
        } else if (count === 0) {
            btnStart.innerHTML = `<i class="fa-solid fa-play"></i> START BOT (PILIH KOIN)`;
        } else {
            btnStart.innerHTML = `<i class="fa-solid fa-play"></i> START BOT (${count} PAIRS AUTO-HUNT)`;
        }
    }

    updatePresetButtonStyles();
}

function onSearchCoinInput(query) {
    const rawVal = (query || '').trim();
    const val = rawVal.toUpperCase();
    const dropdown = document.getElementById('coin-search-dropdown');
    const btnClear = document.getElementById('btn-clear-coin-search');

    if (btnClear) {
        btnClear.style.display = val.length > 0 ? 'inline-block' : 'none';
    }

    if (!dropdown) return;

    if (!val) {
        dropdown.style.display = 'none';
        dropdown.innerHTML = '';
        return;
    }

    const pool = (state.allSymbols && state.allSymbols.length > 0) ? state.allSymbols : DEFAULT_BINANCE_SYMBOLS;
    const valWithUsdt = val.endsWith('USDT') ? val : `${val}USDT`;

    // Filter database
    const matches = pool.filter(item => {
        const sym = (item.symbol || '').toUpperCase();
        const base = (item.baseAsset || '').toUpperCase();
        return sym === val || sym === valWithUsdt || sym.startsWith(val) || sym.includes(val) || base === val || base.startsWith(val) || base.includes(val);
    }).sort((a, b) => {
        const aSym = (a.symbol || '').toUpperCase();
        const bSym = (b.symbol || '').toUpperCase();
        if (aSym === valWithUsdt) return -1;
        if (bSym === valWithUsdt) return 1;
        if (aSym.startsWith(val) && !bSym.startsWith(val)) return -1;
        if (bSym.startsWith(val) && !aSym.startsWith(val)) return 1;
        return aSym.localeCompare(bSym);
    }).slice(0, 30);

    dropdown.innerHTML = '';

    if (matches.length === 0) {
        dropdown.innerHTML = `
            <div style="padding: 1rem; text-align: center; color: #EF4444; font-size: 0.82rem; font-weight: 600;">
                <i class="fa-solid fa-circle-exclamation"></i> Koin "<strong>${val}</strong>" tidak terdaftar di pasar Binance Futures.
            </div>
        `;
        dropdown.style.display = 'block';
        return;
    }

    matches.forEach(item => {
        const isSelected = state.botWatchlist.includes(item.symbol);
        const row = document.createElement('div');
        row.className = 'search-result-item';
        row.innerHTML = `
            <div>
                <span class="result-sym">${item.symbol}</span>
                <span class="result-base">${item.baseAsset || item.symbol.replace('USDT', '')} Perpetual</span>
            </div>
            <button type="button" class="result-add-btn" style="${isSelected ? 'background: #10B981; color: white; border-color: #10B981;' : ''}">
                ${isSelected ? '✓ Aktif' : '+ Pilih'}
            </button>
        `;
        row.onclick = () => {
            addCoinToWatchlist(item.symbol);
            clearSearchInput();
        };
        dropdown.appendChild(row);
    });

    dropdown.style.display = 'block';
}

function clearSearchInput() {
    const input = document.getElementById('bot-coin-search-input');
    const dropdown = document.getElementById('coin-search-dropdown');
    const btnClear = document.getElementById('btn-clear-coin-search');
    if (input) input.value = '';
    if (dropdown) {
        dropdown.style.display = 'none';
        dropdown.innerHTML = '';
    }
    if (btnClear) btnClear.style.display = 'none';
}

function addCoinToWatchlist(symbol) {
    const sym = (symbol || '').toUpperCase().trim();
    if (!sym) return;

    // STRICT VALIDATION: Hanya koin resmi yang ada di Binance Futures yang boleh dimasukkan
    const validItem = (state.allSymbols || []).find(s => s.symbol === sym);
    if (!validItem) {
        alert(`Koin "${sym}" tidak valid atau tidak terdaftar di bursa Binance Futures!`);
        return;
    }

    state.chartFocusSymbol = validItem.symbol;

    if (state.watchlistMode === 'single') {
        state.botWatchlist = [validItem.symbol];
    } else {
        if (!state.botWatchlist.includes(validItem.symbol)) {
            state.botWatchlist.push(validItem.symbol);
        }
    }
    renderWatchlistChips();
    syncWatchlistWithBot();
    if (typeof updateLiveBotChart === 'function') updateLiveBotChart();
}

function removeCoinFromWatchlist(symbol) {
    const sym = symbol.toUpperCase().trim();
    state.botWatchlist = state.botWatchlist.filter(s => s !== sym);
    if (state.chartFocusSymbol === sym) {
        state.chartFocusSymbol = state.botWatchlist[0] || 'BTCUSDT';
    }
    renderWatchlistChips();
    syncWatchlistWithBot();
    if (typeof updateLiveBotChart === 'function') updateLiveBotChart();
}

function clearAllCoins() {
    state.botWatchlist = [];
    state.chartFocusSymbol = 'BTCUSDT';
    renderWatchlistChips();
    syncWatchlistWithBot();
    if (typeof updateLiveBotChart === 'function') updateLiveBotChart();
}

function quickSelectCoin(symbol) {
    addCoinToWatchlist(symbol);
}

async function syncWatchlistWithBot() {
    if (state.botWatchlist.length === 0) return;
    try {
        await fetch('/api/bot/update_watchlist', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ watchlist: state.botWatchlist })
        });
    } catch (e) {
        console.error('Error updating bot watchlist:', e);
    }
}

// Close search dropdown when clicking outside
document.addEventListener('click', (e) => {
    const container = document.querySelector('.coin-search-box-container');
    const dropdown = document.getElementById('coin-search-dropdown');
    if (dropdown && container && !container.contains(e.target)) {
        dropdown.style.display = 'none';
    }
});

function applyBotWatchlistPreset(presetKey) {
    let pool = [];
    const activeStrat = state.selectedStrategy || (document.getElementById('bot-strategy-select') ? document.getElementById('bot-strategy-select').value : 'price_ema_7');

    if (presetKey === 'top_10_pnl' || presetKey === 'top_10_roi') {
        if (state.matrixData && state.matrixData.matrix_rows && state.matrixData.matrix_rows.length > 0) {
            // Urutkan koin 100% PERSIS sesuai tabel matriks (Net PnL tertinggi)
            const sorted = [...state.matrixData.matrix_rows].sort((a, b) => (b.net_profit || 0) - (a.net_profit || 0));
            pool = sorted.slice(0, 10).map(r => r.symbol);
        } else {
            // Fallback default koin terbukti profitable
            pool = ["XTZUSDT", "GUSDT", "ARUSDT", "ENAUSDT", "NEARUSDT", "SUIUSDT", "DOGEUSDT", "1000PEPEUSDT", "SOLUSDT", "AVAXUSDT"];
        }
    } else if (state.pairPresets && state.pairPresets[presetKey] && state.pairPresets[presetKey].length > 0) {
        pool = state.pairPresets[presetKey];
    } else if (presetKey === 'top_12') {
        pool = ["ETHUSDT", "BTCUSDT", "SOLUSDT", "DOGEUSDT", "SUIUSDT", "NEARUSDT", "BNBUSDT", "1000PEPEUSDT", "AVAXUSDT", "LINKUSDT", "XRPUSDT", "ADAUSDT"];
    } else if (presetKey === 'top_25') {
        pool = (state.pairPresets && state.pairPresets.top_25) || ["ETHUSDT", "BTCUSDT", "SOLUSDT", "DOGEUSDT", "SUIUSDT", "NEARUSDT", "BNBUSDT", "1000PEPEUSDT", "AVAXUSDT", "LINKUSDT", "XRPUSDT", "ADAUSDT", "APTUSDT", "ARBUSDT", "OPUSDT", "INJUSDT", "TIAUSDT", "RENDERUSDT", "FETUSDT", "TAOUSDT", "SEIUSDT", "WIFUSDT", "SHIBUSDT", "DOTUSDT", "LTCUSDT"];
    } else if (presetKey === 'top_50') {
        pool = (state.pairPresets && state.pairPresets.top_50) || [];
    } else if (presetKey === 'all_coins') {
        pool = (state.pairPresets && state.pairPresets.all_coins) || (state.allSymbols || []).map(s => s.symbol);
    }
    
    if (pool.length > 0) {
        state.watchlistMode = 'multi';
        state.activePreset = presetKey;
        const btnSingle = document.getElementById('mode-single-coin');
        const btnMulti = document.getElementById('mode-multi-coin');
        if (btnSingle && btnMulti) {
            btnMulti.classList.add('active');
            btnSingle.classList.remove('active');
        }
        state.botWatchlist = [...pool];
        // Set chart focus directly to the #1 top coin in the pool
        state.chartFocusSymbol = pool[0];
        renderWatchlistChips();
        syncWatchlistWithBot();
        if (typeof updateLiveBotChart === 'function') updateLiveBotChart();
    }
}

function syncTop10PnlToBotWatchlist() {
    // 1. Sync strategy select in Bot Tab
    const botStratSelect = document.getElementById('bot-strategy-select');
    if (botStratSelect && state.selectedStrategy) {
        botStratSelect.value = state.selectedStrategy;
    }
    // 2. Sync timeframe select in Bot Tab
    const botTfSelect = document.getElementById('bot-timeframe-select');
    if (botTfSelect && state.selectedTimeframe) {
        botTfSelect.value = state.selectedTimeframe;
    }
    // 3. Apply Top 10 PnL
    applyBotWatchlistPreset('top_10_pnl');
    switchTab('bot');
    const stratName = (state.matrixData && state.matrixData.strategy_meta && state.matrixData.strategy_meta.name) || 'Strategi Terpilih';
    const topCount = state.botWatchlist.length;
    alert(`✅ BERHASIL DISINKRONISASI 100% PERSIS MATRIKS!\n\nTop ${topCount} Koin Cuan Tertinggi:\n${state.botWatchlist.join(', ')}\n\nStrategi & Timeframe di Live Bot otomatis diselaraskan dengan hasil Backtest.`);
}

function onCustomEntrySizeChange(val) {
    const num = parseFloat(val);
    const select = document.getElementById('bot-risk-select');
    const badge = document.getElementById('entry-size-mode-badge');
    if (select) {
        // Check if matches an existing fixed option
        const matchOpt = Array.from(select.options).find(o => o.value === `fixed_${num}`);
        if (matchOpt) {
            select.value = `fixed_${num}`;
        } else {
            select.value = 'custom';
        }
    }
    if (badge) {
        badge.textContent = num ? `$${num} USDT / Posisi` : 'Nominal Dollar ($)';
        badge.style.color = '#10B981';
    }
}

function onRiskPresetSelect(val) {
    const input = document.getElementById('bot-entry-size-input');
    const badge = document.getElementById('entry-size-mode-badge');
    if (val.startsWith('fixed_')) {
        const num = val.replace('fixed_', '');
        if (input) input.value = num;
        if (badge) {
            badge.textContent = `Fixed $${num} USDT`;
            badge.style.color = '#10B981';
        }
    } else if (val === 'custom') {
        if (input) input.focus();
        if (badge) {
            badge.textContent = 'Ketik Bebas ($)';
            badge.style.color = '#FF6A00';
        }
    } else if (val === '0.20') {
        if (input) input.value = 1000;
        if (badge) {
            badge.textContent = '20% Modal (~$2.5k-$3k Size)';
            badge.style.color = '#3B82F6';
        }
    } else if (val === '0.10') {
        if (input) input.value = 500;
        if (badge) {
            badge.textContent = '10% Modal (~$1.5k Size)';
            badge.style.color = '#3B82F6';
        }
    } else if (val === '0.05') {
        if (input) input.value = 250;
        if (badge) {
            badge.textContent = '5% Modal (~$750 Size)';
            badge.style.color = '#3B82F6';
        }
    }
}

window.setWatchlistMode = setWatchlistMode;
window.onSearchCoinInput = onSearchCoinInput;
window.clearSearchInput = clearSearchInput;
window.addCoinToWatchlist = addCoinToWatchlist;
window.removeCoinFromWatchlist = removeCoinFromWatchlist;
window.clearAllCoins = clearAllCoins;
window.quickSelectCoin = quickSelectCoin;
window.applyBotWatchlistPreset = applyBotWatchlistPreset;
window.syncTop10PnlToBotWatchlist = syncTop10PnlToBotWatchlist;
window.onCustomEntrySizeChange = onCustomEntrySizeChange;
window.onRiskPresetSelect = onRiskPresetSelect;

function updateGlossaryCard() {
    const strat = state.strategies.find(s => s.id === state.selectedStrategy);
    if (!strat) return;

    document.getElementById('glossary-style-badge').textContent = strat.style;
    document.getElementById('glossary-style-badge').style.borderColor = strat.style_badge_color || '#10b981';
    document.getElementById('glossary-style-badge').style.color = strat.style_badge_color || '#10b981';
    document.getElementById('glossary-style-badge').style.backgroundColor = `${strat.style_badge_color}1a` || 'rgba(16, 185, 129, 0.15)';
    document.getElementById('glossary-strategy-name').textContent = strat.name;
    document.getElementById('glossary-file-name').innerHTML = `<i class="fa-brands fa-python"></i> ${strat.file}`;
    document.getElementById('glossary-description').textContent = strat.description;

    const longList = document.getElementById('glossary-entry-long');
    longList.innerHTML = '';
    (strat.entry_long || []).forEach(r => {
        const li = document.createElement('li');
        li.textContent = r;
        longList.appendChild(li);
    });

    const shortList = document.getElementById('glossary-entry-short');
    shortList.innerHTML = '';
    (strat.entry_short || []).forEach(r => {
        const li = document.createElement('li');
        li.textContent = r;
        shortList.appendChild(li);
    });

    const exitList = document.getElementById('glossary-exit-rules');
    exitList.innerHTML = '';
    (strat.exit_rules || []).forEach(r => {
        const li = document.createElement('li');
        li.textContent = r;
        exitList.appendChild(li);
    });
}

// --- 6. RUN MATRIX BACKTEST ---
async function runMasterMatrix() {
    if (state.isLoading) return;
    state.isLoading = true;
    btnRunMatrix.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Menghitung...';
    btnRunMatrix.disabled = true;

    try {
        let selectedPairs = [];
        if (state.selectedPairScope === 'top_10_pnl') {
            if (state.matrixData && state.matrixData.matrix_rows && state.matrixData.matrix_rows.length > 0) {
                const sorted = [...state.matrixData.matrix_rows].sort((a, b) => (b.net_profit || 0) - (a.net_profit || 0));
                selectedPairs = sorted.slice(0, 10).map(r => r.symbol);
            } else {
                selectedPairs = ["NEARUSDT", "SUIUSDT", "DOGEUSDT", "1000PEPEUSDT", "BNBUSDT", "ETHUSDT", "SOLUSDT", "AVAXUSDT", "LINKUSDT", "RENDERUSDT"];
            }
        } else if (state.pairPresets && state.pairPresets[state.selectedPairScope] && state.pairPresets[state.selectedPairScope].length > 0) {
            selectedPairs = state.pairPresets[state.selectedPairScope];
        } else if (state.pairPresets && state.pairPresets.top_12 && state.pairPresets.top_12.length > 0) {
            selectedPairs = state.pairPresets.top_12;
        }

        const countText = selectedPairs.length > 0 ? `(${selectedPairs.length} Pair)` : '';
        matrixTbody.innerHTML = `
            <tr>
                <td colspan="15" class="loading-cell">
                    <i class="fa-solid fa-spinner fa-spin"></i> Mengambil data tick dan menghitung matriks ${countText} secara paralel...
                </td>
            </tr>
        `;

        const payload = {
            strategy: state.selectedStrategy,
            interval: state.selectedTimeframe,
            symbols: selectedPairs,
            pairs: selectedPairs,
            leverage: state.selectedLeverage,
            risk_pct: state.selectedRisk,
            candles: 3000
        };

        const res = await fetch('/api/matrix', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await res.json();
        if (data.success) {
            state.matrixData = data;
            renderMatrixTable(data);
            updatePortfolioKPIs(data);
        } else {
            matrixTbody.innerHTML = `<tr><td colspan="15" class="error-cell"><i class="fa-solid fa-triangle-exclamation"></i> Gagal: ${data.error}</td></tr>`;
        }
    } catch (e) {
        matrixTbody.innerHTML = `<tr><td colspan="15" class="error-cell"><i class="fa-solid fa-triangle-exclamation"></i> Terjadi kesalahan koneksi server</td></tr>`;
    } finally {
        state.isLoading = false;
        btnRunMatrix.innerHTML = '<i class="fa-solid fa-rotate"></i> Hitung Matriks';
        btnRunMatrix.disabled = false;
    }
}

// --- 7. RENDER MATRIX TABLE ---
function formatExactPrice(val) {
    if (val === undefined || val === null || isNaN(val)) return '-';
    const num = Number(val);
    if (num === 0) return '0.00';
    if (num < 0.0001) return num.toFixed(8);
    if (num < 0.01) return num.toFixed(6);
    if (num < 1.0) return num.toFixed(4);
    return num.toFixed(2);
}

function formatIndicatorChips(indObj) {
    if (!indObj || Object.keys(indObj).length === 0) return '<span class="text-muted">-</span>';
    let chipsHtml = '<div class="ind-chips-container">';
    
    // Prioritaskan nama-nama label yang ramah dibaca
    const labelMap = {
        'ema_fast': 'EMA Fast',
        'ema_slow': 'EMA Slow',
        'ema_trend': 'EMA 200',
        'ema7': 'EMA 7',
        'ema25': 'EMA 25',
        'ema99': 'EMA 99',
        'ema200': 'EMA 200',
        'supertrend': 'Supertrend',
        'rsi': 'RSI',
        'upper_bb': 'Upper BB',
        'mid_bb': 'Mid BB',
        'lower_bb': 'Lower BB',
        'adx': 'ADX'
    };

    for (const [k, v] of Object.entries(indObj)) {
        const label = labelMap[k] || k.toUpperCase();
        let chipClass = 'chip-neutral';
        if (k.includes('7') || k.includes('fast')) chipClass = 'chip-fast';
        else if (k.includes('25') || k.includes('slow') || k.includes('supertrend')) chipClass = 'chip-medium';
        else if (k.includes('99') || k.includes('200') || k.includes('trend')) chipClass = 'chip-slow';

        chipsHtml += `<span class="ind-chip ${chipClass}"><span class="ind-label">${label}:</span> <strong class="ind-val">${v}</strong></span>`;
    }
    chipsHtml += '</div>';
    return chipsHtml;
}

function renderMatrixTable(data) {
    const thead = document.getElementById('matrix-thead');
    const tbody = document.getElementById('matrix-tbody');
    const tfoot = document.getElementById('matrix-tfoot');

    const filteredMonths = (data.months || []).filter(m => {
        if (state.selectedYear === 'ALL') return true;
        return m.year === state.selectedYear;
    });

    let theadHtml = `
        <tr>
            <th class="sticky-col">PAIR</th>
            <th>HARGA REAL</th>
            <th>INDIKATOR REALTIME</th>
            <th>TOTAL NET PNL</th>
            <th>WIN RATE</th>
            <th>PROFIT FACTOR</th>
            <th>MAX DD</th>
            <th>TRADES</th>
            <th>DETAIL</th>
    `;
    filteredMonths.forEach(m => {
        theadHtml += `<th>${m.label}</th>`;
    });
    theadHtml += `</tr>`;
    thead.innerHTML = theadHtml;

    tbody.innerHTML = '';
    data.matrix_rows.forEach(row => {
        const tr = document.createElement('tr');
        const pnl = row.net_profit;
        const pnlColor = pnl > 0 ? 'text-profit' : (pnl < 0 ? 'text-loss' : 'text-muted');
        const pnlSign = pnl > 0 ? '+' : (pnl < 0 ? '-' : '');
        const pnlAbs = Math.abs(pnl).toFixed(2);
        const roiSign = row.roi_pct > 0 ? '+' : (row.roi_pct < 0 ? '-' : '');
        const roiAbs = Math.abs(row.roi_pct).toFixed(1);
        const lastPriceFormatted = row.last_price ? `$${formatExactPrice(row.last_price)}` : '-';
        const indChips = formatIndicatorChips(row.latest_indicators);

        let rowHtml = `
            <td class="sticky-col pair-name">
                <strong>${row.symbol}</strong>
            </td>
            <td class="font-mono real-price-cell" id="real-price-${row.symbol}" data-price="${row.last_price || 0}">
                <strong>${lastPriceFormatted}</strong>
            </td>
            <td class="indicators-cell">
                ${indChips}
            </td>
            <td class="${pnlColor} net-pnl-cell">
                ${pnlSign}$${pnlAbs} <span class="roi-badge ${pnlColor}">(${roiSign}${roiAbs}%)</span>
            </td>
            <td class="winrate-cell"><strong>${row.win_rate.toFixed(1)}%</strong></td>
            <td>${row.profit_factor.toFixed(2)}</td>
            <td class="text-loss">-${Math.abs(row.max_drawdown).toFixed(1)}%</td>
            <td>${row.total_trades}</td>
            <td>
                <button class="btn-log-action" onclick="window.openTradeLogModal('${row.symbol}')">
                    <i class="fa-regular fa-eye"></i> Log
                </button>
            </td>
        `;

        filteredMonths.forEach(m => {
            const mVal = row.monthly_pnl[m.key];
            if (mVal === undefined || mVal === null) {
                rowHtml += `<td class="month-cell text-muted">-</td>`;
            } else {
                const mColor = mVal > 0 ? 'month-profit' : (mVal < 0 ? 'month-loss' : 'month-zero');
                const mSign = mVal > 0 ? '+' : (mVal < 0 ? '-' : '');
                rowHtml += `<td class="month-cell ${mColor}">${mSign}$${Math.abs(mVal).toFixed(2)}</td>`;
            }
        });

        tr.innerHTML = rowHtml;
        tbody.appendChild(tr);
    });

    const summary = data.portfolio_summary;
    const totPnl = summary.total_net_pnl;
    const totColor = totPnl > 0 ? 'text-profit' : (totPnl < 0 ? 'text-loss' : 'text-muted');
    const totSign = totPnl > 0 ? '+' : (totPnl < 0 ? '-' : '');

    let tfootHtml = `
        <tr class="footer-total-row">
            <td class="sticky-col"><strong>TOTAL PORTOFOLIO</strong></td>
            <td>-</td>
            <td>-</td>
            <td class="${totColor} total-pnl-cell">
                <strong>${totSign}$${Math.abs(totPnl).toFixed(2)}</strong>
            </td>
            <td><strong>${summary.win_rate.toFixed(1)}%</strong></td>
            <td>-</td>
            <td>-</td>
            <td><strong>${summary.total_trades}</strong></td>
            <td>-</td>
    `;

    filteredMonths.forEach(m => {
        const mTot = summary.monthly_totals[m.key] || 0.0;
        const mColor = mTot > 0 ? 'month-profit' : (mTot < 0 ? 'month-loss' : 'month-zero');
        const mSign = mTot > 0 ? '+' : (mTot < 0 ? '-' : '');
        tfootHtml += `<td class="month-cell ${mColor}"><strong>${mSign}$${Math.abs(mTot).toFixed(2)}</strong></td>`;
    });

    tfootHtml += `</tr>`;
    tfoot.innerHTML = tfootHtml;
}

function updatePortfolioKPIs(data) {
    const summary = data.portfolio_summary;
    const totPnl = summary.total_net_pnl;
    const pnlEl = document.getElementById('val-portfolio-pnl');
    pnlEl.textContent = `${totPnl >= 0 ? '+' : '-'}$${Math.abs(totPnl).toFixed(2)}`;
    pnlEl.className = `metric-value ${totPnl >= 0 ? 'text-profit' : 'text-loss'}`;

    document.getElementById('val-portfolio-winrate').textContent = `${summary.win_rate.toFixed(1)}%`;
    document.getElementById('val-portfolio-trades').textContent = `${summary.total_trades} Total Trades Selesai`;

    if (data.matrix_rows && data.matrix_rows.length > 0) {
        const best = data.matrix_rows[0];
        document.getElementById('val-best-pair').textContent = best.symbol;
        const bSign = best.net_profit >= 0 ? '+' : '-';
        document.getElementById('val-best-pair-pnl').textContent = `${bSign}$${Math.abs(best.net_profit).toFixed(2)} (${best.win_rate.toFixed(1)}% Win Rate)`;
    }

    const monthTotals = Object.values(summary.monthly_totals);
    const greenCount = monthTotals.filter(v => v > 0).length;
    const totalCount = monthTotals.length;
    const pct = totalCount > 0 ? ((greenCount / totalCount) * 100).toFixed(0) : 0;
    document.getElementById('val-green-months').textContent = `${greenCount} / ${totalCount} (${pct}%)`;
}

// --- 8. TRADE LOG MODAL ---
window.closeTradeLogModal = function() {
    const modal = document.getElementById('trade-modal');
    if (modal) modal.style.display = 'none';
};

window.closeSimulatorModal = function() {
    const simModal = document.getElementById('simulator-modal');
    if (simModal) simModal.style.display = 'none';
};

window.openTradeLogModal = function(symbol) {
    if (!state.matrixData || !state.matrixData.matrix_rows) return;
    const row = state.matrixData.matrix_rows.find(r => r.symbol === symbol);
    if (!row) return;

    modalPairTitle.textContent = `Detail Riwayat Trade [${symbol}] - Total ${row.trades.length} Posisi`;
    modalTradesTbody.innerHTML = '';

    if (!row.trades || row.trades.length === 0) {
        modalTradesTbody.innerHTML = `<tr><td colspan="7" class="loading-cell">Tidak ada trade yang tereksekusi pada periode ini.</td></tr>`;
    } else {
        row.trades.forEach((t, idx) => {
            const tr = document.createElement('tr');
            const typeBadge = t.type === 'LONG' 
                ? '<span class="tag-badge long" style="font-size: 0.68rem; padding: 2px 6px;">LONG</span>' 
                : '<span class="tag-badge short" style="font-size: 0.68rem; padding: 2px 6px;">SHORT</span>';
            const pnlColor = t.net_pnl > 0 ? 'text-profit' : (t.net_pnl < 0 ? 'text-loss' : 'text-muted');
            const pnlSign = t.net_pnl > 0 ? '+' : (t.net_pnl < 0 ? '-' : '');

            function formatExactPrice(val) {
                if (val === undefined || val === null || isNaN(val)) return '-';
                const num = Number(val);
                if (num === 0) return '0.00';
                if (num < 0.0001) return num.toFixed(8);
                if (num < 0.01) return num.toFixed(6);
                if (num < 1.0) return num.toFixed(4);
                return num.toFixed(2);
            }

            const notionalStr = t.notional_size ? `$${Number(t.notional_size).toFixed(2)}` : (t.quantity ? `${Number(t.quantity).toFixed(3)} Qty` : '-');
            const marginStr = t.margin_used ? `$${Number(t.margin_used).toFixed(2)}` : '-';

            let reasonClass = '';
            const rLower = (t.exit_reason || '').toLowerCase();
            if (rLower.includes('stop loss') || rLower.includes('sl') || rLower.includes('loss')) {
                reasonClass = 'sl';
            } else if (rLower.includes('take profit') || rLower.includes('tp') || rLower.includes('profit')) {
                reasonClass = 'tp';
            } else if (rLower.includes('signal') || rLower.includes('trend')) {
                reasonClass = 'signal';
            }

            tr.innerHTML = `
                <td>
                    <div style="font-weight: 700; font-size: 0.84rem; color: #1E293B; margin-bottom: 2px;">#${idx + 1}</div>
                    <div>${typeBadge}</div>
                </td>
                <td>
                    <div class="trade-subtext"><i class="fa-regular fa-clock" style="font-size: 0.68rem;"></i> ${t.entry_time}</div>
                    <div class="trade-maintext font-mono">$${formatExactPrice(t.entry_price)}</div>
                </td>
                <td>
                    <div class="trade-maintext font-mono text-notional">${notionalStr}</div>
                    <div class="trade-subtext">Margin: <span class="font-mono" style="font-weight: 600;">${marginStr}</span></div>
                </td>
                <td>
                    <div class="trade-subtext"><i class="fa-regular fa-clock" style="font-size: 0.68rem;"></i> ${t.exit_time}</div>
                    <div class="trade-maintext font-mono">$${formatExactPrice(t.exit_price)}</div>
                </td>
                <td>
                    <div class="trade-subtext" style="font-weight: 600; color: #475569;"><i class="fa-solid fa-stopwatch" style="font-size: 0.68rem;"></i> ${t.duration}</div>
                    <div style="margin-top: 3px;"><span class="trade-reason-badge ${reasonClass}">${t.exit_reason || '-'}</span></div>
                </td>
                <td>
                    <div class="trade-maintext ${pnlColor}">${pnlSign}$${Math.abs(t.net_pnl).toFixed(2)}</div>
                    <div class="trade-subtext ${pnlColor}" style="font-weight: 600;">ROI: ${pnlSign}${Math.abs(t.pnl_pct).toFixed(2)}%</div>
                </td>
                <td style="text-align: right;">
                    <div class="trade-maintext font-mono">$${t.capital_after.toFixed(2)}</div>
                    <div class="trade-subtext">Wallet</div>
                </td>
            `;
            modalTradesTbody.appendChild(tr);
        });
    }

    tradeModal.style.display = 'flex';
};

// --- 9. LIVE FUNDING RATE SNIPER LOGIC ---
async function loadLiveFundingRates() {
    try {
        fundingTbody.innerHTML = `
            <tr>
                <td colspan="10" class="loading-cell">
                    <i class="fa-solid fa-spinner fa-spin"></i> Menarik ranking data real-time live funding rates dari 980+ pair Binance...
                </td>
            </tr>
        `;
        const res = await fetch('/api/funding/live');
        const data = await res.json();
        if (data.success && data.pairs) {
            state.fundingData = data.pairs;
            filterAndRenderFundingTable();
            updateTopTargetHero(data.pairs);
        }
    } catch (e) {
        fundingTbody.innerHTML = `<tr><td colspan="10" class="error-cell"><i class="fa-solid fa-triangle-exclamation"></i> Gagal menarik data live funding rate.</td></tr>`;
    }
}

function updateTopTargetHero(pairs) {
    if (!pairs || pairs.length === 0) return;
    const top = pairs[0];
    topTargetSymbol.textContent = top.symbol;
    topTargetRate.textContent = `${top.funding_rate_pct >= 0 ? '+' : ''}${top.funding_rate_pct.toFixed(4)}%`;
    const sign = top.net_profit_1k >= 0 ? '+' : '-';
    topTargetPayout.textContent = `Estimasi Net Profit Hit & Run: ${sign}$${Math.abs(top.net_profit_1k).toFixed(2)} per $1,000 (${top.apy.toFixed(1)}% APY)`;
}

    state.fundingFilter = 'positive';
    state.fundingFilterSpot = 'spot_only';

    const fundingFilterSpotEl = document.getElementById('funding-filter-spot');
    if (fundingFilterSpotEl) {
        fundingFilterSpotEl.addEventListener('change', (e) => {
            state.fundingFilterSpot = e.target.value;
            filterAndRenderFundingTable();
        });
    }

function filterAndRenderFundingTable() {
    let filtered = [...state.fundingData];

    // Spot Availability filter
    if (state.fundingFilterSpot === 'spot_only') {
        filtered = filtered.filter(p => p.has_spot === true);
    } else if (state.fundingFilterSpot === 'futures_only') {
        filtered = filtered.filter(p => p.has_spot === false);
    }

    // Rate filter
    if (state.fundingFilter === 'positive') {
        filtered = filtered.filter(p => p.funding_rate_pct > 0);
    } else if (state.fundingFilter === 'high_yield') {
        filtered = filtered.filter(p => p.funding_rate_pct >= 0.03);
    } else if (state.fundingFilter === 'hot') {
        filtered = filtered.filter(p => p.funding_rate_pct >= 0.10);
    }

    // Search query
    if (state.fundingSearch) {
        filtered = filtered.filter(p => p.symbol.toLowerCase().includes(state.fundingSearch));
    }

    state.filteredFundingData = filtered;
    fundingPairsCount.textContent = `Menampilkan ${filtered.length} dari ${state.fundingData.length} Pair Aktif Binance`;

    fundingTbody.innerHTML = '';
    if (filtered.length === 0) {
        fundingTbody.innerHTML = `<tr><td colspan="10" class="loading-cell">Tidak ada pair yang sesuai dengan kriteria filter.</td></tr>`;
        return;
    }

    function formatCleanPrice(val) {
        if (val === undefined || val === null || isNaN(val)) return '-';
        const num = Number(val);
        if (num === 0) return '0.00';
        if (num < 0.0001) return num.toFixed(8);
        if (num < 0.01) return num.toFixed(6);
        if (num < 1.0) return num.toFixed(4);
        return num.toFixed(2);
    }

    filtered.slice(0, 50).forEach(pair => {
        const tr = document.createElement('tr');
        const rateColor = pair.funding_rate_pct > 0 ? 'text-profit' : (pair.funding_rate_pct < 0 ? 'text-loss' : 'text-muted');
        const rateSign = pair.funding_rate_pct > 0 ? '+' : '';
        const netSign = pair.net_profit_1k > 0 ? '+' : '-';
        const netColor = pair.net_profit_1k > 0 ? 'text-profit' : 'text-loss';
        const basisColor = pair.basis_pct > 0 ? 'text-profit' : (pair.basis_pct < 0 ? 'text-loss' : 'text-muted');
        const basisSign = pair.basis_pct > 0 ? '+' : '';

        const spotBadgeHtml = pair.has_spot
            ? `<span class="tag-badge" style="background: rgba(16, 185, 129, 0.15); color: #10b981; border: 1px solid #10b981;"><i class="fa-solid fa-check"></i> Spot & Futures</span>`
            : `<span class="tag-badge" style="background: rgba(244, 63, 94, 0.15); color: #f43f5e; border: 1px solid #f43f5e;"><i class="fa-solid fa-ban"></i> Futures Only</span>`;

        tr.innerHTML = `
            <td><strong>${pair.symbol}</strong></td>
            <td>${spotBadgeHtml}</td>
            <td class="${rateColor} font-mono" style="font-size: 1.05rem; font-weight: 700;">
                ${rateSign}${pair.funding_rate_pct.toFixed(4)}%
            </td>
            <td class="font-mono">${rateSign}${pair.apy.toFixed(1)}% APY</td>
            <td class="font-mono ${basisColor}" style="font-weight: 600;">
                ${basisSign}${pair.basis_pct.toFixed(3)}%
            </td>
            <td class="font-mono">$${formatCleanPrice(pair.futures_price)}</td>
            <td class="font-mono text-muted">$${formatCleanPrice(pair.spot_index_price)}</td>
            <td class="${netColor} font-mono" style="font-weight: 700;">
                ${netSign}$${Math.abs(pair.net_profit_1k).toFixed(2)}
            </td>
            <td>
                <span class="tag-badge" style="background: ${pair.status_color}22; color: ${pair.status_color}; border: 1px solid ${pair.status_color};">
                    ${pair.status}
                </span>
            </td>
            <td>
                <button class="btn-log-action" style="background: rgba(99, 102, 241, 0.2); border-color: var(--accent-indigo); color: #818cf8;" onclick='window.openFundingSimulatorFromRow(${JSON.stringify(pair).replace(/'/g, "&apos;")})'>
                    <i class="fa-solid fa-calculator"></i> Simulasi
                </button>
            </td>
        `;
        fundingTbody.appendChild(tr);
    });
}

// --- 10. SIMULATOR MODAL LOGIC ---
window.openFundingSimulatorFromRow = function(pair) {
    openFundingSimulator(pair);
};

function openFundingSimulator(pair) {
    if (!pair) return;
    simModalTitle.textContent = `Kalkulator Simulasi Hit & Run Funding [${pair.symbol}]`;
    simInputSymbol.value = pair.symbol;
    simInputRate.value = pair.funding_rate_pct.toFixed(4);
    simInputCapital.value = 1000;
    simInputIntervals.value = 1;
    calculateSimulationLive();
    simulatorModal.style.display = 'flex';
}

function calculateSimulationLive() {
    const capital = parseFloat(simInputCapital.value) || 1000;
    const ratePct = parseFloat(simInputRate.value) || 0.15;
    const intervals = parseInt(simInputIntervals.value) || 1;

    // Gross payout
    const grossPayout = capital * (ratePct / 100.0) * intervals;
    // Taker fee (0.10% roundtrip)
    const takerFee = capital * 0.0010;
    const netProfit = grossPayout - takerFee;
    const roiPct = (netProfit / capital) * 100.0;
    const apy = ratePct * 3 * 365;

    const netSign = netProfit >= 0 ? '+' : '-';
    const netColor = netProfit >= 0 ? 'text-profit' : 'text-loss';

    simGrossPayout.textContent = `+$${grossPayout.toFixed(2)}`;
    simFeeCost.textContent = `-$${takerFee.toFixed(2)}`;
    simNetProfit.textContent = `${netSign}$${Math.abs(netProfit).toFixed(2)} (${netSign}${Math.abs(roiPct).toFixed(2)}%)`;
    simNetProfit.className = `sim-val highlight ${netColor}`;
    simApyVal.textContent = `+${apy.toFixed(1)}% APY`;
}

// --- 11. EXPORT MATRIX TO CSV ---
function exportMatrixToCSV() {
    if (!state.matrixData || !state.matrixData.matrix_rows) {
        alert('Tidak ada data matriks untuk diexport.');
        return;
    }

    const data = state.matrixData;
    const filteredMonths = data.months.filter(m => {
        if (state.selectedYear === 'ALL') return true;
        return m.year === state.selectedYear;
    });

    const headers = ["Pair", "Total Net PnL (USDT)", "ROI %", "Win Rate %", "Profit Factor", "Max Drawdown %", "Total Trades", ...filteredMonths.map(m => `"${m.label}"`)];
    
    const rows = data.matrix_rows.map(row => {
        const monthVals = filteredMonths.map(m => row.monthly_pnl[m.key] !== undefined ? row.monthly_pnl[m.key] : 0.0);
        return [
            row.symbol,
            row.net_profit,
            row.roi_pct,
            row.win_rate,
            row.profit_factor,
            row.max_drawdown,
            row.total_trades,
            ...monthVals
        ];
    });

    // Add Total Portfolio Footer
    const footerMonthVals = filteredMonths.map(m => data.portfolio_summary.monthly_totals[m.key] || 0.0);
    rows.push([
        "TOTAL PORTOFOLIO",
        data.portfolio_summary.total_net_pnl,
        "-",
        data.portfolio_summary.win_rate,
        "-",
        "-",
        data.portfolio_summary.total_trades,
        ...footerMonthVals
    ]);

    let csvContent = "data:text/csv;charset=utf-8," + [headers.join(","), ...rows.map(e => e.join(","))].join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `MasterBacktestMatrix_${state.selectedStrategy}_${state.selectedTimeframe}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

// --- 12. LIVE BOT DEMO CLIENT LOGIC ---
let lastLogCount = 0;

async function loadBotStatus() {
    try {
        const res = await fetch('/api/bot/status');
        const data = await res.json();
        
        // Update Account Metrics
        const bal = data.balance || data.account || {};
        const walletBal = bal.total_wallet_balance !== undefined ? bal.total_wallet_balance : (bal.wallet_balance !== undefined ? bal.wallet_balance : 5000.0);
        const availBal = bal.available_balance !== undefined ? bal.available_balance : 5000.0;
        const unPnl = bal.total_unrealized_profit !== undefined ? bal.total_unrealized_profit : (bal.total_unrealized_pnl !== undefined ? bal.total_unrealized_pnl : 0.0);
        const positions = data.open_positions || data.positions || (data.account && data.account.positions) || [];

        const walletEl = document.getElementById('bot-wallet-balance');
        const availEl = document.getElementById('bot-available-balance');
        const pnlEl = document.getElementById('bot-floating-pnl');
        const posCountEl = document.getElementById('bot-active-positions-count');

        if (walletEl) walletEl.textContent = `$${Number(walletBal).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
        if (availEl) availEl.textContent = `$${Number(availBal).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
        
        if (pnlEl) {
            const pnlNum = Number(unPnl);
            const pnlSign = pnlNum >= 0 ? '+' : '-';
            pnlEl.textContent = `${pnlSign}$${Math.abs(pnlNum).toFixed(2)}`;
            pnlEl.className = `bot-metric-val ${pnlNum > 0 ? 'text-profit' : (pnlNum < 0 ? 'text-loss' : 'pnl-neutral')}`;
        }

        if (posCountEl) {
            posCountEl.textContent = `${positions.length} / 10 Posisi (Maks 10)`;
        }

        // Update Bot State & Buttons
        const statusBadge = document.getElementById('bot-status-badge');
        const statusText = document.getElementById('bot-status-text');
        const btnStart = document.getElementById('btn-start-bot');
        const btnStop = document.getElementById('btn-stop-bot');

        // Update Strategy Dropdown Selection ONLY when bot is actively running
        const botStratSelect = document.getElementById('bot-strategy-select');
        if (botStratSelect && data.is_running && data.active_strategy_id && document.activeElement !== botStratSelect) {
            const stratId = (data.active_strategy_id === 'price_ema_7') ? 'price_ema_crossover' : data.active_strategy_id;
            const hasOption = Array.from(botStratSelect.options).some(o => o.value === stratId);
            if (hasOption && botStratSelect.value !== stratId) {
                botStratSelect.value = stratId;
            }
        }

        // Sync Timeframe & Leverage Dropdowns
        const botTfSelect = document.getElementById('bot-timeframe-select');
        if (botTfSelect && data.is_running && data.timeframe && document.activeElement !== botTfSelect) {
            if (botTfSelect.value !== data.timeframe) botTfSelect.value = data.timeframe;
        }
        const botLevSelect = document.getElementById('bot-leverage-select');
        if (botLevSelect && data.is_running && data.leverage && document.activeElement !== botLevSelect) {
            if (botLevSelect.value !== String(data.leverage)) botLevSelect.value = String(data.leverage);
        }

        if (data.is_running) {
            // Persist to localStorage for 0ms instant load on duplicate tabs / refresh
            localStorage.setItem('bot_active_state', JSON.stringify({
                is_running: true,
                watchlist: data.watchlist || state.botWatchlist,
                active_strategy_id: data.active_strategy_id || state.selectedStrategy,
                timeframe: data.timeframe || state.selectedTimeframe,
                leverage: data.leverage || state.selectedLeverage || 3,
                risk_pct: data.risk_pct || state.selectedRisk || 'fixed_250',
                timestamp: Date.now()
            }));

            // Sync watchlist chips in state if changed on backend
            if (Array.isArray(data.watchlist) && data.watchlist.length > 0) {
                const isDiff = data.watchlist.length !== state.botWatchlist.length || 
                               data.watchlist.some((s, idx) => s !== state.botWatchlist[idx]);
                if (isDiff) {
                    state.botWatchlist = [...data.watchlist];
                    if (state.botWatchlist.length > 1) {
                        state.watchlistMode = 'multi';
                        const btnSingle = document.getElementById('mode-single-coin');
                        const btnMulti = document.getElementById('mode-multi-coin');
                        if (btnSingle && btnMulti) {
                            btnMulti.classList.add('active');
                            btnSingle.classList.remove('active');
                        }
                    }
                    if (!state.chartFocusSymbol || !state.botWatchlist.includes(state.chartFocusSymbol)) {
                        state.chartFocusSymbol = state.botWatchlist[0];
                    }
                    renderWatchlistChips();
                }
            }

            if (statusBadge) statusBadge.className = 'bot-status-badge running';
            const wl = data.watchlist || state.botWatchlist || ['BTCUSDT'];
            const wlText = wl.length > 8 ? `${wl.length} PAIRS AUTO-HUNT (${wl.slice(0, 5).join(', ')} +${wl.length - 5} lainnya)` : `${wl.length} PAIR: ${wl.join(', ')}`;
            if (statusText) statusText.innerHTML = `<span class="pulse-dot green"></span> BOT ACTIVE (SCANNING ${wlText})`;
            if (btnStart) btnStart.style.display = 'none';
            if (btnStop) btnStop.style.display = 'inline-flex';
        } else {
            localStorage.setItem('bot_active_state', JSON.stringify({
                is_running: false,
                watchlist: state.botWatchlist,
                timestamp: Date.now()
            }));
            if (statusBadge) statusBadge.className = 'bot-status-badge';
            if (statusText) statusText.innerHTML = `<span class="pulse-dot"></span> BOT STANDBY / READY`;
            if (btnStart) btnStart.style.display = 'inline-flex';
            if (btnStop) btnStop.style.display = 'none';
        }

        // Render Open Positions Table
        renderBotPositionsTable(positions);

        // Render Live Trade History Table
        renderBotTradesTable(data.binance_trades || [], data.trade_history || []);

        // Render Live Logs
        renderBotLogs(data.recent_logs || data.logs || []);

    } catch (e) {
        console.error('Error fetching bot status:', e);
    }
}

function renderBotTradesTable(binanceTrades, localTrades) {
    const tbody = document.getElementById('bot-trades-tbody');
    if (!tbody) return;

    if ((!binanceTrades || binanceTrades.length === 0) && (!localTrades || localTrades.length === 0)) {
        tbody.innerHTML = `
            <tr>
                <td colspan="9" class="empty-cell">
                    <i class="fa-regular fa-folder-open"></i> Belum ada rekaman transaksi yang dieksekusi.
                </td>
            </tr>
        `;
        return;
    }

    function formatCleanPrice(val) {
        if (val === undefined || val === null || isNaN(val)) return '-';
        const num = Number(val);
        if (num === 0) return '0.00';
        if (num < 0.0001) return num.toFixed(8);
        if (num < 0.01) return num.toFixed(6);
        if (num < 1.0) return num.toFixed(4);
        return num.toFixed(2);
    }

    tbody.innerHTML = '';
    
    // Prefer binance real trades if available, otherwise fallback to local bot trades
    if (binanceTrades && binanceTrades.length > 0) {
        binanceTrades.forEach(t => {
            const tr = document.createElement('tr');
            const isBuy = (t.side || '').toUpperCase() === 'BUY';
            const pnl = Number(t.realized_pnl || 0);
            
            // Tentukan Aksi secara cerdas (OPEN vs CLOSE, TP vs CUTLOSS)
            let actionBadge = '';
            if (Math.abs(pnl) < 1e-5) {
                // Posisi Buka Baru (Realized PnL = 0)
                if (isBuy) {
                    actionBadge = '<span class="trade-action-badge open-long"><i class="fa-solid fa-arrow-trend-up"></i> OPEN LONG</span>';
                } else {
                    actionBadge = '<span class="trade-action-badge open-short"><i class="fa-solid fa-arrow-trend-down"></i> OPEN SHORT</span>';
                }
            } else {
                // Posisi Tutup (Telah Merealisasikan PnL)
                if (isBuy) {
                    // Penutupan Posisi SHORT (dengan Buy kembali)
                    if (pnl > 0) {
                        actionBadge = '<span class="trade-action-badge close-tp"><i class="fa-solid fa-circle-check"></i> CLOSE SHORT (TP)</span>';
                    } else {
                        actionBadge = '<span class="trade-action-badge close-sl"><i class="fa-solid fa-shield-halved"></i> CLOSE SHORT (CUTLOSS)</span>';
                    }
                } else {
                    // Penutupan Posisi LONG (dengan Sell)
                    if (pnl > 0) {
                        actionBadge = '<span class="trade-action-badge close-tp"><i class="fa-solid fa-circle-check"></i> CLOSE LONG (TP)</span>';
                    } else {
                        actionBadge = '<span class="trade-action-badge close-sl"><i class="fa-solid fa-shield-halved"></i> CLOSE LONG (CUTLOSS)</span>';
                    }
                }
            }
            
            const pnlColor = pnl > 0 ? 'text-profit' : (pnl < 0 ? 'text-loss' : 'text-muted');
            const pnlText = pnl !== 0 ? `${pnl >= 0 ? '+' : ''}$${pnl.toFixed(4)}` : '$0.00';
            const feeText = t.commission ? `$${Number(t.commission).toFixed(4)}` : '$0.00';
            const quoteVal = t.quote_qty ? `$${Number(t.quote_qty).toFixed(2)}` : `$${(t.price * t.qty).toFixed(2)}`;

            tr.innerHTML = `
                <td class="font-mono text-muted">${t.time || '-'}</td>
                <td><strong>${t.symbol}</strong></td>
                <td>${actionBadge}</td>
                <td class="font-mono" style="font-weight: 700;">$${formatCleanPrice(t.price)}</td>
                <td class="font-mono">${t.qty}</td>
                <td class="font-mono">${quoteVal}</td>
                <td class="font-mono ${pnlColor}" style="font-weight: 700;">${pnlText}</td>
                <td class="font-mono text-muted">${feeText}</td>
                <td class="font-mono" style="font-size: 0.8rem; color: #818cf8;">#${t.order_id || t.id || '-'}</td>
            `;
            tbody.appendChild(tr);
        });
    } else if (localTrades && localTrades.length > 0) {
        localTrades.forEach(t => {
            const tr = document.createElement('tr');
            const isBuy = (t.side || '').toUpperCase() === 'BUY';
            const isClose = (t.action || '').toUpperCase().includes('CLOSE') || (t.type || '').toUpperCase() === 'CLOSE';
            let sideBadge = '';
            if (isClose) {
                sideBadge = isBuy
                    ? '<span class="trade-action-badge close-neutral"><i class="fa-solid fa-xmark"></i> CLOSE SHORT</span>'
                    : '<span class="trade-action-badge close-neutral"><i class="fa-solid fa-xmark"></i> CLOSE LONG</span>';
            } else {
                sideBadge = isBuy 
                    ? '<span class="trade-action-badge open-long"><i class="fa-solid fa-arrow-trend-up"></i> OPEN LONG</span>' 
                    : '<span class="trade-action-badge open-short"><i class="fa-solid fa-arrow-trend-down"></i> OPEN SHORT</span>';
            }

            tr.innerHTML = `
                <td class="font-mono text-muted">${t.timestamp || '-'}</td>
                <td><strong>${t.symbol}</strong></td>
                <td>${sideBadge}</td>
                <td class="font-mono">$${formatCleanPrice(t.entry_price)}</td>
                <td class="font-mono">${t.quantity}</td>
                <td class="font-mono">-</td>
                <td class="font-mono text-muted">-</td>
                <td class="font-mono text-muted">-</td>
                <td class="font-mono" style="font-size: 0.8rem; color: #818cf8;">#${t.order_id || '-'}</td>
            `;
            tbody.appendChild(tr);
        });
    }
}

function renderBotPositionsTable(positions) {
    const tbody = document.getElementById('bot-positions-tbody');
    if (!tbody) return;

    if (!positions || positions.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="9" class="empty-cell">
                    <i class="fa-regular fa-folder-open"></i> Tidak ada posisi aktif saat ini. Bot sedang memindai peluang market...
                </td>
            </tr>
        `;
        return;
    }

    function formatCleanPrice(val) {
        if (val === undefined || val === null || isNaN(val)) return '-';
        const num = Number(val);
        if (num === 0) return '0.00';
        if (num < 0.0001) return num.toFixed(8);
        if (num < 0.01) return num.toFixed(6);
        if (num < 1.0) return num.toFixed(4);
        return num.toFixed(2);
    }

    tbody.innerHTML = '';
    positions.forEach(pos => {
        const tr = document.createElement('tr');
        const isLong = pos.position_amt > 0;
        const sideBadge = isLong 
            ? '<span class="tag-badge long"><i class="fa-solid fa-arrow-trend-up"></i> LONG</span>' 
            : '<span class="tag-badge short"><i class="fa-solid fa-arrow-trend-down"></i> SHORT</span>';
        
        const pnl = pos.unrealized_pnl || 0.0;
        const pnlColor = pnl > 0 ? 'text-profit' : (pnl < 0 ? 'text-loss' : 'text-muted');
        const pnlSign = pnl >= 0 ? '+' : '-';

        tr.innerHTML = `
            <td><strong>${pos.symbol}</strong></td>
            <td>${sideBadge}</td>
            <td class="font-mono">${Math.abs(pos.position_amt)}</td>
            <td class="font-mono">$${formatCleanPrice(pos.entry_price)}</td>
            <td class="font-mono" style="font-weight: 700;">$${formatCleanPrice(pos.mark_price)}</td>
            <td class="font-mono ${pnlColor}" style="font-weight: 700;">${pnlSign}$${Math.abs(pnl).toFixed(2)}</td>
            <td class="font-mono text-loss">$${formatCleanPrice(pos.liquidation_price)}</td>
            <td><span class="tag-badge" style="background: rgba(99, 102, 241, 0.2); color: #818cf8;">${pos.leverage}x</span></td>
            <td>
                <button class="btn-log-action" style="background: rgba(244, 63, 94, 0.2); border-color: #f43f5e; color: #f43f5e;" onclick="window.closeBotPosition('${pos.symbol}')">
                    <i class="fa-solid fa-xmark"></i> Close Market
                </button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

function renderBotLogs(logs) {
    const logBox = document.getElementById('bot-terminal-logs');
    if (!logBox) return;

    if (!logs || logs.length === 0) return;

    logBox.innerHTML = '';
    logs.forEach(log => {
        const div = document.createElement('div');
        const tag = (log.tag || log.level || 'INFO').toUpperCase();
        div.className = `log-row ${tag.toLowerCase()}`;
        
        let tagColor = '#818cf8';
        if (tag === 'SUCCESS' || tag === 'START') tagColor = '#10b981';
        if (tag === 'WARNING' || tag === 'SIGNAL' || tag === 'ORDER') tagColor = '#f59e0b';
        if (tag === 'ERROR' || tag === 'REJECT') tagColor = '#f43f5e';
        if (tag === 'SCAN') tagColor = '#38bdf8';

        const timeStr = log.time || log.timestamp || '00:00:00';

        div.innerHTML = `
            <span class="log-time" style="color: #64748b; margin-right: 8px;">${timeStr}</span>
            <span class="log-tag" style="color: ${tagColor}; font-weight: 700; margin-right: 8px;">[${tag}]</span>
            <span class="log-msg">${log.message}</span>
        `;
        logBox.appendChild(div);
    });

    // Auto scroll to bottom
    logBox.scrollTop = logBox.scrollHeight;
}

async function startBotAutomation() {
    const stratSelect = document.getElementById('bot-strategy-select');
    const tfSelect = document.getElementById('bot-timeframe-select');
    const levSelect = document.getElementById('bot-leverage-select');
    const riskSelect = document.getElementById('bot-risk-select');
    const entryInput = document.getElementById('bot-entry-size-input');

    const strategy_id = stratSelect ? stratSelect.value : 'price_ema_7';
    const timeframe = tfSelect ? tfSelect.value : '1m';
    const leverage = levSelect ? parseInt(levSelect.value) : 3;

    let risk_pct = '0.20';
    const rawVal = entryInput ? parseFloat(entryInput.value) : null;
    if (riskSelect && riskSelect.value === 'custom' && rawVal) {
        risk_pct = `fixed_${rawVal}`;
    } else if (riskSelect && riskSelect.value.startsWith('fixed_')) {
        risk_pct = riskSelect.value;
    } else if (riskSelect && (riskSelect.value === '0.20' || riskSelect.value === '0.10' || riskSelect.value === '0.05')) {
        risk_pct = parseFloat(riskSelect.value);
    } else if (rawVal) {
        risk_pct = `fixed_${rawVal}`;
    }

    const watchlist = (state.botWatchlist && state.botWatchlist.length > 0) ? state.botWatchlist : ["ETHUSDT"];

    // 0-ms instant optimistic UI & localStorage update
    const statusBadge = document.getElementById('bot-status-badge');
    const statusText = document.getElementById('bot-status-text');
    const btnStart = document.getElementById('btn-start-bot');
    const btnStop = document.getElementById('btn-stop-bot');
    if (statusBadge) statusBadge.className = 'bot-status-badge running';
    const wlText = watchlist.length > 8 ? `${watchlist.length} PAIRS AUTO-HUNT (${watchlist.slice(0, 5).join(', ')} +${watchlist.length - 5} lainnya)` : `${watchlist.length} PAIR: ${watchlist.join(', ')}`;
    if (statusText) statusText.innerHTML = `<span class="pulse-dot green"></span> BOT ACTIVE (SCANNING ${wlText})`;
    if (btnStart) btnStart.style.display = 'none';
    if (btnStop) btnStop.style.display = 'inline-flex';

    localStorage.setItem('bot_active_state', JSON.stringify({
        is_running: true,
        watchlist: watchlist,
        active_strategy_id: strategy_id,
        timeframe: timeframe,
        leverage: leverage,
        risk_pct: risk_pct,
        timestamp: Date.now()
    }));

    try {
        const res = await fetch('/api/bot/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ strategy_id, timeframe, leverage, risk_pct, watchlist })
        });
        const data = await res.json();
        console.log('Bot Start Response:', data);
        loadBotStatus();
    } catch (e) {
        console.error('Failed to start bot:', e);
    }
}

async function stopBotAutomation() {
    // 0-ms instant optimistic UI & localStorage update
    const statusBadge = document.getElementById('bot-status-badge');
    const statusText = document.getElementById('bot-status-text');
    const btnStart = document.getElementById('btn-start-bot');
    const btnStop = document.getElementById('btn-stop-bot');
    if (statusBadge) statusBadge.className = 'bot-status-badge';
    if (statusText) statusText.innerHTML = `<span class="pulse-dot"></span> BOT STANDBY / READY`;
    if (btnStart) btnStart.style.display = 'inline-flex';
    if (btnStop) btnStop.style.display = 'none';

    localStorage.setItem('bot_active_state', JSON.stringify({
        is_running: false,
        watchlist: state.botWatchlist,
        timestamp: Date.now()
    }));

    try {
        const res = await fetch('/api/bot/stop', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({})
        });
        const data = await res.json();
        console.log('Bot Stop Response:', data);
        loadBotStatus();
    } catch (e) {
        console.error('Failed to stop bot:', e);
    }
}

async function resetBotSession() {
    const targetPairs = (state.botWatchlist && state.botWatchlist.length > 0) ? state.botWatchlist.join(', ') : 'ETHUSDT';
    if (!confirm(`Apakah Anda yakin ingin me-reset total sesi trading & menutup semua posisi untuk mulai dari modal bersih $5,000.00 (${targetPairs})?`)) return;
    try {
        const res = await fetch('/api/bot/reset', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({})
        });
        const data = await res.json();
        console.log('Bot Reset Response:', data);
        loadBotStatus();
    } catch (e) {
        console.error('Failed to reset bot:', e);
    }
}

window.startBotAutomation = startBotAutomation;
window.stopBotAutomation = stopBotAutomation;
window.resetBotSession = resetBotSession;

window.closeBotPosition = async function(symbol) {
    if (!confirm(`Tutup posisi ${symbol} secara instan dengan Market Order di Binance Demo?`)) return;
    try {
        const res = await fetch('/api/bot/close_position', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ symbol })
        });
        const data = await res.json();
        console.log('Close Position Response:', data);
        loadBotStatus();
    } catch (e) {
        console.error('Failed to close position:', e);
    }
};

// --- 10. REAL-TIME BINANCE FUTURES TICKER STREAM (COINMARKETCAP / BINANCE LIVE TICKER) ---
function updatePriceCell(symbol, currentPrice) {
    const priceCell = document.getElementById(`real-price-${symbol}`);
    if (priceCell && !isNaN(currentPrice) && currentPrice > 0) {
        const oldPrice = parseFloat(priceCell.getAttribute('data-price') || currentPrice);
        if (Math.abs(currentPrice - oldPrice) > 1e-8) {
            priceCell.setAttribute('data-price', currentPrice);
            priceCell.innerHTML = `<strong>$${formatExactPrice(currentPrice)}</strong>`;

            priceCell.classList.remove('flash-green', 'flash-red');
            void priceCell.offsetWidth; // trigger reflow
            if (currentPrice > oldPrice) {
                priceCell.classList.add('flash-green');
            } else {
                priceCell.classList.add('flash-red');
            }
        }
    }

    // Direct tick sync to active live forming candle on chart
    if (symbol === currentStreamingSymbol && currentLiveCandle && candleSeriesInstance && !isNaN(currentPrice) && currentPrice > 0) {
        currentLiveCandle.close = currentPrice;
        if (currentPrice > currentLiveCandle.high) currentLiveCandle.high = currentPrice;
        if (currentPrice < currentLiveCandle.low) currentLiveCandle.low = currentPrice;
        candleSeriesInstance.update(currentLiveCandle);

        const priceEl = document.getElementById('chart-live-price');
        if (priceEl) priceEl.textContent = `$${formatCleanPrice(currentPrice)}`;
    }
}

// 1. HTTP Fast Polling Stream (100% Anti-block, updates every second)
let tickerPollInterval = null;
function startTickerPolling() {
    if (tickerPollInterval) clearInterval(tickerPollInterval);
    
    async function poll() {
        try {
            const res = await fetch('/api/tickers');
            const data = await res.json();
            if (data.success && data.prices) {
                for (const [sym, price] of Object.entries(data.prices)) {
                    updatePriceCell(sym, price);
                }
            }
        } catch (e) {}
    }
    
    poll();
    tickerPollInterval = setInterval(poll, 1000);
}

// 2. Direct WebSocket Stream
let wsTicker = null;
function initBinanceLiveTickerStream() {
    startTickerPolling();

    if (wsTicker) {
        try { wsTicker.close(); } catch(e) {}
    }

    try {
        wsTicker = new WebSocket('wss://fstream.binance.com/ws/!miniTicker@arr');
        
        wsTicker.onmessage = (event) => {
            try {
                const tickers = JSON.parse(event.data);
                if (!Array.isArray(tickers)) return;

                tickers.forEach(t => {
                    const symbol = t.s;
                    const currentPrice = parseFloat(t.c);
                    updatePriceCell(symbol, currentPrice);
                });
            } catch (err) {}
        };

        wsTicker.onerror = () => {};
        wsTicker.onclose = () => {
            setTimeout(initBinanceLiveTickerStream, 5000);
        };
    } catch (e) {}
}

// --- 11. LIVE TRADINGVIEW CANDLESTICK CHART & MQL5/STRATEGY PLOTTING CONTROLLER ---
let liveChartInstance = null;
let liveRsiChartInstance = null;
let candleSeriesInstance = null;
let emaLineSeriesInstance = null;
let upperBandSeriesInstance = null;
let lowerBandSeriesInstance = null;
let rsiSeriesInstance = null;
let rsiObLine = null;
let rsiOsLine = null;
let currentChartTimeframe = '1m';
let chartUpdateInterval = null;
let chartWsConnection = null;
let lastChartSymbol = '';
let lastChartTf = '';
let lastFetchedCandles = [];
let lastFetchedEma = [];
let lastFetchedUpper = [];
let lastFetchedLower = [];
let lastFetchedRsi = [];
let currentLiveCandle = null;
let currentLiveEma = null;
let currentLiveRsi = null;
let currentLiveUpper = null;
let currentLiveLower = null;
let currentStrategyTitle = 'EMA 7';

function formatLegendDate(timeSec) {
    if (!timeSec) return '--/--/-- --:-- WIB';
    const d = new Date(timeSec * 1000);
    const yyyy = d.getFullYear();
    const mm = String(d.getMonth() + 1).padStart(2, '0');
    const dd = String(d.getDate()).padStart(2, '0');
    const hh = String(d.getHours()).padStart(2, '0');
    const min = String(d.getMinutes()).padStart(2, '0');
    return `${yyyy}/${mm}/${dd} ${hh}:${min} WIB`;
}

function updateChartLegend(candle, emaVal, rsiVal, upperVal, lowerVal) {
    if (!candle) return;
    const timeEl = document.getElementById('legend-time');
    const openEl = document.getElementById('legend-open');
    const highEl = document.getElementById('legend-high');
    const lowEl = document.getElementById('legend-low');
    const closeEl = document.getElementById('legend-close');
    const changeEl = document.getElementById('legend-change');
    const rangeEl = document.getElementById('legend-range');
    const emaEl = document.getElementById('legend-ema');
    const emaLabelEl = document.getElementById('legend-ema-label');
    const rsiEl = document.getElementById('legend-rsi');
    const rsiBadgeEl = document.getElementById('legend-rsi-badge');
    const rsiHeaderBadge = document.getElementById('chart-rsi-header-badge');

    const upperEl = document.getElementById('legend-upper');
    const upperWrap = document.getElementById('legend-upper-wrap');
    const lowerEl = document.getElementById('legend-lower');
    const lowerWrap = document.getElementById('legend-lower-wrap');
    const rsiTitleEl = document.getElementById('legend-rsi-title');

    const isBull = (candle.close >= candle.open);
    const barColor = isBull ? '#0ecb81' : '#f6465d';

    if (timeEl && candle.time) {
        timeEl.textContent = typeof candle.time === 'number' ? formatLegendDate(candle.time) : (candle.time.year ? `${candle.time.year}/${String(candle.time.month).padStart(2,'0')}/${String(candle.time.day).padStart(2,'0')}` : candle.time);
    }

    if (openEl && candle.open !== undefined) {
        openEl.textContent = formatCleanPrice(candle.open);
        openEl.style.color = barColor;
    }
    if (highEl && candle.high !== undefined) {
        highEl.textContent = formatCleanPrice(candle.high);
        highEl.style.color = barColor;
    }
    if (lowEl && candle.low !== undefined) {
        lowEl.textContent = formatCleanPrice(candle.low);
        lowEl.style.color = barColor;
    }
    if (closeEl && candle.close !== undefined) {
        closeEl.textContent = formatCleanPrice(candle.close);
        closeEl.style.color = barColor;
    }

    // CHANGE %: ((Close - Open) / Open) * 100
    if (changeEl && candle.open > 0) {
        const changePct = ((candle.close - candle.open) / candle.open) * 100;
        const sign = changePct >= 0 ? '+' : '';
        changeEl.textContent = `${sign}${changePct.toFixed(2)}%`;
        changeEl.style.color = changePct >= 0 ? '#0ecb81' : '#f6465d';
    }

    // Range %: ((High - Low) / Low) * 100
    if (rangeEl && candle.low > 0) {
        const rangePct = ((candle.high - candle.low) / candle.low) * 100;
        rangeEl.textContent = `${rangePct.toFixed(2)}%`;
        rangeEl.style.color = '#64748b';
    }

    if (emaLabelEl) {
        emaLabelEl.textContent = currentStrategyTitle ? (currentStrategyTitle.length > 20 ? currentStrategyTitle.substring(0, 20) + '...' : currentStrategyTitle) : 'Main Ind';
    }

    if (emaEl && emaVal !== undefined && emaVal !== null) {
        const v = typeof emaVal === 'object' ? emaVal.value : emaVal;
        emaEl.textContent = formatCleanPrice(v);
    }

    // Upper & Lower Band Legend Display
    const effectiveUpper = (upperVal !== undefined && upperVal !== null) ? (typeof upperVal === 'object' ? upperVal.value : upperVal) : currentLiveUpper;
    if (effectiveUpper !== undefined && effectiveUpper !== null && !isNaN(effectiveUpper)) {
        if (upperEl) upperEl.textContent = formatCleanPrice(effectiveUpper);
        if (upperWrap) upperWrap.style.display = 'inline';
    } else if (upperWrap) {
        upperWrap.style.display = 'none';
    }

    const effectiveLower = (lowerVal !== undefined && lowerVal !== null) ? (typeof lowerVal === 'object' ? lowerVal.value : lowerVal) : currentLiveLower;
    if (effectiveLower !== undefined && effectiveLower !== null && !isNaN(effectiveLower)) {
        if (lowerEl) lowerEl.textContent = formatCleanPrice(effectiveLower);
        if (lowerWrap) lowerWrap.style.display = 'inline';
    } else if (lowerWrap) {
        lowerWrap.style.display = 'none';
    }

    // Dynamic RSI Label (Wilder vs Freqtrade SMA)
    const isWilder = (state.selectedStrategy && state.selectedStrategy.includes('wilder')) || (currentStrategyTitle && currentStrategyTitle.toLowerCase().includes('wilder'));
    const rsiLabelText = isWilder ? 'RSI (Wilder 14)' : 'RSI (Freqtrade 14)';
    if (rsiTitleEl) rsiTitleEl.textContent = rsiLabelText;

    // RSI (14) Legend & Status Badge
    const effectiveRsi = (rsiVal !== undefined && rsiVal !== null) ? (typeof rsiVal === 'object' ? rsiVal.value : rsiVal) : currentLiveRsi;
    if (effectiveRsi !== undefined && effectiveRsi !== null && !isNaN(effectiveRsi)) {
        const rVal = Number(effectiveRsi);
        if (rsiEl) rsiEl.textContent = rVal.toFixed(2);
        
        let rsiText = `${rVal.toFixed(1)}`;
        let badgeBg = 'rgba(139, 92, 246, 0.1)';
        let badgeColor = '#8b5cf6';
        let statusTag = '';

        if (rVal >= 70) {
            statusTag = 'OVERBOUGHT (Exit Zone)';
            badgeBg = 'rgba(239, 68, 68, 0.15)';
            badgeColor = '#ef4444';
        } else if (rVal <= 30) {
            statusTag = 'OVERSOLD (Dip Buy Zone)';
            badgeBg = 'rgba(16, 185, 129, 0.15)';
            badgeColor = '#10b981';
        }

        if (rsiBadgeEl) {
            if (statusTag) {
                rsiBadgeEl.textContent = statusTag;
                rsiBadgeEl.style.background = badgeBg;
                rsiBadgeEl.style.color = badgeColor;
                rsiBadgeEl.style.display = 'inline-block';
            } else {
                rsiBadgeEl.style.display = 'none';
            }
        }

        if (rsiHeaderBadge) {
            rsiHeaderBadge.textContent = `${rsiLabelText}: ${rsiText} ${statusTag ? `[${statusTag.split(' ')[0]}]` : ''}`;
            rsiHeaderBadge.style.background = badgeBg;
            rsiHeaderBadge.style.color = badgeColor;
        }
    }
}

function initLiveBotChart() {
    const container = document.getElementById('live-bot-chart-container');
    const rsiContainer = document.getElementById('live-bot-rsi-container');
    if (!container || typeof LightweightCharts === 'undefined') return;

    if (liveChartInstance) {
        liveChartInstance.applyOptions({ width: container.clientWidth || 800 });
        if (liveRsiChartInstance && rsiContainer) {
            liveRsiChartInstance.applyOptions({ width: rsiContainer.clientWidth || 800 });
        }
        updateLiveBotChart();
        return;
    }

    try {
        const commonTimeFormatter = (time) => {
            const d = new Date(time * 1000);
            const dd = String(d.getDate()).padStart(2, '0');
            const mm = String(d.getMonth() + 1).padStart(2, '0');
            const yyyy = d.getFullYear();
            const hh = String(d.getHours()).padStart(2, '0');
            const min = String(d.getMinutes()).padStart(2, '0');
            return `${dd}/${mm}/${yyyy} ${hh}:${min} WIB`;
        };

        // 1. MAIN CANDLESTICK CHART
        liveChartInstance = LightweightCharts.createChart(container, {
            width: container.clientWidth || 800,
            height: 350,
            localization: {
                locale: 'id-ID',
                dateFormat: 'yyyy/MM/dd',
                timeFormatter: commonTimeFormatter
            },
            layout: {
                background: { color: '#ffffff' },
                textColor: '#334155',
                fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
                fontSize: 12
            },
            grid: {
                vertLines: { color: '#f8fafc' },
                horzLines: { color: '#f1f5f9' }
            },
            crosshair: {
                mode: LightweightCharts.CrosshairMode.Normal,
                vertLine: { color: '#94a3b8', width: 1, style: 3 },
                horzLine: { color: '#94a3b8', width: 1, style: 3 }
            },
            rightPriceScale: {
                borderColor: '#e2e8f0',
                autoScale: true,
                alignLabels: true,
                scaleMargins: {
                    top: 0.1,
                    bottom: 0.1
                }
            },
            timeScale: {
                borderColor: '#e2e8f0',
                timeVisible: true,
                secondsVisible: false,
                rightOffset: 8,
                barSpacing: 10,
                minBarSpacing: 4,
                tickMarkFormatter: (time) => {
                    const d = new Date(time * 1000);
                    const hh = String(d.getHours()).padStart(2, '0');
                    const mm = String(d.getMinutes()).padStart(2, '0');
                    return `${hh}:${mm}`;
                }
            }
        });

        // Candlestick Series (Binance Official Crisp Colors with Live Price Badge)
        candleSeriesInstance = liveChartInstance.addCandlestickSeries({
            upColor: '#0ecb81',
            downColor: '#f6465d',
            borderVisible: true,
            borderUpColor: '#0ecb81',
            borderDownColor: '#f6465d',
            wickUpColor: '#0ecb81',
            wickDownColor: '#f6465d',
            lastValueVisible: true,
            priceLineVisible: true,
            priceLineWidth: 1,
            priceLineColor: '#0ecb81',
            priceLineStyle: LightweightCharts.LineStyle.Dashed,
        });

        // Upper Band Series (Hide badges from Y-axis)
        upperBandSeriesInstance = liveChartInstance.addLineSeries({
            color: 'rgba(6, 182, 212, 0.75)',
            lineWidth: 1,
            lineStyle: LightweightCharts.LineStyle.Dashed,
            lastValueVisible: false,
            priceLineVisible: false,
            crosshairMarkerVisible: false
        });

        // Lower Band Series (Hide badges from Y-axis)
        lowerBandSeriesInstance = liveChartInstance.addLineSeries({
            color: 'rgba(236, 72, 153, 0.75)',
            lineWidth: 1,
            lineStyle: LightweightCharts.LineStyle.Dashed,
            lastValueVisible: false,
            priceLineVisible: false,
            crosshairMarkerVisible: false
        });

        // Main Indicator Line Overlay (Hide badges from Y-axis)
        emaLineSeriesInstance = liveChartInstance.addLineSeries({
            color: '#f59e0b',
            lineWidth: 2,
            lastValueVisible: false,
            priceLineVisible: false,
            crosshairMarkerVisible: false
        });

        // 2. RSI (14) OSCILLATOR SUB-PANE CHART
        if (rsiContainer) {
            liveRsiChartInstance = LightweightCharts.createChart(rsiContainer, {
                width: rsiContainer.clientWidth || 800,
                height: 110,
                localization: {
                    locale: 'id-ID',
                    dateFormat: 'yyyy/MM/dd',
                    timeFormatter: commonTimeFormatter
                },
                layout: {
                    background: { color: '#ffffff' },
                    textColor: '#64748b',
                    fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
                    fontSize: 11
                },
                grid: {
                    vertLines: { color: '#f8fafc' },
                    horzLines: { color: '#f1f5f9' }
                },
                crosshair: {
                    mode: LightweightCharts.CrosshairMode.Normal,
                    vertLine: { color: '#94a3b8', width: 1, style: 3 },
                    horzLine: { color: '#94a3b8', width: 1, style: 3 }
                },
                rightPriceScale: {
                    borderColor: '#e2e8f0',
                    autoScale: true,
                    scaleMargins: {
                        top: 0.1,
                        bottom: 0.1
                    }
                },
                timeScale: {
                    borderColor: '#e2e8f0',
                    timeVisible: true,
                    secondsVisible: false,
                    visible: false,
                    rightOffset: 8,
                    barSpacing: 10,
                    minBarSpacing: 4
                }
            });

            // RSI 14 Series (Violet) with explicit 0 - 100 range
            rsiSeriesInstance = liveRsiChartInstance.addLineSeries({
                color: '#8b5cf6',
                lineWidth: 2,
                title: 'RSI 14',
                priceFormat: {
                    type: 'price',
                    precision: 2,
                    minMove: 0.01
                },
                autoscaleInfoProvider: () => ({
                    priceRange: {
                        minValue: 0,
                        maxValue: 100,
                    },
                })
            });

            // Overbought Level 70 Horizontal Guide Line (Red)
            rsiSeriesInstance.createPriceLine({
                price: 70.0,
                color: '#ef4444',
                lineWidth: 1,
                lineStyle: LightweightCharts.LineStyle.Dashed,
                axisLabelVisible: true,
                title: '70'
            });

            // Oversold Level 30 Horizontal Guide Line (Green)
            rsiSeriesInstance.createPriceLine({
                price: 30.0,
                color: '#10b981',
                lineWidth: 1,
                lineStyle: LightweightCharts.LineStyle.Dashed,
                axisLabelVisible: true,
                title: '30'
            });

            // Neutral 50 Center Line (Gray Dotted)
            rsiSeriesInstance.createPriceLine({
                price: 50.0,
                color: '#cbd5e1',
                lineWidth: 1,
                lineStyle: LightweightCharts.LineStyle.Dotted,
                axisLabelVisible: false,
                title: '50'
            });

            // Synchronize Visible Range between Main Chart & RSI Sub-pane
            liveChartInstance.timeScale().subscribeVisibleLogicalRangeChange((range) => {
                if (liveRsiChartInstance && range) {
                    liveRsiChartInstance.timeScale().setVisibleLogicalRange(range);
                }
            });
            liveRsiChartInstance.timeScale().subscribeVisibleLogicalRangeChange((range) => {
                if (liveChartInstance && range) {
                    liveChartInstance.timeScale().setVisibleLogicalRange(range);
                }
            });
        }

        let isSyncingCrosshair = false;
        let isUserHoveringHistoricalBar = false;

        // Crosshair Hover Event - Realtime OHLC, EMA & RSI Inspector (Synced with RSI Subpane)
        liveChartInstance.subscribeCrosshairMove((param) => {
            if (isSyncingCrosshair) return;
            if (!param || !param.time || !param.seriesData) {
                isUserHoveringHistoricalBar = false;
                const activeC = currentLiveCandle || (lastFetchedCandles && lastFetchedCandles.length > 0 ? lastFetchedCandles[lastFetchedCandles.length - 1] : null);
                const activeE = currentLiveEma || (lastFetchedEma && lastFetchedEma.length > 0 ? lastFetchedEma[lastFetchedEma.length - 1].value : null);
                const activeR = currentLiveRsi || (lastFetchedRsi && lastFetchedRsi.length > 0 ? lastFetchedRsi[lastFetchedRsi.length - 1].value : null);
                updateChartLegend(activeC, activeE, activeR);
                if (liveRsiChartInstance) {
                    try { liveRsiChartInstance.clearCrosshairPosition(); } catch (e) {}
                }
                return;
            }

            const cData = param.seriesData.get(candleSeriesInstance);
            const eData = param.seriesData.get(emaLineSeriesInstance);
            const emaVal = eData ? eData.value : null;

            if (currentLiveCandle && param.time !== currentLiveCandle.time) {
                isUserHoveringHistoricalBar = true;
            } else {
                isUserHoveringHistoricalBar = false;
            }

            // Find matching RSI point at this exact timestamp
            let rsiVal = null;
            if (lastFetchedRsi && lastFetchedRsi.length > 0) {
                const rMatch = lastFetchedRsi.find(item => item.time === param.time);
                if (rMatch) rsiVal = rMatch.value;
            }

            let uMatch = null;
            if (lastFetchedUpper && lastFetchedUpper.length > 0) {
                const uObj = lastFetchedUpper.find(item => item.time === param.time);
                if (uObj) uMatch = uObj.value;
            }
            let lMatch = null;
            if (lastFetchedLower && lastFetchedLower.length > 0) {
                const lObj = lastFetchedLower.find(item => item.time === param.time);
                if (lObj) lMatch = lObj.value;
            }

            if (cData) {
                updateChartLegend(cData, emaVal, rsiVal, uMatch, lMatch);
            }

            // Project vertical crosshair to RSI subpane
            if (liveRsiChartInstance && rsiSeriesInstance && param.time) {
                try {
                    isSyncingCrosshair = true;
                    liveRsiChartInstance.setCrosshairPosition(rsiVal !== null ? rsiVal : 50, param.time, rsiSeriesInstance);
                    isSyncingCrosshair = false;
                } catch (e) {
                    isSyncingCrosshair = false;
                }
            }
        });

        if (liveRsiChartInstance) {
            liveRsiChartInstance.subscribeCrosshairMove((param) => {
                if (isSyncingCrosshair) return;
                if (!param || !param.time || !param.seriesData) {
                    if (liveChartInstance) {
                        try { liveChartInstance.clearCrosshairPosition(); } catch (e) {}
                    }
                    return;
                }

                const rData = param.seriesData.get(rsiSeriesInstance);
                const rsiVal = rData ? rData.value : null;

                let cMatch = null;
                let emaVal = null;
                if (lastFetchedCandles && lastFetchedCandles.length > 0) {
                    cMatch = lastFetchedCandles.find(item => item.time === param.time);
                }
                if (lastFetchedEma && lastFetchedEma.length > 0) {
                    const eMatch = lastFetchedEma.find(item => item.time === param.time);
                    if (eMatch) emaVal = eMatch.value;
                }

                if (cMatch) {
                    updateChartLegend(cMatch, emaVal, rsiVal);
                }

                // Project vertical crosshair to Main Candlestick Chart
                if (liveChartInstance && candleSeriesInstance && param.time) {
                    try {
                        isSyncingCrosshair = true;
                        liveChartInstance.setCrosshairPosition(cMatch ? cMatch.close : 0, param.time, candleSeriesInstance);
                        isSyncingCrosshair = false;
                    } catch (e) {
                        isSyncingCrosshair = false;
                    }
                }
            });
        }

        // Auto reset legend to live moving candle when mouse leaves chart area
        const resetToLiveCandle = () => {
            isUserHoveringHistoricalBar = false;
            if (liveChartInstance) {
                try { liveChartInstance.clearCrosshairPosition(); } catch (e) {}
            }
            if (liveRsiChartInstance) {
                try { liveRsiChartInstance.clearCrosshairPosition(); } catch (e) {}
            }
            const activeC = currentLiveCandle || (lastFetchedCandles && lastFetchedCandles.length > 0 ? lastFetchedCandles[lastFetchedCandles.length - 1] : null);
            const activeE = currentLiveEma || (lastFetchedEma && lastFetchedEma.length > 0 ? lastFetchedEma[lastFetchedEma.length - 1].value : null);
            const activeR = currentLiveRsi || (lastFetchedRsi && lastFetchedRsi.length > 0 ? lastFetchedRsi[lastFetchedRsi.length - 1].value : null);
            updateChartLegend(activeC, activeE, activeR);
        };

        if (container) container.addEventListener('mouseleave', resetToLiveCandle);
        if (rsiContainer) rsiContainer.addEventListener('mouseleave', resetToLiveCandle);

        // Responsive resize
        window.addEventListener('resize', () => {
            if (liveChartInstance && container) {
                liveChartInstance.applyOptions({ width: container.clientWidth });
            }
            if (liveRsiChartInstance && rsiContainer) {
                liveRsiChartInstance.applyOptions({ width: rsiContainer.clientWidth });
            }
        });

        // Initial fetch
        updateLiveBotChart();

        // Refresh indicators/markers gently every 30s without resetting active candle ticks
        if (chartUpdateInterval) clearInterval(chartUpdateInterval);
        chartUpdateInterval = setInterval(() => {
            // Only refresh if candle time has elapsed
            const nowSec = Math.floor(Date.now() / 1000);
            let tfSeconds = 60;
            if (currentChartTimeframe === '5m') tfSeconds = 300;
            else if (currentChartTimeframe === '15m') tfSeconds = 900;
            else if (currentChartTimeframe === '1h') tfSeconds = 3600;
            
            if (nowSec % tfSeconds < 5) {
                updateLiveBotChart(false);
            }
        }, 5000);

    } catch (e) {
        console.error('Failed to initialize TradingView Lightweight Chart:', e);
    }
}

let chartBookWsConnection = null;
let candleCountdownInterval = null;

// 100% DIRECT BINANCE USD-M FUTURES WEBSOCKET STREAMER (0-MS TICK SYNC)
let currentStreamingSymbol = '';
let currentStreamingTimeframe = '';

function connectChartWebSocket(symbol, timeframe) {
    const s = symbol.toLowerCase();
    const interval = timeframe || '1m';
    
    currentStreamingSymbol = symbol.toUpperCase();
    currentStreamingTimeframe = interval;

    if (chartWsConnection) {
        try { 
            chartWsConnection.onmessage = null;
            chartWsConnection.onclose = null;
            chartWsConnection.onerror = null;
            chartWsConnection.close(); 
        } catch (e) {}
        chartWsConnection = null;
    }

    const wsUrls = [
        'wss://fstream.binance.com/ws',
        'wss://stream.binancefuture.com/ws',
        `wss://fstream.binance.com/ws/${s}@kline_${interval}`
    ];
    let currentUrlIdx = 0;

    function createWs() {
        if (currentStreamingSymbol !== symbol.toUpperCase()) return;
        const url = wsUrls[currentUrlIdx % wsUrls.length];
        try {
            chartWsConnection = new WebSocket(url);

            chartWsConnection.onopen = () => {
                if (currentStreamingSymbol !== symbol.toUpperCase()) {
                    try { chartWsConnection.close(); } catch(e) {}
                    return;
                }
                try {
                    chartWsConnection.send(JSON.stringify({
                        method: "SUBSCRIBE",
                        params: [
                            `${s}@kline_${interval}`,
                            `${s}@bookTicker`,
                            `${s}@aggTrade`
                        ],
                        id: Date.now()
                    }));
                } catch (e) {}
            };

            chartWsConnection.onmessage = (event) => {
                try {
                    const ov = document.getElementById('chart-loading-overlay');
                    if (ov && ov.style.display !== 'none') ov.style.display = 'none';

                    const msg = JSON.parse(event.data);
                    
                    // Strict Symbol & TF Filter
                    if (msg.s && msg.s.toUpperCase() !== currentStreamingSymbol) return;
                    
                    // Handle Kline stream event
                    const k = msg.k || (msg.e === 'kline' ? msg.k : null);
                    if (k && candleSeriesInstance) {
                        if (k.s && k.s.toUpperCase() !== currentStreamingSymbol) return;
                        if (k.i && k.i !== currentStreamingTimeframe) return;

                        const candleTime = Math.floor(k.t / 1000);
                        const openPrice = parseFloat(k.o);
                        const highPrice = parseFloat(k.h);
                        const lowPrice = parseFloat(k.l);
                        const closePrice = parseFloat(k.c);

                        const liveBar = {
                            time: candleTime,
                            open: openPrice,
                            high: highPrice,
                            low: lowPrice,
                            close: closePrice
                        };

                        currentLiveCandle = liveBar;

                        // Update candlestick in real-time
                        candleSeriesInstance.update(liveBar);

                        // Compute dynamic real-time EMA 7: EMA_now = (Price_now - EMA_prev) * (2 / 8) + EMA_prev
                        if (emaLineSeriesInstance && lastFetchedEma && lastFetchedEma.length > 0) {
                            let prevEma = lastFetchedEma[lastFetchedEma.length - 1].value;
                            if (lastFetchedEma.length >= 2 && lastFetchedEma[lastFetchedEma.length - 1].time === candleTime) {
                                prevEma = lastFetchedEma[lastFetchedEma.length - 2].value;
                            }
                            const multiplier = 2.0 / (7.0 + 1.0);
                            const liveEmaVal = (closePrice - prevEma) * multiplier + prevEma;
                            currentLiveEma = liveEmaVal;

                            emaLineSeriesInstance.update({
                                time: candleTime,
                                value: liveEmaVal
                            });

                            // Update header EMA
                            const emaLegendEl = document.getElementById('chart-ema-legend');
                            if (emaLegendEl) emaLegendEl.textContent = `EMA 7: $${formatCleanPrice(liveEmaVal)}`;
                        }

                        // Update RSI live series
                        if (rsiSeriesInstance && currentLiveRsi !== null) {
                            rsiSeriesInstance.update({
                                time: candleTime,
                                value: currentLiveRsi
                            });
                        }

                        // Update header Live Price
                        const priceEl = document.getElementById('chart-live-price');
                        if (priceEl) priceEl.textContent = `$${formatCleanPrice(closePrice)}`;

                        // Update Top Legend if not hovering historical bar
                        if (!isUserHoveringHistoricalBar) {
                            updateChartLegend(liveBar, currentLiveEma, currentLiveRsi, currentLiveUpper, currentLiveLower);
                        }
                    }

                    // Handle Real-time Trade Execution (aggTrade)
                    if (msg.e === 'aggTrade' || (msg.p !== undefined && msg.q !== undefined)) {
                        if (msg.s && msg.s.toUpperCase() !== currentStreamingSymbol) return;
                        const tradePrice = parseFloat(msg.p);
                        
                        const priceEl = document.getElementById('chart-live-price');
                        if (priceEl) priceEl.textContent = `$${formatCleanPrice(tradePrice)}`;

                        let tfSec = 60;
                        if (currentStreamingTimeframe === '5m') tfSec = 300;
                        else if (currentStreamingTimeframe === '15m') tfSec = 900;
                        else if (currentStreamingTimeframe === '1h') tfSec = 3600;

                        const expectedCandleTime = Math.floor(Math.floor(Date.now() / 1000) / tfSec) * tfSec;

                        if (!currentLiveCandle || currentLiveCandle.time < expectedCandleTime) {
                            const prevClose = currentLiveCandle ? currentLiveCandle.close : tradePrice;
                            currentLiveCandle = {
                                time: expectedCandleTime,
                                open: prevClose,
                                high: Math.max(prevClose, tradePrice),
                                low: Math.min(prevClose, tradePrice),
                                close: tradePrice
                            };
                        } else {
                            currentLiveCandle.close = tradePrice;
                            if (tradePrice > currentLiveCandle.high) currentLiveCandle.high = tradePrice;
                            if (tradePrice < currentLiveCandle.low) currentLiveCandle.low = tradePrice;
                        }

                        if (candleSeriesInstance) {
                            candleSeriesInstance.update(currentLiveCandle);
                        }

                        if (emaLineSeriesInstance && lastFetchedEma && lastFetchedEma.length > 0) {
                            let prevEma = lastFetchedEma[lastFetchedEma.length - 1].value;
                            const multiplier = 2.0 / (7.0 + 1.0);
                            const liveEmaVal = (tradePrice - prevEma) * multiplier + prevEma;
                            currentLiveEma = liveEmaVal;
                            emaLineSeriesInstance.update({
                                time: currentLiveCandle.time,
                                value: liveEmaVal
                            });
                            const emaLegendEl = document.getElementById('chart-ema-legend');
                            if (emaLegendEl) emaLegendEl.textContent = `EMA 7: $${formatCleanPrice(liveEmaVal)}`;
                        }

                        if (!isUserHoveringHistoricalBar) {
                            updateChartLegend(currentLiveCandle, currentLiveEma, currentLiveRsi, currentLiveUpper, currentLiveLower);
                        }
                    }

                    // Handle BookTicker stream event (Ask / Bid)
                    if (msg.b !== undefined && msg.a !== undefined) {
                        if (msg.s && msg.s.toUpperCase() !== currentStreamingSymbol) return;
                        
                        const bestBid = parseFloat(msg.b);
                        const bestAsk = parseFloat(msg.a);

                        const askEl = document.getElementById('live-ask-val');
                        const bidEl = document.getElementById('live-bid-val');
                        if (askEl) askEl.textContent = formatCleanPrice(bestAsk);
                        if (bidEl) bidEl.textContent = formatCleanPrice(bestBid);

                        const midPrice = (bestBid + bestAsk) / 2.0;
                        const priceEl = document.getElementById('chart-live-price');
                        if (priceEl && !k && !msg.p) priceEl.textContent = `$${formatCleanPrice(midPrice)}`;
                    }

                } catch (err) {}
            };

            chartWsConnection.onerror = () => {};
            chartWsConnection.onclose = () => {
                if (currentStreamingSymbol !== symbol.toUpperCase()) return;
                currentUrlIdx++;
                setTimeout(createWs, 2000);
            };
        } catch (e) {}
    }

    createWs();

    // Candle Countdown Timer (e.g. 00:45)
    if (candleCountdownInterval) clearInterval(candleCountdownInterval);
    function updateCountdown() {
        const nowSec = Math.floor(Date.now() / 1000);
        let tfSeconds = 60;
        if (interval === '5m') tfSeconds = 300;
        else if (interval === '15m') tfSeconds = 900;
        else if (interval === '1h') tfSeconds = 3600;

        const remaining = tfSeconds - (nowSec % tfSeconds);
        const mm = String(Math.floor(remaining / 60)).padStart(2, '0');
        const ss = String(remaining % 60).padStart(2, '0');
        const countdownEl = document.getElementById('live-candle-countdown');
        if (countdownEl) countdownEl.textContent = `${mm}:${ss}`;
    }
    updateCountdown();
    candleCountdownInterval = setInterval(updateCountdown, 1000);
}

let activeChartRequestId = 0;

// 100% DIRECT BINANCE USD-M FUTURES KLINES & DYNAMIC STRATEGY INDICATOR ENGINE
async function updateLiveBotChart() {
    if (!liveChartInstance || !candleSeriesInstance) return;

    const sym = state.chartFocusSymbol || ((state.botWatchlist && state.botWatchlist.length > 0) ? state.botWatchlist[0] : 'BTCUSDT');
    const tf = currentChartTimeframe || '1m';
    const botStratSelect = document.getElementById('bot-strategy-select');
    const currentStratId = botStratSelect ? botStratSelect.value : (state.selectedStrategy || 'price_ema_crossover');

    // IMMEDIATELY lock streaming symbol and update UI title to prevent old ticker ticks from bleeding in
    currentStreamingSymbol = sym.toUpperCase();
    currentStreamingTimeframe = tf;

    const titleEl = document.getElementById('live-chart-symbol-title');
    if (titleEl) titleEl.textContent = `${sym} (${tf})`;

    const reqId = ++activeChartRequestId;
    const isSymbolSwitch = (lastChartSymbol !== sym || lastChartTf !== tf);

    if (isSymbolSwitch) {
        lastChartSymbol = sym;
        lastChartTf = tf;
        currentLiveCandle = null;
        currentLiveEma = null;
        currentLiveRsi = null;
        lastFetchedCandles = [];
        lastFetchedEma = [];
        lastFetchedUpper = [];
        lastFetchedLower = [];
        lastFetchedRsi = [];

        // 1. Immediately disconnect old websocket so ticks from old pair don't clash
        if (chartWsConnection) {
            try {
                chartWsConnection.onmessage = null;
                chartWsConnection.onclose = null;
                chartWsConnection.onerror = null;
                chartWsConnection.close();
            } catch (e) {}
            chartWsConnection = null;
        }

        // 2. Clear old chart series immediately and reset autoScale to eliminate price scale glitch
        try {
            candleSeriesInstance.setData([]);
            if (emaLineSeriesInstance) emaLineSeriesInstance.setData([]);
            if (upperBandSeriesInstance) upperBandSeriesInstance.setData([]);
            if (lowerBandSeriesInstance) lowerBandSeriesInstance.setData([]);
            if (rsiSeriesInstance) rsiSeriesInstance.setData([]);
            candleSeriesInstance.setMarkers([]);
            liveChartInstance.priceScale('right').applyOptions({ autoScale: true });
            if (liveRsiChartInstance) liveRsiChartInstance.priceScale('right').applyOptions({ autoScale: true });
        } catch (e) {}

        const overlay = document.getElementById('chart-loading-overlay');
        if (overlay) overlay.style.display = 'flex';
        setTimeout(() => {
            const ov = document.getElementById('chart-loading-overlay');
            if (ov) ov.style.display = 'none';
        }, 1000);
    }

    let candles = [];
    let emaSeries = [];
    let upperSeries = [];
    let lowerSeries = [];
    let rsiSeries = [];
    let markers = [];
    let stratName = 'EMA 7';
    let precision = 2;
    let minMove = 0.01;

    try {
        // Fetch accurate strategy indicators and markers calculated directly from server API (1000 candles to match backtest range)
        const resLocal = await fetch(`/api/chart/klines?symbol=${encodeURIComponent(sym)}&timeframe=${tf}&strategy=${encodeURIComponent(currentStratId)}&limit=1000`);
        const dataLocal = await resLocal.json();
        if (reqId !== activeChartRequestId) {
            const overlay = document.getElementById('chart-loading-overlay');
            if (overlay) overlay.style.display = 'none';
            return; // Discard outdated async responses
        }

        if (dataLocal.success && dataLocal.candles && dataLocal.candles.length > 0) {
            candles = dataLocal.candles;
            if (dataLocal.ema) emaSeries = dataLocal.ema;
            if (dataLocal.upper_band) upperSeries = dataLocal.upper_band;
            if (dataLocal.lower_band) lowerSeries = dataLocal.lower_band;
            if (dataLocal.rsi) rsiSeries = dataLocal.rsi;
            if (dataLocal.markers) markers = dataLocal.markers;
            if (dataLocal.strategy_name) stratName = dataLocal.strategy_name;
            if (dataLocal.precision !== undefined) precision = dataLocal.precision;
            if (dataLocal.min_move !== undefined) minMove = dataLocal.min_move;
        }
    } catch (e) {
        console.warn('Local chart API fetch failed, falling back to direct fapi:', e);
    }

    // Direct Binance Futures Fallback if local API is unreachable (500 candles)
    if (!candles || candles.length === 0) {
        try {
            const directUrl = `https://fapi.binance.com/fapi/v1/klines?symbol=${encodeURIComponent(sym)}&interval=${tf}&limit=500`;
            const res = await fetch(directUrl);
            if (reqId !== activeChartRequestId) {
                const overlay = document.getElementById('chart-loading-overlay');
                if (overlay) overlay.style.display = 'none';
                return;
            }
            if (res.ok) {
                const raw = await res.json();
                if (Array.isArray(raw) && raw.length > 0) {
                    candles = raw.map(item => ({
                        time: Math.floor(item[0] / 1000),
                        open: parseFloat(item[1]),
                        high: parseFloat(item[2]),
                        low: parseFloat(item[3]),
                        close: parseFloat(item[4]),
                        volume: parseFloat(item[5])
                    }));
                }
            }
        } catch (e) {}
    }

    const overlayEl = document.getElementById('chart-loading-overlay');
    if (overlayEl) overlayEl.style.display = 'none';

    if (reqId !== activeChartRequestId) return;

    if (!candles || candles.length === 0) {
        return;
    }

    lastFetchedCandles = candles;
    currentStrategyTitle = stratName;

    // Determine precision dynamically from symbol and latest price matching Binance Futures
    const symUpper = sym.toUpperCase();
    if (symUpper.includes('BTC') || latestClose >= 20000) {
        precision = 1; // Binance Futures BTCUSDT tickSize is 0.1 (1 decimal)
        minMove = 0.1;
    } else if (symUpper.includes('ETH') || symUpper.includes('BNB') || symUpper.includes('SOL') || latestClose >= 50.0) {
        precision = 2;
        minMove = 0.01;
    } else if (symUpper.includes('NEAR') || symUpper.includes('SUI')) {
        precision = 3;
        minMove = 0.001;
    } else if (latestClose < 0.0001) {
        precision = 8;
        minMove = 0.00000001;
    } else if (latestClose < 0.01) {
        precision = 6;
        minMove = 0.000001;
    } else if (latestClose < 0.1) {
        precision = 5;
        minMove = 0.00001;
    } else if (latestClose < 50.0) {
        precision = 4;
        minMove = 0.0001;
    } else {
        precision = 2;
        minMove = 0.01;
    }

    const pOptions = {
        priceFormat: {
            type: 'price',
            precision: precision,
            minMove: minMove
        }
    };
    candleSeriesInstance.applyOptions(pOptions);
    if (emaLineSeriesInstance) emaLineSeriesInstance.applyOptions(pOptions);
    if (upperBandSeriesInstance) upperBandSeriesInstance.applyOptions(pOptions);
    if (lowerBandSeriesInstance) lowerBandSeriesInstance.applyOptions(pOptions);

    // Compute fallback EMA if not populated
    if (!emaSeries || emaSeries.length === 0) {
        const kEma = 2.0 / (7.0 + 1.0);
        let prevEma = null;
        for (let i = 0; i < candles.length; i++) {
            const c = candles[i].close;
            if (prevEma === null) {
                prevEma = c;
            } else {
                prevEma = (c - prevEma) * kEma + prevEma;
            }
            emaSeries.push({ time: candles[i].time, value: prevEma });
        }
    }
    lastFetchedEma = emaSeries;
    lastFetchedUpper = upperSeries;
    lastFetchedLower = lowerSeries;

    // Compute fallback RSI if not returned
    if (!rsiSeries || rsiSeries.length === 0) {
        let gains = 0, losses = 0;
        const period = 14;
        for (let i = 1; i < candles.length; i++) {
            const diff = candles[i].close - candles[i-1].close;
            if (i <= period) {
                if (diff > 0) gains += diff;
                else losses += Math.abs(diff);
                if (i === period) {
                    const avgGain = gains / period;
                    const avgLoss = losses / period;
                    const rs = avgLoss === 0 ? 100 : avgGain / avgLoss;
                    rsiSeries.push({ time: candles[i].time, value: 100 - (100 / (1 + rs)) });
                }
            } else {
                const prevGain = gains / period;
                const prevLoss = losses / period;
                const curGain = diff > 0 ? diff : 0;
                const curLoss = diff < 0 ? Math.abs(diff) : 0;
                const avgGain = (prevGain * (period - 1) + curGain) / period;
                const avgLoss = (prevLoss * (period - 1) + curLoss) / period;
                gains = avgGain * period;
                losses = avgLoss * period;
                const rs = avgLoss === 0 ? 100 : avgGain / avgLoss;
                rsiSeries.push({ time: candles[i].time, value: 100 - (100 / (1 + rs)) });
            }
        }
    }
    lastFetchedRsi = rsiSeries;

    // Set Data on Main Chart Series
    candleSeriesInstance.setData(candles);
    if (emaLineSeriesInstance) emaLineSeriesInstance.setData(emaSeries);
    if (upperBandSeriesInstance) upperBandSeriesInstance.setData(upperSeries || []);
    if (lowerBandSeriesInstance) lowerBandSeriesInstance.setData(lowerSeries || []);
    candleSeriesInstance.setMarkers(markers);

    // Set Data on RSI Sub-pane Series
    if (rsiSeriesInstance && rsiSeries.length > 0) {
        rsiSeriesInstance.setData(rsiSeries);
    }

    // Initialize currentLiveCandle immediately from latest candle
    if (candles && candles.length > 0) {
        const lastBar = candles[candles.length - 1];
        currentLiveCandle = {
            time: lastBar.time,
            open: lastBar.open,
            high: lastBar.high,
            low: lastBar.low,
            close: lastBar.close
        };
    }

    if (isSymbolSwitch || !chartWsConnection) {
        if (candles.length > 0) {
            const totalBars = candles.length;
            const visibleBars = 75; // Binance official standard zoom (~75 candles)
            const fromLogical = Math.max(0, totalBars - visibleBars);
            const toLogical = totalBars + 5;
            liveChartInstance.timeScale().setVisibleLogicalRange({ from: fromLogical, to: toLogical });
            if (liveRsiChartInstance) {
                liveRsiChartInstance.timeScale().setVisibleLogicalRange({ from: fromLogical, to: toLogical });
            }
        }
        liveChartInstance.priceScale('right').applyOptions({ autoScale: true });
        if (liveRsiChartInstance) {
            liveRsiChartInstance.priceScale('right').applyOptions({ autoScale: true });
        }
        // Connect websocket only after new candle data has loaded to prevent scale glitch
        connectChartWebSocket(sym, tf);
    }

    // Update Header Display
    if (titleEl) titleEl.textContent = `${sym} (${tf})`;

    const priceEl = document.getElementById('chart-live-price');
    if (priceEl) priceEl.textContent = `$${formatCleanPrice(latestClose)}`;

    const emaLegendEl = document.getElementById('chart-ema-legend');
    if (emaLegendEl && emaSeries.length > 0) {
        const latestEma = emaSeries[emaSeries.length - 1].value;
        const shortStratLabel = stratName.length > 25 ? stratName.substring(0, 25) + '...' : stratName;
        emaLegendEl.textContent = `${shortStratLabel}: $${formatCleanPrice(latestEma)}`;
    }

    // Update Top Legend with latest live candle
    const latestC = candles[candles.length - 1];
    const latestE = emaSeries.length > 0 ? emaSeries[emaSeries.length - 1].value : latestClose;
    const latestR = rsiSeries.length > 0 ? rsiSeries[rsiSeries.length - 1].value : null;
    const latestU = upperSeries.length > 0 ? upperSeries[upperSeries.length - 1].value : null;
    const latestL = lowerSeries.length > 0 ? lowerSeries[lowerSeries.length - 1].value : null;
    currentLiveRsi = latestR;
    currentLiveUpper = latestU;
    currentLiveLower = latestL;
    updateChartLegend(latestC, latestE, latestR, latestU, latestL);

    // Hide Loading Overlay
    const overlay = document.getElementById('chart-loading-overlay');
    if (overlay) overlay.style.display = 'none';
}

function changeChartTimeframe(tf) {
    currentChartTimeframe = tf;
    const btns = document.querySelectorAll('#chart-tf-buttons .tf-btn');
    btns.forEach(b => {
        if (b.getAttribute('data-chart-tf') === tf) b.classList.add('active');
        else b.classList.remove('active');
    });

    const overlay = document.getElementById('chart-loading-overlay');
    if (overlay) overlay.style.display = 'flex';
    
    updateLiveBotChart();
}

window.changeChartTimeframe = changeChartTimeframe;
window.initLiveBotChart = initLiveBotChart;
window.updateLiveBotChart = updateLiveBotChart;

// Auto initialize chart when switching to bot tab or on DOM load
document.addEventListener('DOMContentLoaded', () => {
    setTimeout(initLiveBotChart, 300);
});





