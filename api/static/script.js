/* ================================
   AtomForge - Focused Two-Function UI
   Simple, robust JavaScript module
   ================================ */

const App = (() => {
  const qs = (s, r=document) => r.querySelector(s);
  const qsa = (s, r=document) => [...r.querySelectorAll(s)];
  const st = {
    mode: (location.hash.replace('#','') || localStorage.getItem('atomforge:mode') || 'compile')
  };

  // Elements
  const el = {
    tabCompile: qs('#tab-compile'),
    tabDecompile: qs('#tab-decompile'),
    panelCompile: qs('#panel-compile'),
    panelDecompile: qs('#panel-decompile'),
    runBtn: qs('#runBtn'),
    runLabel: qs('#runBtn .label'),
    fdoInput: qs('#fdoInput'),
    // Decompile
    toggleBtns: qsa('.toggle-btn'),
    fileView: qs('#fileInputView'),
    hexInputView: qs('#hexInputView'),
    binaryDrop: qs('#binaryDrop'),
    binaryFile: qs('#binaryFile'),
    fileDecoded: qs('#fileDecoded'),
    openAsHexBtn: qs('#openAsHexBtn'),
    hexInput: qs('#hexInput'),
    // Hex detection elements
    hexStatusLine: qs('#hexStatusLine'),
    hexStatusText: qs('#hexStatusText'),
    hexStatusIcon: qs('#hexStatusIcon'),
    // Output
    outTabs: qsa('.output .tab'),
    outPanels: {
      status: qs('#out-status'),
      hex: qs('#out-hex'),
      source: qs('#out-source'),
    },
    statusLog: qs('#statusLog'),
    hexOutPanel: qs('#out-hex'),
    hexOutViewer: qs('#hexView'),
    sourceView: qs('#sourceView'),
    compileSize: qs('#compileSize'),
    decompileSize: qs('#decompileSize'),
    downloadBin: qs('#downloadBin'),
    copyHex: qs('#copyHex'),
    downloadTxt: qs('#downloadTxt'),
    copySource: qs('#copySource'),
    // Examples menu
    examplesBtn: qs('#examplesBtn'),
    examplesMenu: qs('#examplesMenu'),
    // API modal
    apiBtn: qs('#apiBtn'),
    apiModal: qs('#apiModal'),
    apiModalClose: qs('#apiModalClose'),
    apiBackdrop: qs('#apiModal .modal-backdrop'),
    // File management
    fileBtn: qs('#fileBtn'),
    fileMenu: qs('#fileMenu'),
    saveBtn: qs('#saveBtn'),
    saveAsBtn: qs('#saveAsBtn'),
    openBtn: qs('#openBtn'),
    recentBtn: qs('#recentBtn'),
    newBtn: qs('#newBtn'),
    // Save modal
    saveModal: qs('#saveModal'),
    saveModalClose: qs('#saveModalClose'),
    saveForm: qs('#saveForm'),
    scriptName: qs('#scriptName'),
    saveConfirmBtn: qs('#saveConfirmBtn'),
    saveCancelBtn: qs('#saveCancelBtn'),
    saveStatus: qs('#saveStatus'),
    btnText: qs('#saveConfirmBtn .btn-text'),
    btnSpinner: qs('#saveConfirmBtn .btn-spinner'),
    // File browser modal
    fileBrowserModal: qs('#fileBrowserModal'),
    fileBrowserModalClose: qs('#fileBrowserModalClose'),
    fileSearchInput: qs('#fileSearchInput'),
    fileSearchClear: qs('#fileSearchClear'),
    showAllFiles: qs('#showAllFiles'),
    showFavorites: qs('#showFavorites'),
    showRecent: qs('#showRecent'),
    fileLoadingIndicator: qs('#fileLoadingIndicator'),
    fileNoResults: qs('#fileNoResults'),
    fileList: qs('#fileList'),
    // Confirmation modal
    confirmModal: qs('#confirmModal'),
    confirmModalClose: qs('#confirmModalClose'),
    confirmMessage: qs('#confirmMessage'),
    confirmCancelBtn: qs('#confirmCancelBtn'),
    confirmOkBtn: qs('#confirmOkBtn'),
    // Toast system
    toastContainer: qs('#toastContainer'),
    // Status bar
    statusBar: qs('#statusBar'),
    statusOperation: qs('#statusOperation'),
    statusStats: qs('#statusStats'),
    statusMode: qs('#statusMode'),
    brand: qs('.brand'),
  };

  let currentBinary = null;   // Uint8Array from file OR hex
  let compiledBuffer = null;  // ArrayBuffer
  let decompiledText = '';
  let isJsonlFileLoaded = false; // removed P3 JSONL support; keep false

  // ASCII atom support
  // ASCII helper removed
  let asciiAtoms = [];
  let asciiSupportEnabled = false;

  // File management state
  let currentScript = null;         // Currently loaded script
  let hasUnsavedChanges = false;    // Track unsaved changes
  let originalContent = '';         // Content when file was loaded/saved
  let searchDebounceTimer = null;   // For file search
  let currentFilter = 'all';        // Current file filter
  let autoSaveTimer = null;         // Auto-save timer
  let compileCheckTimer = null;     // For compilation checking

  // Per-mode output state preservation
  let modeOutputs = {
    compile: {
      hexContent: '',           // Compiled binary hex dump
      hexSize: '0 bytes',
      buffer: null,
      activeTab: 'status'
    },
    decompile: {
      hexContent: '',           // Input binary hex dump (for decompilation)
      hexSize: '0 bytes',
      sourceContent: '',        // Decompiled source code
      sourceSize: '0 chars',
      buffer: null,
      text: '',
      activeTab: 'status'
    }
  };

  function init() {
    bindTabs();
    bindRun();
    bindDecompileInputs();
    bindOutputTabs();
    bindDownloads();
    setupExamples();
    setupAPIModal();
    setupFileManagement();
    setupDocumentBar();
    setupBottomResize();
    // ASCII support removed
    // P3 extraction removed
    // Ensure hex input is enabled by default since it's now the default view
    el.hexInput.removeAttribute('disabled');
    setMode(st.mode, {pushHash:false});
    updateStatusBar(); // Initialize status bar with current content
    log('Ready.');
  }

  function setMode(mode, {pushHash=true}={}) {
    if (!['compile','decompile'].includes(mode)) return;
    st.mode = mode;
    localStorage.setItem('atomforge:mode', mode);
    el.tabCompile.setAttribute('aria-selected', String(mode==='compile'));
    el.tabDecompile.setAttribute('aria-selected', String(mode==='decompile'));
    el.tabDecompile.tabIndex = mode==='decompile' ? 0 : -1;
    el.tabCompile.tabIndex = mode==='compile' ? 0 : -1;
    el.panelCompile.hidden = mode!=='compile';
    el.panelDecompile.hidden = mode!=='decompile';
    el.runLabel.textContent = 'Run';

    // Update output tab availability based on mode
    updateOutputTabsForMode(mode);

    // Status bar is always visible on both modes
    if (el.statusBar) {
      el.statusBar.style.display = 'flex';
    }

    // Show/hide file menu based on mode (only relevant for compile mode)
    if (el.fileBtn && el.fileMenu) {
      const showFileMenu = mode === 'compile';
      // Use visibility to preserve layout and prevent tab shifting
      el.fileBtn.style.visibility = showFileMenu ? 'visible' : 'hidden';
      el.fileBtn.style.pointerEvents = showFileMenu ? 'auto' : 'none';
      if (!showFileMenu) {
        el.fileMenu.hidden = true; // Ensure menu is closed when hidden
        el.fileBtn.setAttribute('aria-expanded', 'false');
      }
    }

    // Update status mode text and trigger validation check
    if (el.statusMode) {
      el.statusMode.textContent = mode === 'compile' ? 'Compile' : 'Decompile';
      el.statusMode.className = 'status-mode'; // Reset to neutral state when switching modes

      // Trigger validation check and status bar update for the new mode
      setTimeout(() => {
        updateStatusBar(); // Update metrics (lines/chars vs bytes)
        updateValidationStatus();
      }, 100); // Small delay to ensure mode switch is complete
    }

    if (pushHash) location.hash = mode;
    (mode==='compile' ? el.fdoInput : el.hexInput).focus();
  }

  function updateOutputTabsForMode(mode) {
    const sourceTab = qs('.output .tab[data-tab="source"]');
    const hexTab = qs('.output .tab[data-tab="hex"]');

    // Don't save current outputs when switching - only save when operations complete
    // Just restore the outputs for the new mode
    restoreModeOutputs(mode);

    if (mode === 'compile') {
      // In compile mode: Hex tab available, Source tab disabled
      sourceTab.disabled = true;
      sourceTab.setAttribute('aria-disabled', 'true');
      sourceTab.style.opacity = '0.5';
      sourceTab.style.cursor = 'not-allowed';
      hexTab.disabled = false;
      hexTab.removeAttribute('aria-disabled');
      hexTab.style.opacity = '';
      hexTab.style.cursor = '';
    } else {
      // In decompile mode: Both tabs available
      sourceTab.disabled = false;
      sourceTab.removeAttribute('aria-disabled');
      sourceTab.style.opacity = '';
      sourceTab.style.cursor = '';
      hexTab.disabled = false;
      hexTab.removeAttribute('aria-disabled');
      hexTab.style.opacity = '';
      hexTab.style.cursor = '';
    }

    // Restore the remembered active tab for this mode
    const activeTab = mode === 'compile' ? modeOutputs.compile.activeTab : modeOutputs.decompile.activeTab;
    restoreActiveTab(mode, activeTab);
  }

  function getCurrentActiveTab() {
    // Find which output tab is currently selected
    const activeTabs = ['status', 'hex', 'source'];
    for (const tab of activeTabs) {
      const tabElement = qs(`.output .tab[data-tab="${tab}"]`);
      if (tabElement && tabElement.getAttribute('aria-selected') === 'true') {
        return tab;
      }
    }
    return 'status'; // fallback
  }


  function restoreModeOutputs(mode) {
    if (mode === 'compile') {
      // Restore compile-specific hex output (compiled binary)
      el.hexOutViewer.textContent = modeOutputs.compile.hexContent || '';
      el.compileSize.textContent = modeOutputs.compile.hexSize || '0 bytes';
      compiledBuffer = modeOutputs.compile.buffer;
      // Clear decompile-specific outputs
      el.sourceView.textContent = '';
      el.decompileSize.textContent = '0 chars';
      decompiledText = '';
    } else if (mode === 'decompile') {
      // Restore decompile-specific hex output (formatted input hex)
      el.hexOutViewer.textContent = modeOutputs.decompile.hexContent || '';
      el.compileSize.textContent = modeOutputs.decompile.hexSize || '0 bytes';
      el.sourceView.textContent = modeOutputs.decompile.sourceContent || '';
      el.decompileSize.textContent = modeOutputs.decompile.sourceSize || '0 chars';
      decompiledText = modeOutputs.decompile.text || '';
      // Clear compile-specific buffer
      compiledBuffer = null;
    }
  }

  function restoreActiveTab(mode, requestedTab) {
    // Check if the requested tab is available for this mode
    let tabToShow = requestedTab;

    if (mode === 'compile' && requestedTab === 'source') {
      // Source tab is disabled in compile mode, fallback to a valid tab
      tabToShow = modeOutputs.compile.hexContent ? 'hex' : 'status';
    }

    // Ensure the tab we're trying to show actually exists and is enabled
    const tabElement = qs(`.output .tab[data-tab="${tabToShow}"]`);
    if (tabElement && !tabElement.disabled) {
      reveal(tabToShow);
    } else {
      // Fallback to status if something goes wrong
      reveal('status');
    }
  }

  function bindTabs() {
    el.tabCompile.addEventListener('click', () => setMode('compile'));
    el.tabDecompile.addEventListener('click', () => setMode('decompile'));
  }

  function bindRun() {
    el.runBtn.addEventListener('click', () => run());
    document.addEventListener('keydown', (e) => {
      if ((e.metaKey||e.ctrlKey) && e.key === 'Enter') { e.preventDefault(); run(); }
    });
  }

  async function run() {
    if (st.mode === 'compile') return compile();

    // Determine which input tab is active
    const activeInput = el.toggleBtns.find(btn => btn.classList.contains('active'))?.dataset.input;

    // Only process JSONL if on File tab AND JSONL is loaded
    if (activeInput === 'file' && isJsonlFileLoaded && window.jsonlData) {
      return decompileJsonl();
    }

    // For all other cases (File tab with binary, Hex tab), use tab-aware getBinary()
    return decompile();
  }

  // ---------- Compile ----------
  async function compile() {
    const source = (el.fdoInput.value || '').trim();
    if (!source) return log('Enter FDO source to compile.', 'error');

    // Check for raw_data atoms (informational only - advanced feature)
    if (/raw_data\s*</.test(source)) {
      log('Note: raw_data atoms are for advanced use (chunk-compile API). They may not work in the browser UI.', 'info');
    }

    setBusy(true, 'Compiling…');

    try {
      const res = await fetch('/compile', {
        method: 'POST', headers: {'Content-Type':'application/json'},
        body: JSON.stringify({ source })
      });
      if (!res.ok) {
        const e = await safeJson(res);
        const detail = e && e.detail ? e.detail : e;
        const daemon = detail && detail.daemon ? detail.daemon : null;
        // Prefer normalized error payload from server when available
        const derrServer = daemon && daemon.normalized ? daemon.normalized : null;
        const { derr, cleanMessage } = derrServer ? { derr: derrServer, cleanMessage: (derrServer.message||`HTTP ${res.status}`) } : parseDaemonError(daemon, detail, res.status);
        renderDaemonError(derr, daemon);
        const err = new Error(cleanMessage);
        err._rendered = true;
        throw err;
      }
      compiledBuffer = await res.arrayBuffer();
      const bytes = new Uint8Array(compiledBuffer);
      el.compileSize.textContent = formatBytes(bytes.length);
      el.hexOutViewer.textContent = hexdump(bytes);

      // Save compile outputs to mode state
      modeOutputs.compile.hexContent = el.hexOutViewer.textContent;
      modeOutputs.compile.hexSize = el.compileSize.textContent;
      modeOutputs.compile.buffer = compiledBuffer;

      reveal('hex');
      modeOutputs.compile.activeTab = 'hex'; // Remember we switched to hex tab
      el.outPanels.hex.scrollTop = 0;
      log(`Compilation OK — ${formatBytes(bytes.length)}`, 'success');
    } catch (err) {
      if (!(err && err._rendered)) {
        log(`Compilation failed: ${err.message}`, 'error');
      }
      reveal('status');
      modeOutputs.compile.activeTab = 'status';
    } finally { setBusy(false); }
  }

  // ---------- Decompile ----------
  async function decompile() {
    const bytes = getBinary();
    if (!bytes) return;
    setBusy(true, 'Decompiling…');
    try {
      const base64 = btoa(String.fromCharCode.apply(null, bytes));
      const res = await fetch('/decompile', {
        method: 'POST', headers: {'Content-Type':'application/json'},
        body: JSON.stringify({ binary_data: base64 })
      });
      if (!res.ok) {
        const e = await safeJson(res);
        const detail = e && e.detail ? e.detail : e;
        const daemon = detail && detail.daemon ? detail.daemon : null;
        const derrServer = daemon && daemon.normalized ? daemon.normalized : null;
        const { derr, cleanMessage } = derrServer ? { derr: derrServer, cleanMessage: (derrServer.message||`HTTP ${res.status}`) } : parseDaemonError(daemon, detail, res.status);
        renderDaemonError(derr, daemon);
        const err = new Error(cleanMessage);
        err._rendered = true;
        throw err;
      }
      const data = await res.json(); // {source_code, output_size}
      decompiledText = data.source_code || '';
      el.decompileSize.textContent = `${(data.output_size||decompiledText.length).toLocaleString()} chars`;
      el.sourceView.textContent = decompiledText;

      // Populate hex output with formatted input hex
      el.compileSize.textContent = formatBytes(bytes.length);
      el.hexOutViewer.textContent = hexdump(bytes);

      // Save decompile outputs to mode state
      modeOutputs.decompile.hexContent = el.hexOutViewer.textContent;
      modeOutputs.decompile.hexSize = el.compileSize.textContent;
      modeOutputs.decompile.sourceContent = el.sourceView.textContent;
      modeOutputs.decompile.sourceSize = el.decompileSize.textContent;
      modeOutputs.decompile.text = decompiledText;

      reveal('source');
      modeOutputs.decompile.activeTab = 'source'; // Remember we switched to source tab
      log('Decompilation OK.', 'success');
    } catch (err) {
      if (!(err && err._rendered)) {
        log(`Decompilation failed: ${err.message}`, 'error');
      }
      reveal('status');
      modeOutputs.decompile.activeTab = 'status';
    } finally { setBusy(false); }
  }

  async function decompileJsonl() {
    if (!window.jsonlData) {
      log('No JSONL file loaded.', 'error');
      return;
    }

    // Show processing overlay with phased messaging
    processingUI.show();
    setBusy(true);
    log(`Starting JSONL processing of ${window.jsonlData.filename}...`, 'info');

    try {
      // Create FormData for file upload
      const formData = new FormData();
      const blob = new Blob([window.jsonlData.content], { type: 'application/json' });
      formData.append('file', blob, window.jsonlData.filename);

      const res = await fetch('/decompile-jsonl', {
        method: 'POST',
        body: formData
      });

      if (!res.ok) {
        const e = await safeJson(res);
        const detail = e && e.detail ? e.detail : e;
        throw new Error(detail?.error || `HTTP ${res.status}`);
      }

      const data = await res.json();

      if (!data.success) {
        throw new Error(data.error || 'JSONL processing failed');
      }

      // Display the decompiled source
      decompiledText = data.source || '';
      el.decompileSize.textContent = `${decompiledText.length.toLocaleString()} chars`;
      el.sourceView.textContent = decompiledText;

      // Display comprehensive JSONL processing results
      const metadata = `JSONL Processing Complete
${'='.repeat(50)}
Input: ${window.jsonlData.filename}
Total frames: ${data.frames_processed}
FDO frames found: ${data.fdo_frames_found}
Successfully decompiled: ${data.frames_decompiled_successfully}
Failed (non-FDO data): ${data.frames_failed_decompilation}
Success rate: ${(100 - data.decompilation_failure_rate).toFixed(1)}%
Processing time: ${data.decompilation_time}

Supported tokens: ${data.supported_tokens.join(', ')}
Chronological order: ${data.chronological_order}`;

      el.compileSize.textContent = `${data.fdo_frames_found} FDO frames`;
      el.hexOutViewer.textContent = metadata;

      // Save decompile outputs to mode state
      modeOutputs.decompile.hexContent = el.hexOutViewer.textContent;
      modeOutputs.decompile.hexSize = el.compileSize.textContent;
      modeOutputs.decompile.sourceContent = el.sourceView.textContent;
      modeOutputs.decompile.sourceSize = el.decompileSize.textContent;
      modeOutputs.decompile.text = decompiledText;

      reveal('source');
      modeOutputs.decompile.activeTab = 'source';

      // Success message with key stats
      const successRate = (100 - data.decompilation_failure_rate).toFixed(1);
      log(`JSONL complete: ${data.frames_decompiled_successfully}/${data.fdo_frames_found} FDO frames (${successRate}% success) in ${data.decompilation_time}`, 'success');
    } catch (err) {
      log(`JSONL processing failed: ${err.message}`, 'error');
      reveal('status');
      modeOutputs.decompile.activeTab = 'status';
    } finally {
      // Hide processing overlay
      processingUI.hide();
      setBusy(false);
    }
  }

  function getBinary() {
    // Determine which input tab is active
    const activeInput = el.toggleBtns.find(btn => btn.classList.contains('active'))?.dataset.input;

    if (activeInput === 'hex') {
      // Hex tab: only use hex input, never fall back to file
      const raw = (el.hexInput.value || '').trim();
      if (!raw) { log('Paste hex data to decompile.', 'error'); return null; }
      const clean = raw.replace(/[^0-9A-Fa-f]/g, '');
      if (clean.length % 2 !== 0) { log('Hex length must be even.', 'error'); return null; }
      const bytes = new Uint8Array(clean.length/2);
      for (let i=0;i<clean.length;i+=2) bytes[i/2] = parseInt(clean.substr(i,2),16);
      currentBinary = bytes;
      return bytes;
    } else if (activeInput === 'file') {
      // File tab: use loaded file data
      if (!currentBinary) { showToast('Choose a file to decompile.', 'error'); return null; }
      return currentBinary;
    }

    // Fallback: no active tab or unrecognized tab
    showToast('Select an input method.', 'error');
    return null;
  }

  function bindDecompileInputs() {
    // Toggle File/Hex
    el.toggleBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        el.toggleBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        const inputType = btn.dataset.input;

        // Hide all input views
        el.fileView.hidden = true;
        el.hexInputView.hidden = true;

        // Show the selected input view
        switch (inputType) {
          case 'hex':
            el.hexInputView.hidden = false;
            el.hexInput.removeAttribute('disabled');
            el.hexInput.focus();
            refreshHexDecoded();
            break;
          case 'file':
            el.fileView.hidden = false;
            el.binaryFile.focus();
            break;
        }
      });
    });

    // Single-click opens the file picker
    el.binaryDrop.addEventListener('click', (e) => { e.preventDefault(); el.binaryFile.click(); });

    // File -> bytes
    el.binaryFile.addEventListener('change', (e) => {
      const f = e.target.files?.[0]; if (!f) return;

      // Check if this is a JSONL file
      if (f.name.toLowerCase().endsWith('.jsonl')) {
        // Handle JSONL file for P3 frame processing
        const reader = new FileReader();
        reader.onload = async ev => {
          const jsonlContent = ev.target.result;

          // Set the JSONL loaded state
          isJsonlFileLoaded = true;
          currentBinary = null; // Clear binary data as we're handling JSONL
          el.openAsHexBtn.hidden = true;

          // Visually indicate loaded state on the drop zone
          el.binaryDrop.classList.add('loaded');
          const msgNode = el.binaryDrop.querySelector('span');
          if (msgNode) {
            msgNode.textContent = `${f.name} — JSONL P3 frames (click to change)`;
          }
          showToast(`Loaded JSONL file: ${f.name}`, 'success');

          // Store JSONL data for processing during decompile
          window.jsonlData = {
            filename: f.name,
            content: jsonlContent
          };
        };
        reader.readAsText(f);
      } else {
        // Handle binary file
        const reader = new FileReader();
        reader.onload = ev => {
          currentBinary = new Uint8Array(ev.target.result);
          el.fileDecoded.textContent = currentBinary.length.toLocaleString();
          el.openAsHexBtn.hidden = false;
          isJsonlFileLoaded = false;
          window.jsonlData = null; // Clear any JSONL data

          // Visually indicate loaded state on the drop zone
          el.binaryDrop.classList.add('loaded');
          const msgNode = el.binaryDrop.querySelector('span');
          if (msgNode) {
            msgNode.textContent = `${f.name} — ${formatBytes(currentBinary.length)} (click to change)`;
          }
          showToast(`Loaded ${f.name} (${formatBytes(currentBinary.length)})`, 'success');
        };
        reader.readAsArrayBuffer(f);
      }
    });

    // Open as Hex button functionality
    el.openAsHexBtn.addEventListener('click', () => {
      if (!currentBinary) return;
      // Convert binary to hex string
      const hexString = Array.from(currentBinary)
        .map(byte => byte.toString(16).padStart(2, '0'))
        .join('').toUpperCase();

      // Switch to hex tab and populate
      el.toggleBtns.forEach(b => b.classList.remove('active'));
      el.toggleBtns.find(b => b.dataset.input === 'hex').classList.add('active');
      el.fileView.hidden = true;
      el.hexInputView.hidden = false;
      el.hexInput.value = hexString;
      el.hexInput.focus();
      refreshHexDecoded();
      showToast('File opened as hex', 'success');
    });

    el.hexInput.addEventListener('input', refreshHexDecoded);
    el.hexInput.addEventListener('paste', (e) => { requestAnimationFrame(refreshHexDecoded); });

    // Hex detection for AOL/P3 frames
    setupHexDetection();
  }

  // ---------- Hex Detection for AOL/P3 Frames ----------
  let hexDetectionTimeout = null;
  let lastHexDetection = null;

  function setupHexDetection() {
    if (!el.hexInput || !el.hexStatusLine) return;

    // Real-time hex detection with debouncing
    el.hexInput.addEventListener('input', () => {
      clearTimeout(hexDetectionTimeout);
      hexDetectionTimeout = setTimeout(detectHexFrame, 300); // 300ms debounce
    });

    el.hexInput.addEventListener('paste', () => {
      requestAnimationFrame(() => {
        clearTimeout(hexDetectionTimeout);
        hexDetectionTimeout = setTimeout(detectHexFrame, 100); // Faster response after paste
      });
    });

    // Clickable status bar for FDO extraction
    el.hexStatusLine.addEventListener('click', (e) => {
      if (el.hexStatusLine.classList.contains('detected')) {
        extractFdoFromHex();
      }
    });

    // Keyboard support for accessibility
    el.hexStatusLine.addEventListener('keydown', (e) => {
      if ((e.key === 'Enter' || e.key === ' ') && el.hexStatusLine.classList.contains('detected')) {
        e.preventDefault();
        extractFdoFromHex();
      }
    });
  }

  async function detectHexFrame() {
    const hexData = (el.hexInput.value || '').trim();

    if (!hexData) {
      updateHexDetectionStatus('default', '');
      hideHexActions();
      lastHexDetection = null;
      return;
    }

    // Show analyzing status
    updateHexDetectionStatus('detecting', 'Analyzing hex data...');

    try {
      // Clean and validate hex
      const cleanHex = hexData.replace(/[^0-9A-Fa-f]/g, '');
      if (cleanHex.length === 0 || cleanHex.length % 2 !== 0) {
        updateHexDetectionStatus('error', 'Invalid hex format');
        hideHexActions();
        lastHexDetection = null;
        return;
      }

      // Convert hex to base64 for API
      const bytes = new Uint8Array(cleanHex.length / 2);
      for (let i = 0; i < cleanHex.length; i += 2) {
        bytes[i / 2] = parseInt(cleanHex.substr(i, 2), 16);
      }
      const base64Data = btoa(String.fromCharCode.apply(null, bytes));

      // Detect P3/AOL frame
      const response = await fetch('/detect-fdo', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ p3_frame: base64Data })
      });

      const result = await response.json();
      lastHexDetection = result;

      if (result.success && result.fdo_detected) {
        const meta = result.fdo_metadata;
        updateHexDetectionStatus('detected',
          `AOL/P3 frame detected • ${meta.token} token • ${meta.fdo_size} bytes`
        );
        showHexActions();
      } else if (result.success && result.p3_frame_valid) {
        updateHexDetectionStatus('invalid',
          'Valid P3 frame, no FDO data detected'
        );
        hideHexActions();
      } else {
        updateHexDetectionStatus('neutral', 'No AOL/P3 frame found');
        hideHexActions();
      }

    } catch (error) {
      console.error('Hex detection error:', error);
      updateHexDetectionStatus('error', 'Network error during detection');
      hideHexActions();
      lastHexDetection = null;
    }
  }

  function updateHexDetectionStatus(state, message) {
    if (!el.hexStatusLine || !el.hexStatusText) return;

    // Show/hide status line based on whether there's a message
    if (message) {
      el.hexStatusLine.hidden = false;

      // Remove all state classes from status line
      el.hexStatusLine.classList.remove('detecting', 'detected', 'error', 'invalid', 'neutral', 'warning');

      // Add current state class to status line
      if (state !== 'default') {
        el.hexStatusLine.classList.add(state);
      }

      // Update text
      el.hexStatusText.textContent = message;

      // Manage accessibility attributes based on state
      if (state === 'detected') {
        el.hexStatusLine.setAttribute('tabindex', '0');
        el.hexStatusLine.setAttribute('aria-disabled', 'false');
        el.hexStatusLine.setAttribute('aria-label', 'Extract FDO from detected AOL/P3 frame');
      } else {
        el.hexStatusLine.setAttribute('tabindex', '-1');
        el.hexStatusLine.setAttribute('aria-disabled', 'true');
        el.hexStatusLine.setAttribute('aria-label', 'Hex detection status');
      }

      // Add subtle border feedback to textarea
      el.hexInput.classList.remove('detecting', 'detected', 'error', 'warning');
      if (state !== 'default' && state !== 'neutral') {
        el.hexInput.classList.add(state);
      }
    } else {
      el.hexStatusLine.hidden = true;
      el.hexInput.classList.remove('detecting', 'detected', 'error', 'warning');
    }
  }

  function showHexActions() {
    // Status bar is now clickable - accessibility handled in updateHexDetectionStatus
    // This function kept for compatibility but functionality moved to updateHexDetectionStatus
  }

  function hideHexActions() {
    // Status bar is now not clickable - accessibility handled in updateHexDetectionStatus
    // This function kept for compatibility but functionality moved to updateHexDetectionStatus
  }

  function extractFdoFromHex() {
    if (!lastHexDetection || !lastHexDetection.fdo_detected) {
      showToast('No FDO data detected to extract', 'error');
      return;
    }

    try {
      // Decode base64 FDO data to hex
      const fdoBytes = atob(lastHexDetection.fdo_data);
      const hexString = Array.from(fdoBytes)
        .map(char => char.charCodeAt(0).toString(16).padStart(2, '0'))
        .join('').toUpperCase();

      // Replace current hex input with extracted FDO data
      el.hexInput.value = hexString;
      el.hexInput.focus();
      refreshHexDecoded();

      // Show success message before clearing detection
      const meta = lastHexDetection?.fdo_metadata;
      if (meta) {
        showToast(`FDO data extracted: ${meta.token} token, ${meta.fdo_size} bytes`, 'success');
      } else {
        showToast('FDO data extracted successfully', 'success');
      }

      // Clear detection status since we've extracted the data
      updateHexDetectionStatus('default', '');
      hideHexActions();
      lastHexDetection = null;

    } catch (error) {
      console.error('FDO extraction error:', error);
      showToast('Failed to extract FDO data', 'error');
    }
  }

  function isHexString(str) {
    const cleaned = str.replace(/[^0-9A-Fa-f]/g, '');
    return cleaned.length > 0 && cleaned.length === str.replace(/[\s\-:]/g, '').length;
  }

  // ---------- Output tabs & helpers ----------
  function bindOutputTabs() {
    el.outTabs.forEach(btn => btn.addEventListener('click', (e) => {
      if (btn.disabled) {
        e.preventDefault();
        return;
      }
      reveal(btn.dataset.tab);
    }));
  }
  function reveal(tab) {
    ['status','hex','source'].forEach(t => {
      qs(`.output .tab[data-tab="${t}"]`).setAttribute('aria-selected', String(t===tab));
      el.outPanels[t].hidden = t!==tab;
    });
  }
  function bindDownloads() {
    el.downloadBin.addEventListener('click', () => {
      if (!compiledBuffer) return;
      const blob = new Blob([compiledBuffer], {type:'application/octet-stream'});
      const a = document.createElement('a'); a.href = URL.createObjectURL(blob);
      a.download = 'compiled.fdo'; a.click(); URL.revokeObjectURL(a.href);
      showToast('Binary downloaded successfully', 'success');
    });
    el.copyHex.addEventListener('click', async () => {
      try {
        if (!compiledBuffer) {
          showToast('No hex content to copy', 'error');
          return;
        }
        const bytes = new Uint8Array(compiledBuffer);
        // Copy raw hex: contiguous uppercase hex pairs, no offsets/ASCII/spacing
        const rawHex = Array.from(bytes).map(v => v.toString(16).padStart(2,'0')).join('').toUpperCase();
        if (!rawHex) {
          showToast('No hex content to copy', 'error');
          return;
        }
        const ok = await copyTextToClipboard(rawHex);
        showToast(ok ? 'Hex copied to clipboard' : 'Failed to copy hex', ok ? 'success' : 'error');
      } catch (err) {
        showToast('Failed to copy hex', 'error');
      }
    });
    el.downloadTxt.addEventListener('click', () => {
      if (!decompiledText) return;
      const blob = new Blob([decompiledText], {type:'text/plain'});
      const a = document.createElement('a'); a.href = URL.createObjectURL(blob);
      a.download = 'decompiled.txt'; a.click(); URL.revokeObjectURL(a.href);
      showToast('Source downloaded successfully', 'success');
    });
    el.copySource.addEventListener('click', async () => {
      try {
        const sourceContent = decompiledText || '';
        if (!sourceContent.trim()) {
          showToast('No source content to copy', 'error');
          return;
        }
        const ok = await copyTextToClipboard(sourceContent);
        showToast(ok ? 'Source copied to clipboard' : 'Failed to copy source', ok ? 'success' : 'error');
      } catch (err) {
        showToast('Failed to copy source', 'error');
      }
    });
  }

  // ---------- Examples menu ----------
  function setupExamples() {
    if (!el.examplesBtn || !el.examplesMenu) {
      console.warn('Examples elements not found');
      return;
    }

    let searchDebounceTimer = null;
    let currentSearchQuery = '';
    let allExamples = [];
    let searchInput = null;
    let searchContainer = null;
    let examplesContainer = null;
    let loadingIndicator = null;
    let noResultsMsg = null;

    async function loadExamples(searchQuery = '') {
      try {
        // Build URL with search param if provided
        const url = searchQuery ? `/examples?search=${encodeURIComponent(searchQuery)}` : '/examples';
        const res = await fetch(url);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const list = await res.json();
        return list || [];
      } catch (err) {
        console.error('Failed to load examples:', err);
        showToast('Failed to load examples', 'error');
        return [];
      }
    }

    function createSearchUI() {
      // Clear and rebuild menu structure
      el.examplesMenu.innerHTML = '';
      el.examplesMenu.style.minWidth = '400px';
      el.examplesMenu.style.maxHeight = '60vh';
      el.examplesMenu.style.display = 'flex';
      el.examplesMenu.style.flexDirection = 'column';

      // Create search container
      searchContainer = document.createElement('div');
      searchContainer.style.padding = '8px';
      searchContainer.style.borderBottom = '1px solid var(--border)';
      searchContainer.style.position = 'sticky';
      searchContainer.style.top = '0';
      searchContainer.style.background = 'var(--background)';
      searchContainer.style.zIndex = '10';

      // Create search input wrapper with icon
      const searchWrapper = document.createElement('div');
      searchWrapper.style.position = 'relative';
      searchWrapper.style.display = 'flex';
      searchWrapper.style.alignItems = 'center';

      // Search icon
      const searchIcon = document.createElement('span');
      searchIcon.innerHTML = '';
      searchIcon.style.position = 'absolute';
      searchIcon.style.left = '10px';
      searchIcon.style.fontSize = '14px';
      searchIcon.style.opacity = '0.6';
      searchIcon.style.pointerEvents = 'none';

      // Create search input
      searchInput = document.createElement('input');
      searchInput.type = 'text';
      searchInput.placeholder = 'Search atoms or filenames...';
      searchInput.style.width = '100%';
      searchInput.style.padding = '8px 12px 8px 32px';
      searchInput.style.border = '1px solid var(--border)';
      searchInput.style.borderRadius = '4px';
      searchInput.style.fontSize = '13px';
      searchInput.style.background = 'var(--background)';
      searchInput.style.color = 'var(--text)';
      searchInput.setAttribute('autocomplete', 'off');
      searchInput.setAttribute('spellcheck', 'false');

      // Clear button (initially hidden)
      const clearBtn = document.createElement('button');
      clearBtn.innerHTML = '×';
      clearBtn.type = 'button';
      clearBtn.style.position = 'absolute';
      clearBtn.style.right = '8px';
      clearBtn.style.background = 'none';
      clearBtn.style.border = 'none';
      clearBtn.style.color = 'var(--text-secondary)';
      clearBtn.style.cursor = 'pointer';
      clearBtn.style.padding = '4px';
      clearBtn.style.fontSize = '14px';
      clearBtn.style.display = 'none';
      clearBtn.style.opacity = '0.7';
      clearBtn.title = 'Clear search';
      
      clearBtn.addEventListener('click', (e) => {
        e.preventDefault();
        searchInput.value = '';
        clearBtn.style.display = 'none';
        currentSearchQuery = '';
        performSearch('');
      });

      searchWrapper.appendChild(searchIcon);
      searchWrapper.appendChild(searchInput);
      searchWrapper.appendChild(clearBtn);
      searchContainer.appendChild(searchWrapper);

      // Loading indicator
      loadingIndicator = document.createElement('div');
      loadingIndicator.textContent = 'Searching...';
      loadingIndicator.style.padding = '12px';
      loadingIndicator.style.textAlign = 'center';
      loadingIndicator.style.color = 'var(--text-secondary)';
      loadingIndicator.style.fontSize = '13px';
      loadingIndicator.style.display = 'none';

      // No results message
      noResultsMsg = document.createElement('div');
      noResultsMsg.textContent = 'No matching examples found';
      noResultsMsg.style.padding = '20px';
      noResultsMsg.style.textAlign = 'center';
      noResultsMsg.style.color = 'var(--text-secondary)';
      noResultsMsg.style.fontSize = '13px';
      noResultsMsg.style.display = 'none';

      // Examples container
      examplesContainer = document.createElement('div');
      examplesContainer.style.flex = '1';
      examplesContainer.style.overflowY = 'auto';
      examplesContainer.style.minHeight = '100px';
      examplesContainer.style.maxHeight = 'calc(60vh - 60px)';

      el.examplesMenu.appendChild(searchContainer);
      el.examplesMenu.appendChild(loadingIndicator);
      el.examplesMenu.appendChild(noResultsMsg);
      el.examplesMenu.appendChild(examplesContainer);

      // Search input event handler with debouncing
      searchInput.addEventListener('input', (e) => {
        const query = e.target.value.trim();
        clearBtn.style.display = query ? 'block' : 'none';
        
        // Clear existing timer
        if (searchDebounceTimer) {
          clearTimeout(searchDebounceTimer);
        }

        // Set new timer for debounced search
        searchDebounceTimer = setTimeout(() => {
          if (query !== currentSearchQuery) {
            currentSearchQuery = query;
            performSearch(query);
          }
        }, 300); // 300ms debounce
      });

      // Prevent menu from closing when interacting with search
      searchInput.addEventListener('click', (e) => {
        e.stopPropagation();
      });

      searchInput.addEventListener('keydown', (e) => {
        e.stopPropagation();
        if (e.key === 'Escape') {
          searchInput.value = '';
          clearBtn.style.display = 'none';
          currentSearchQuery = '';
          performSearch('');
        }
      });
    }

    async function performSearch(query) {
      // Show loading state
      loadingIndicator.style.display = 'block';
      noResultsMsg.style.display = 'none';
      examplesContainer.innerHTML = '';

      // Load examples with search query
      const examples = await loadExamples(query);

      // Hide loading
      loadingIndicator.style.display = 'none';

      if (examples.length === 0 && query) {
        noResultsMsg.style.display = 'block';
        return;
      }

      renderExamples(examples.slice(0, 200)); // Cap at 200 for performance
    }

    function renderExamples(examples) {
      examplesContainer.innerHTML = '';
      
      if (examples.length === 0) {
        noResultsMsg.style.display = 'block';
        return;
      }

      noResultsMsg.style.display = 'none';

      examples.forEach(ex => {
        const b = document.createElement('button');
        b.type = 'button';
        b.setAttribute('role', 'menuitem');
        b.style.width = '100%';
        b.style.textAlign = 'left';
        b.style.padding = '8px 12px';
        b.style.border = 'none';
        b.style.background = 'none';
        b.style.cursor = 'pointer';
        b.style.color = 'var(--text)';
        b.style.fontSize = '13px';
        b.style.transition = 'background 0.15s';
        
        // Create content with name and size
        const nameSpan = document.createElement('span');
        nameSpan.textContent = ex.label || ex.name || 'Example';
        nameSpan.style.display = 'inline-block';
        nameSpan.style.marginRight = '8px';
        
        const sizeSpan = document.createElement('span');
        sizeSpan.textContent = `(${ex.size?.toLocaleString?.() || '0'} bytes)`;
        sizeSpan.style.color = 'var(--text-secondary)';
        sizeSpan.style.fontSize = '12px';
        
        b.appendChild(nameSpan);
        b.appendChild(sizeSpan);
        b.title = `${ex.name} — ${ex.size?.toLocaleString?.() || ''} bytes`;

        // Hover effect
        b.addEventListener('mouseenter', () => {
          b.style.background = 'var(--hover)';
        });
        b.addEventListener('mouseleave', () => {
          b.style.background = 'none';
        });

        b.addEventListener('click', (e) => {
          e.preventDefault();
          e.stopPropagation();

          // Load example content
          el.fdoInput.value = ex.text || ex.source || '';
          el.examplesMenu.hidden = true;
          el.examplesBtn.setAttribute('aria-expanded', 'false');
          setMode('compile');

          // Set up example state for document bar
          currentScript = {
            name: ex.name || 'Example',
            is_example: true,
            is_readonly: true,
            is_favorite: false
          };
          originalContent = ex.text || ex.source || '';
          hasUnsavedChanges = false;

          updateStatusBar();
          setStatusOperation(`Loaded example: ${ex.name} at ${new Date().toLocaleTimeString()}`);
          log(`Loaded example: ${ex.name} (${(ex.text || ex.source || '').length} chars)`);
          updateValidationStatus();
          el.fdoInput.focus();
          el.fdoInput.setSelectionRange(0, 0); // Set cursor to start
          el.fdoInput.scrollTop = 0; // Scroll to top
          showToast(`Loaded example: ${ex.name}`, 'success');
        });

        examplesContainer.appendChild(b);
      });
    }

    async function openExamplesMenu() {
      // Create UI if not already created
      if (!searchContainer) {
        createSearchUI();
      }

      // Reset search on open
      if (searchInput) {
        searchInput.value = '';
        currentSearchQuery = '';
      }

      // Load initial examples
      await performSearch('');

      // Focus search input
      setTimeout(() => {
        if (searchInput) searchInput.focus();
      }, 50);
    }

    el.examplesBtn.addEventListener('click', async (e) => {
      e.preventDefault();
      e.stopPropagation();
      const isHidden = el.examplesMenu.hasAttribute('hidden') || el.examplesMenu.hidden;
      if (isHidden) {
        await openExamplesMenu();
      }
      el.examplesMenu.hidden = !isHidden;
      el.examplesBtn.setAttribute('aria-expanded', String(!isHidden));
    });

    document.addEventListener('click', (e)=>{
      if (!el.examplesBtn.contains(e.target) && !el.examplesMenu.contains(e.target)) {
        el.examplesMenu.hidden = true;
        el.examplesBtn.setAttribute('aria-expanded', 'false');
      }
    });
  }

  // ---------- API Modal ----------
  function setupAPIModal() {
    if (!el.apiBtn || !el.apiModal) {
      console.warn('API modal elements not found');
      return;
    }

    // Update base URL in modal content based on current location
    const baseUrlElement = qs('.api-base-url');
    if (baseUrlElement) {
      baseUrlElement.textContent = `${window.location.protocol}//${window.location.host}`;
    }

    // Setup tab functionality
    setupAPITabs();

    // Show modal
    el.apiBtn.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      el.apiModal.hidden = false;
      el.apiModal.focus();
      document.body.style.overflow = 'hidden'; // Prevent background scroll
    });

    // Close modal - close button
    el.apiModalClose.addEventListener('click', (e) => {
      e.preventDefault();
      closeAPIModal();
    });

    // Close modal - backdrop click
    el.apiBackdrop.addEventListener('click', (e) => {
      e.preventDefault();
      closeAPIModal();
    });

    // Close modal - escape key
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && !el.apiModal.hidden) {
        e.preventDefault();
        closeAPIModal();
      }
    });

    // Setup copy buttons
    setupAPICopyButtons();
  }

  function closeAPIModal() {
    el.apiModal.hidden = true;
    document.body.style.overflow = ''; // Restore background scroll
    el.apiBtn.focus(); // Return focus to trigger button
  }

  function setupAPICopyButtons() {
    const copyButtons = qsa('.copy-btn');
    copyButtons.forEach(btn => {
      btn.addEventListener('click', async (e) => {
        e.preventDefault();
        const copyType = btn.dataset.copy;
        let textToCopy = '';

        // Get the code content from the previous sibling pre element
        const codeBlock = btn.parentElement.querySelector('pre code');
        if (codeBlock) {
          textToCopy = codeBlock.textContent;
        }

        if (textToCopy) {
          const success = await copyTextToClipboard(textToCopy);
          if (success) {
            // Temporarily change button text to show success
            const originalText = btn.textContent;
            btn.textContent = 'Copied!';
            btn.style.background = 'var(--success)';
            btn.style.color = 'var(--text-inverse)';

            setTimeout(() => {
              btn.textContent = originalText;
              btn.style.background = '';
              btn.style.color = '';
            }, 2000);

            showToast(`${copyType.charAt(0).toUpperCase() + copyType.slice(1)} command copied to clipboard`, 'success');
          } else {
            showToast('Failed to copy to clipboard', 'error');
          }
        }
      });
    });
  }

  function setupAPITabs() {
    const tabButtons = qsa('.api-tab');
    const tabPanels = qsa('.api-tab-panel');

    tabButtons.forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        const targetTab = btn.dataset.tab;

        // Update button states
        tabButtons.forEach(b => {
          b.classList.remove('active');
          b.setAttribute('aria-selected', 'false');
        });
        btn.classList.add('active');
        btn.setAttribute('aria-selected', 'true');

        // Update panel visibility
        tabPanels.forEach(panel => {
          panel.classList.remove('active');
        });
        const targetPanel = qs(`#tab-${targetTab}`);
        if (targetPanel) {
          targetPanel.classList.add('active');
        }

        // Re-setup copy buttons for newly visible content
        setupAPICopyButtons();
      });
    });
  }

  // ---------- UI helpers ----------
  function log(msg, level='info'){
    const line=document.createElement('div');
    line.className=`log-line ${level}`;
    if (msg.toLowerCase().includes('syntax error')) {
        line.classList.add('syntax-error');
    }
    line.textContent=msg;
    el.statusLog.prepend(line);
    // Keep only 100 lines
    const max = 100;
    while (el.statusLog.children.length > max) el.statusLog.lastChild.remove();
  }

  function formatBytes(n){
    if(n<1024) return `${n} bytes`;
    const kb=n/1024;
    if(kb<1024) return `${kb.toFixed(1)} KB`;
    const mb=kb/1024;
    return `${mb.toFixed(1)} MB`;
  }

  function visible(node){
    return node && node.offsetParent !== null;
  }

  function toggle(node, show){
    node.hidden = !show;
    node.style.display = show ? '' : 'none';
  }

  function hexdump(bytes, {cols=16, group=2} = {}) {
    let out = '';
    const b = (bytes instanceof Uint8Array) ? bytes : new Uint8Array(bytes || 0);
    for (let i = 0; i < b.length; i += cols) {
      const chunk = b.slice(i, i + cols);
      const hex = Array.from(chunk)
        .map(v => v.toString(16).padStart(2, '0'))
        .map((v, idx) => (idx && group && idx % group === 0) ? ` ${v}` : v)
        .join(' ')
        .toUpperCase();
      const ascii = Array.from(chunk).map(v => (v >= 32 && v < 127) ? String.fromCharCode(v) : '.').join('');
      out += `${i.toString(16).padStart(8,'0')}  ${hex.padEnd(cols*3 + Math.floor(cols/group) - 2, ' ')}  |${ascii}|\n`;
    }
    return out || '(no data)';
  }

  async function safeJson(res){
    try{ return await res.json(); } catch{ return {}; }
  }


  function parseDaemonError(daemon, detail, status){
    let derr = daemon?.json?.error;
    if (!derr && typeof daemon?.text === 'string') {
      // Try strict JSON first
      try { const parsed = JSON.parse(daemon.text); derr = parsed && parsed.error; } catch(_) {
        // Lenient parse from pretty text
        const txt = daemon.text;
        const get = (re) => { const m = txt.match(re); return m ? m[1] : undefined; };
        const msgRaw = get(/"message"\s*:\s*"([\s\S]*?)"/);
        const lineNum = get(/"line"\s*:\s*(\d+)/);
        const kind = get(/"kind"\s*:\s*"([^"]*)"/);
        const hint = get(/"hint"\s*:\s*"([\s\S]*?)"/);
        // Find context-like lines by scanning for lines with "|"
        const ctx = [];
        txt.split(/\r?\n/).forEach((ln) => {
          const s = ln.trim().replace(/^,?\"|\",?$/g,'');
          if (/^(>>\s*)?\d+\s\|\s/.test(s)) ctx.push(s);
        });
        if (msgRaw || lineNum || kind || hint || ctx.length) {
          derr = {
            message: msgRaw || 'Error',
            line: lineNum ? parseInt(lineNum, 10) : undefined,
            kind,
            context: ctx.length ? ctx : undefined,
            hint
          };
        }
      }
    }
    const message = derr?.message || detail?.error || `HTTP ${status}`;
    // Remove Ada32 prefix like "Ada32 error rc=0x30014 (196628): "
    const cleanMessage = message.replace(/^Ada32\s+error\s+rc=[^:]+:\s*/i, '').trim();
    return { derr, cleanMessage };
  }

  function renderDaemonError(derr, daemon){
    if (derr){
      const headline = derr.message || 'Error';
      const title = derr.kind && !headline.startsWith(derr.kind) ? `${derr.kind}: ${headline}` : headline;
      // choose focused context line (with >>), else line-matched, else first
      let contextLine = null;
      if (Array.isArray(derr.context) && derr.context.length){
        contextLine = derr.context.find(l => /^\s*>>/.test(l)) || null;
        if (!contextLine && typeof derr.line === 'number'){
          const ln = String(derr.line);
          contextLine = derr.context.find(l => new RegExp(`^\s*(?:>>\s*)?${ln}\s\|`).test(l)) || null;
        }
        if (!contextLine) contextLine = derr.context[0];
      }
      // Because log() prepends, log context second so it appears below the headline (top-down)
      log(title, 'error');
      if (contextLine) log(contextLine, 'error');
    } else if (daemon?.text){
      // As a last resort, print a compact first line of the text blob
      const first = (daemon.text || '').split(/\r?\n/)[0].trim();
      if (first) log(first, 'error');
    }
  }

  function setBusy(on, label){
    el.runBtn.disabled = on;
    el.runBtn.classList.toggle('loading', on);
    if(on) log(label||'Working…');
  }

  // ================================
  // JSONL Processing UI Manager
  // ================================
  class JsonlProcessingUI {
    constructor() {
      this.overlay = qs('#processingOverlay');
      this.messageEl = qs('#processingMessage');
      this.timerEl = qs('#processingTimer');
      this.startTime = null;
      this.timerInterval = null;
      this.phaseTimeouts = [];

      // Phase messages based on elapsed time
      this.phases = [
        { time: 0, message: 'Parsing JSONL frames and preparing for decompilation...' },
        { time: 15, message: 'Decompiling FDO frames from P3 protocol data...' },
        { time: 30, message: 'Processing continues - large files take time to decompile thoroughly...' },
        { time: 60, message: 'Still processing - complex FDO data requires careful decompilation...' },
        { time: 90, message: 'Making progress - your patience is appreciated...' },
        { time: 120, message: 'Almost there - finalizing decompilation results...' },
        { time: 150, message: 'Wrapping up - this is a particularly large dataset...' },
        { time: 180, message: 'Final stages - completing decompilation and building output...' }
      ];
    }

    show() {
      this.startTime = Date.now();
      this.overlay.hidden = false;
      this.overlay.setAttribute('aria-busy', 'true');
      this.messageEl.textContent = this.phases[0].message;
      this.timerEl.textContent = '0s';

      // Start elapsed time counter
      this.timerInterval = setInterval(() => this.updateTimer(), 1000);

      // Schedule phase message updates
      this.schedulePhaseUpdates();
    }

    hide() {
      this.overlay.hidden = true;
      this.overlay.setAttribute('aria-busy', 'false');

      // Clear timer and phase timeouts
      if (this.timerInterval) {
        clearInterval(this.timerInterval);
        this.timerInterval = null;
      }

      this.phaseTimeouts.forEach(timeout => clearTimeout(timeout));
      this.phaseTimeouts = [];

      this.startTime = null;
    }

    updateTimer() {
      if (!this.startTime) return;

      const elapsed = Math.floor((Date.now() - this.startTime) / 1000);
      const minutes = Math.floor(elapsed / 60);
      const seconds = elapsed % 60;

      if (minutes > 0) {
        this.timerEl.textContent = `${minutes}m ${seconds}s`;
      } else {
        this.timerEl.textContent = `${seconds}s`;
      }
    }

    schedulePhaseUpdates() {
      // Skip first phase (already shown)
      for (let i = 1; i < this.phases.length; i++) {
        const phase = this.phases[i];
        const timeout = setTimeout(() => {
          this.messageEl.textContent = phase.message;
        }, phase.time * 1000);

        this.phaseTimeouts.push(timeout);
      }
    }
  }

  // Initialize processing UI manager
  const processingUI = new JsonlProcessingUI();

  // Clipboard helper: uses async Clipboard API on secure contexts, falls back to execCommand on HTTP
  async function copyTextToClipboard(text){
    if (!text) return false;
    try {
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(text);
        return true;
      }
    } catch (_) { /* fall through to legacy path */ }
    try {
      const ta = document.createElement('textarea');
      ta.value = text;
      ta.setAttribute('readonly','');
      ta.style.position = 'fixed';
      ta.style.top = '-1000px';
      ta.style.left = '-1000px';
      ta.style.opacity = '0';
      document.body.appendChild(ta);
      ta.focus();
      ta.select();
      ta.setSelectionRange(0, ta.value.length);
      const ok = document.execCommand('copy');
      document.body.removeChild(ta);
      return !!ok;
    } catch (_) {
      return false;
    }
  }

  // ---------- Toast System ----------
  function showToast(message, type = 'info', duration = 3000) {
    const container = qs('#toastContainer');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;

    container.appendChild(toast);

    // Trigger animation
    requestAnimationFrame(() => {
      toast.classList.add('show');
    });

    // Auto-remove
    setTimeout(() => {
      toast.classList.remove('show');
      setTimeout(() => {
        if (toast.parentNode) {
          toast.parentNode.removeChild(toast);
        }
      }, 250);
    }, duration);
  }

  function setupBottomResize(){
    const split = document.querySelector('.content-split');   // NEW selector
    const out = document.querySelector('.output');
    if (!split || !out) return;
    let startY=0, startH=out.clientHeight;
    const move = (e)=>{
      const y=(e.clientY||e.touches?.[0]?.clientY||0);
      const dy=y-startY;
      const h=Math.min(window.innerHeight*0.85, Math.max(180, startH - dy));
      out.style.maxHeight=h+'px';
      out.style.height=h+'px';
    };
    const up = ()=>{
      window.removeEventListener('mousemove',move);
      window.removeEventListener('mouseup',up);
      window.removeEventListener('touchmove',move);
      window.removeEventListener('touchend',up);
    };
    const down = (e)=>{
      startY=(e.clientY||e.touches?.[0]?.clientY||0);
      startH=out.clientHeight;
      window.addEventListener('mousemove',move);
      window.addEventListener('mouseup',up);
      window.addEventListener('touchmove',move);
      window.addEventListener('touchend',up);
    };
    split.addEventListener('mousedown',down);
    split.addEventListener('touchstart',down,{passive:true});
  }

  // ---------- ASCII Atom Support ----------
  // ASCII helpers removed

  // P3 extraction removed - refreshHexDecoded functionality moved to status bar
  function refreshHexDecoded() {
    // Legacy function - now triggers status bar update for compatibility
    updateStatusBar();
  }

  async function extractFDOFromP3() {
    const hexData = el.hexInput.value.trim();

    if (!hexData) {
      showToast('No hex data to extract from', 'error');
      return;
    }

    log('Extracting FDO from P3 packets...');
    el.extractFdoBtn.disabled = true;
    el.extractFdoBtn.textContent = 'Extracting...';

    try {
      const response = await fetch('/extract-fdo', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ hex_data: hexData })
      });

      const result = await response.json();

      if (result.success) {
        // Replace hex input with extracted FDO data
        el.hexInput.value = result.fdo_hex;
        refreshHexDecoded();

        // Log success details with enhanced metrics
        log(`FDO extracted successfully`);
        log(`  Found ${result.frames_found} P3 frames`);
        log(`  Extracted ${result.total_fdo_bytes} FDO bytes`);
        if (result.skipped_non_fdo_packets > 0) {
          log(`  Skipped ${result.skipped_non_fdo_packets} non-FDO packets`);
        }
        if (result.frames_with_crc_issues > 0) {
          log(`  ${result.frames_with_crc_issues} frames had CRC issues`);
        }

        showToast(`Extracted ${result.total_fdo_bytes} bytes of FDO data from ${result.frames_found} P3 frames`, 'success');
      } else {
        log(`✗ P3 extraction failed: ${result.error}`);
        if (result.skipped_non_fdo_packets > 0) {
          log(`  Skipped ${result.skipped_non_fdo_packets} non-FDO packets`);
        }
        showToast(`Extraction failed: ${result.error}`, 'error');
      }
    } catch (error) {
      log(`✗ P3 extraction error: ${error.message}`);
      showToast(`Extraction error: ${error.message}`, 'error');
    } finally {
      el.extractFdoBtn.disabled = false;
      el.extractFdoBtn.textContent = 'Extract FDO';
    }
  }

  // ---------- File Management System ----------
  function setupFileManagement() {
    if (!el.fileBtn || !el.fileMenu) {
      console.warn('File management elements not found');
      return;
    }

    bindFileMenu();
    bindSaveDialog();
    bindFileBrowser();
    bindConfirmDialog();
    setupUnsavedChangesTracking();
    setupKeyboardShortcuts();

    log('File management initialized');
  }

  function bindFileMenu() {
    // File menu toggle
    el.fileBtn.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      const isHidden = el.fileMenu.hasAttribute('hidden') || el.fileMenu.hidden;
      el.fileMenu.hidden = !isHidden;
      el.fileBtn.setAttribute('aria-expanded', String(!isHidden));

      // Focus first menu item when opening
      if (!isHidden) {
        const firstItem = el.fileMenu.querySelector('button[role="menuitem"]:not([disabled])');
        if (firstItem) {
          setTimeout(() => firstItem.focus(), 50);
        }
      }
    });

    // Keyboard navigation for File menu
    el.fileMenu.addEventListener('keydown', (e) => {
      const items = Array.from(el.fileMenu.querySelectorAll('button[role="menuitem"]:not([disabled])'));
      const currentIndex = items.indexOf(document.activeElement);

      switch(e.key) {
        case 'ArrowDown':
          e.preventDefault();
          const nextIndex = (currentIndex + 1) % items.length;
          items[nextIndex]?.focus();
          break;
        case 'ArrowUp':
          e.preventDefault();
          const prevIndex = currentIndex - 1 < 0 ? items.length - 1 : currentIndex - 1;
          items[prevIndex]?.focus();
          break;
        case 'Escape':
          e.preventDefault();
          el.fileMenu.hidden = true;
          el.fileBtn.setAttribute('aria-expanded', 'false');
          el.fileBtn.focus();
          break;
        case 'Home':
          e.preventDefault();
          items[0]?.focus();
          break;
        case 'End':
          e.preventDefault();
          items[items.length - 1]?.focus();
          break;
      }
    });

    // Close file menu when clicking outside
    document.addEventListener('click', (e) => {
      if (!el.fileBtn.contains(e.target) && !el.fileMenu.contains(e.target)) {
        el.fileMenu.hidden = true;
        el.fileBtn.setAttribute('aria-expanded', 'false');
      }
    });

    // Close on Escape key globally
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && !el.fileMenu.hidden) {
        el.fileMenu.hidden = true;
        el.fileBtn.setAttribute('aria-expanded', 'false');
        el.fileBtn.focus();
      }
    });

    // File menu actions
    el.saveBtn.addEventListener('click', () => {
      el.fileMenu.hidden = true;
      handleSave();
    });

    el.saveAsBtn.addEventListener('click', () => {
      el.fileMenu.hidden = true;
      handleSaveAs();
    });

    el.openBtn.addEventListener('click', () => {
      el.fileMenu.hidden = true;
      handleOpen();
    });

    el.recentBtn.addEventListener('click', () => {
      el.fileMenu.hidden = true;
      handleRecentFiles();
    });

    el.newBtn.addEventListener('click', () => {
      el.fileMenu.hidden = true;
      handleNew();
    });
  }

  function bindSaveDialog() {
    const openSaveModal = (isNew = false, suggestedName = '') => {
      el.scriptName.value = suggestedName;
      el.saveModal.hidden = false;
      el.scriptName.focus();
      document.body.style.overflow = 'hidden';
      validateSaveName();
      resetSaveStatus();
    };

    const closeSaveModal = () => {
      el.saveModal.hidden = true;
      document.body.style.overflow = '';
      el.fileBtn.focus();
      resetSaveStatus();
    };

    const resetSaveStatus = () => {
      el.saveStatus.hidden = true;
      el.saveStatus.className = 'save-status';
      el.saveForm.classList.remove('saving');
      el.saveConfirmBtn.classList.remove('saving');
      el.btnSpinner.hidden = true;
      el.saveConfirmBtn.disabled = false;
    };

    const setSaveStatus = (type, message) => {
      el.saveStatus.hidden = false;
      el.saveStatus.className = `save-status ${type}`;
      el.saveStatus.querySelector('.status-message').textContent = message;
    };

    const setSavingState = (saving) => {
      el.saveForm.classList.toggle('saving', saving);
      el.saveConfirmBtn.classList.toggle('saving', saving);
      el.saveConfirmBtn.disabled = saving;
      el.btnSpinner.hidden = !saving;
      el.saveCancelBtn.disabled = saving;

      if (saving) {
        setSaveStatus('loading', 'Saving script...');
      }
    };

    // Save form validation
    const validateSaveName = () => {
      const name = el.scriptName.value.trim();
      const isValid = name && name.length <= 100;
      el.saveConfirmBtn.disabled = !isValid;

      // Clear error status when user types
      if (el.saveStatus.classList.contains('error')) {
        resetSaveStatus();
      }

      return isValid;
    };

    el.scriptName.addEventListener('input', validateSaveName);

    // Enhanced save form submission with proper feedback
    el.saveForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const name = el.scriptName.value.trim();

      if (!validateSaveName()) return;

      setSavingState(true);

      try {
        const content = el.fdoInput.value || '';
        const script = await saveScript(name, content, currentScript?.id);

        if (script) {
          // Success state
          setSaveStatus('success', `Saved "${name}" successfully!`);

          // Update app state
          currentScript = script;
          originalContent = content;
          hasUnsavedChanges = false;
          updateUIForSavedState();
          setStatusOperation(`Saved "${name}" at ${new Date().toLocaleTimeString()}`);
          log(`Saved "${name}" (${content.length} chars)`);

          // Close modal after short delay to show success
          setTimeout(() => {
            closeSaveModal();
            showToast(`Saved "${name}"`, 'success');
          }, 1200);
        } else {
          throw new Error('Save operation returned no result');
        }
      } catch (error) {
        setSavingState(false);

        // Determine error message based on error type
        let errorMessage = 'Failed to save script';

        if (error.status === 409) {
          errorMessage = 'A script with that name already exists';
        } else if (error.status === 400) {
          errorMessage = 'Invalid script name or content';
        } else if (error.status === 413) {
          errorMessage = 'Script is too large to save';
        } else if (error.status >= 500) {
          errorMessage = 'Server error occurred. Please try again.';
        } else if (error.name === 'NetworkError' || !window.navigator.onLine) {
          errorMessage = 'Network connection lost. Check your connection.';
        } else if (error.message) {
          errorMessage = error.message;
        }

        setSaveStatus('error', errorMessage);

        // Re-enable form for retry
        setTimeout(() => {
          el.saveConfirmBtn.disabled = false;
          el.saveCancelBtn.disabled = false;
        }, 500);
      }
    });

    // Close handlers
    el.saveModalClose.addEventListener('click', closeSaveModal);
    el.saveCancelBtn.addEventListener('click', closeSaveModal);

    // Expose openSaveModal for use by other functions
    window.openSaveModal = openSaveModal;
  }

  function bindFileBrowser() {
    let currentScripts = [];

    const openFileBrowser = async (filter = 'all') => {
      // Validate all required elements
      const requiredElements = ['fileBrowserModal', 'fileList', 'fileLoadingIndicator', 'fileNoResults', 'fileSearchInput'];
      const missingElements = requiredElements.filter(name => !el[name]);

      if (missingElements.length > 0) {
        console.error('Missing required elements for file browser:', missingElements);
        showToast(`File browser initialization error: missing ${missingElements.join(', ')}`, 'error');
        return;
      }

      currentFilter = filter;
      updateFilterButtons();
      el.fileBrowserModal.hidden = false;
      await loadScripts();
      el.fileSearchInput.focus();
      document.body.style.overflow = 'hidden';
    };

    const closeFileBrowser = () => {
      el.fileBrowserModal.hidden = true;
      document.body.style.overflow = '';
      el.fileBtn.focus();
    };

    const updateFilterButtons = () => {
      [el.showAllFiles, el.showFavorites, el.showRecent].forEach(btn => {
        btn.classList.toggle('active', btn.dataset.filter === currentFilter);
      });
    };

    const loadScripts = async (searchTerm = '') => {
      if (!el.fileList) {
        console.error('fileList element not found in loadScripts');
        showToast('File browser not properly initialized', 'error');
        return;
      }

      el.fileLoadingIndicator.hidden = false;
      el.fileNoResults.hidden = true;
      el.fileList.innerHTML = '';

      try {
        let scripts;
        if (currentFilter === 'recent') {
          scripts = await fetchRecentScripts();
        } else {
          const favoritesOnly = currentFilter === 'favorites';
          scripts = await fetchScripts(searchTerm, favoritesOnly);
        }

        currentScripts = scripts;
        renderFileList(scripts);
      } catch (error) {
        console.error('Error loading scripts:', error);
        showToast(`Failed to load scripts: ${error.message}`, 'error');
        currentScripts = [];
      } finally {
        el.fileLoadingIndicator.hidden = true;
      }
    };

    const renderFileList = (scripts) => {
      if (!el.fileList) {
        console.error('fileList element not found');
        return;
      }

      el.fileList.innerHTML = '';

      if (scripts.length === 0) {
        el.fileNoResults.hidden = false;
        return;
      }

      el.fileNoResults.hidden = true;

      scripts.forEach(script => {
        const item = createFileItem(script);
        el.fileList.appendChild(item);
      });
    };

    const createFileItem = (script) => {
      const item = document.createElement('div');
      item.className = 'file-row';
      item.dataset.scriptId = script.id;

      const icon = script.is_favorite ? '★' : '';
      const lastModified = new Date(script.updated_at).toLocaleTimeString([], {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
      const sizeInBytes = Math.ceil((script.content_length || 0) * 1.5); // Rough char to byte conversion

      item.innerHTML = `
        <div class="file-name-col">
          <span class="file-favorite">${icon}</span>
          <span class="file-name" title="${script.name}">${script.name}</span>
        </div>
        <div class="file-size-col">${sizeInBytes.toLocaleString()}B</div>
        <div class="file-date-col">${lastModified}</div>
        <div class="file-actions-col">
          <button class="file-action-btn favorite-btn ${script.is_favorite ? 'active' : ''}"
                  data-action="favorite" title="Toggle favorite">★</button>
          <button class="file-action-btn delete-btn" data-action="delete" title="Delete script">×</button>
        </div>
      `;

      // Single click handler for both loading scripts and action buttons
      item.addEventListener('click', async (e) => {
        // Handle action buttons first
        if (e.target.dataset.action === 'favorite') {
          e.stopPropagation();
          await toggleScriptFavorite(script.id);
          loadScripts(el.fileSearchInput.value); // Refresh list
          return;
        } else if (e.target.dataset.action === 'delete') {
          e.stopPropagation();
          await confirmDeleteScript(script.id, script.name);
          return;
        }

        // If not clicking action buttons, load the script
        if (!e.target.dataset.action) {
          try {
            const fullScript = await fetchScript(script.id);
            if (fullScript) {
              await loadScriptIntoEditor(fullScript);
              closeFileBrowser();
            }
          } catch (error) {
            showToast('Failed to load script', 'error');
          }
        }
      });

      return item;
    };

    // Search functionality
    el.fileSearchInput.addEventListener('input', (e) => {
      const query = e.target.value.trim();
      el.fileSearchClear.hidden = !query;

      if (searchDebounceTimer) {
        clearTimeout(searchDebounceTimer);
      }

      searchDebounceTimer = setTimeout(() => {
        loadScripts(query);
      }, 300);
    });

    el.fileSearchClear.addEventListener('click', () => {
      el.fileSearchInput.value = '';
      el.fileSearchClear.hidden = true;
      loadScripts('');
    });

    // Filter buttons
    el.showAllFiles.addEventListener('click', () => {
      currentFilter = 'all';
      updateFilterButtons();
      loadScripts(el.fileSearchInput.value);
    });

    el.showFavorites.addEventListener('click', () => {
      currentFilter = 'favorites';
      updateFilterButtons();
      loadScripts(el.fileSearchInput.value);
    });

    el.showRecent.addEventListener('click', () => {
      currentFilter = 'recent';
      updateFilterButtons();
      loadScripts('');
    });

    // Close handlers
    el.fileBrowserModalClose.addEventListener('click', closeFileBrowser);

    // Expose openFileBrowser for use by other functions
    window.openFileBrowser = openFileBrowser;
  }

  function bindConfirmDialog() {
    let currentResolve = null;

    const showConfirmDialog = (message, title = 'Confirm Action') => {
      return new Promise((resolve) => {
        currentResolve = resolve;
        el.confirmMessage.textContent = message;
        document.querySelector('#confirmModalTitle').textContent = title;
        el.confirmModal.hidden = false;
        document.body.style.overflow = 'hidden';
        el.confirmOkBtn.focus();
      });
    };

    const closeConfirmDialog = (result = false) => {
      el.confirmModal.hidden = true;
      document.body.style.overflow = '';
      if (currentResolve) {
        currentResolve(result);
        currentResolve = null;
      }
    };

    el.confirmOkBtn.addEventListener('click', () => closeConfirmDialog(true));
    el.confirmCancelBtn.addEventListener('click', () => closeConfirmDialog(false));
    el.confirmModalClose.addEventListener('click', () => closeConfirmDialog(false));

    // Expose showConfirmDialog for use by other functions
    window.showConfirmDialog = showConfirmDialog;
  }

  function setupUnsavedChangesTracking() {
    // Track changes to the editor
    el.fdoInput.addEventListener('input', () => {
      const currentContent = el.fdoInput.value || '';

      // If this was a read-only example and user is editing, transition to editable
      if (currentScript && currentScript.is_readonly && currentContent !== originalContent) {
        currentScript.is_readonly = false;
        currentScript.is_example = false;
        currentScript.name = `${currentScript.name} (Copy)`;
      }

      hasUnsavedChanges = currentContent !== originalContent;
      updateUIForUnsavedChanges();
      updateStatusBar();
      updateValidationStatus();
    });

    // Track changes to the hex input for decompile validation and status bar
    el.hexInput.addEventListener('input', () => {
      updateStatusBar(); // Update byte count in status bar
      updateValidationStatus(); // This now handles both compile and decompile validation
    });

    // Warn before leaving if there are unsaved changes
    window.addEventListener('beforeunload', (e) => {
      if (hasUnsavedChanges) {
        e.preventDefault();
        e.returnValue = 'You have unsaved changes. Are you sure you want to leave?';
        return e.returnValue;
      }
    });
  }

  function setupKeyboardShortcuts() {
    document.addEventListener('keydown', async (e) => {
      if (e.ctrlKey || e.metaKey) {
        switch (e.key.toLowerCase()) {
          case 's':
            e.preventDefault();
            if (e.shiftKey) {
              handleSaveAs();
            } else {
              handleSave();
            }
            break;
          case 'o':
            e.preventDefault();
            handleOpen();
            break;
          case 'n':
            e.preventDefault();
            handleNew();
            break;
        }
      }
    });
  }

  // File operation handlers
  async function handleSave() {
    if (currentScript) {
      // Update existing script
      try {
        const content = el.fdoInput.value || '';
        const updatedScript = await saveScript(currentScript.name, content, currentScript.id);
        if (updatedScript) {
          currentScript = updatedScript;
          originalContent = content;
          hasUnsavedChanges = false;
          updateUIForSavedState();
          setStatusOperation(`Saved "${currentScript.name}" at ${new Date().toLocaleTimeString()}`);
          log(`Auto-saved "${currentScript.name}" (${content.length} chars)`);
          showToast(`Saved "${currentScript.name}"`, 'success');
        }
      } catch (error) {
        showToast('Failed to save script', 'error');
      }
    } else {
      // No current script, show save as dialog
      handleSaveAs();
    }
  }

  async function handleSaveAs() {
    const suggestedName = currentScript?.name || 'Untitled Script';
    window.openSaveModal(true, suggestedName);
  }

  async function handleOpen() {
    if (hasUnsavedChanges) {
      const shouldContinue = await window.showConfirmDialog(
        'You have unsaved changes that will be lost. Continue?',
        'Unsaved Changes'
      );
      if (!shouldContinue) return;
    }

    window.openFileBrowser('all');
  }

  async function handleRecentFiles() {
    window.openFileBrowser('recent');
  }

  async function handleNew() {
    if (hasUnsavedChanges) {
      const shouldContinue = await window.showConfirmDialog(
        'You have unsaved changes that will be lost. Continue?',
        'Unsaved Changes'
      );
      if (!shouldContinue) return;
    }

    currentScript = null;
    el.fdoInput.value = '';
    originalContent = '';
    hasUnsavedChanges = false;
    updateUIForNewFile();
    setStatusOperation(`New file created at ${new Date().toLocaleTimeString()}`);
    log('New file created');
    el.fdoInput.focus();
    showToast('New file created', 'success');
  }

  async function loadScriptIntoEditor(script) {
    currentScript = script;
    el.fdoInput.value = script.content || '';
    originalContent = script.content || '';
    hasUnsavedChanges = false;
    updateUIForLoadedScript();
    setStatusOperation(`Loaded "${script.name}" at ${new Date().toLocaleTimeString()}`);
    log(`Loaded "${script.name}" (${(script.content || '').length} chars)`);
    updateValidationStatus();
    el.fdoInput.focus();
    el.fdoInput.setSelectionRange(0, 0); // Set cursor to start
    el.fdoInput.scrollTop = 0; // Scroll to top
    showToast(`Loaded "${script.name}"`, 'success');
  }

  async function confirmDeleteScript(scriptId, scriptName) {
    const shouldDelete = await window.showConfirmDialog(
      `Are you sure you want to delete "${scriptName}"? This action cannot be undone.`,
      'Delete Script'
    );

    if (shouldDelete) {
      try {
        const success = await deleteScript(scriptId);
        if (success) {
          log(`Deleted "${scriptName}"`);
          showToast(`Deleted "${scriptName}"`, 'success');
          // Refresh the file list
          if (el.fileBrowserModal && !el.fileBrowserModal.hidden) {
            window.openFileBrowser(currentFilter);
          }
        }
      } catch (error) {
        showToast('Failed to delete script', 'error');
      }
    }
  }

  async function toggleScriptFavorite(scriptId) {
    try {
      await toggleFavorite(scriptId);
    } catch (error) {
      showToast('Failed to update favorite status', 'error');
    }
  }

  // API functions
  async function fetchScripts(search = '', favoritesOnly = false) {
    const params = new URLSearchParams();
    if (search) params.set('search', search);
    if (favoritesOnly) params.set('favorites_only', 'true');

    const response = await fetch(`/files?${params}`);
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`HTTP ${response.status}: ${errorText}`);
    }
    return response.json();
  }

  async function fetchRecentScripts(limit = 10) {
    const response = await fetch(`/files/recent?limit=${limit}`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  }

  async function fetchScript(scriptId) {
    const response = await fetch(`/files/${scriptId}`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  }

  async function saveScript(name, content, scriptId = null) {
    const url = scriptId ? `/files/${scriptId}` : '/files';
    const method = scriptId ? 'PUT' : 'POST';

    const response = await fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, content, script_id: scriptId })
    });

    if (!response.ok) {
      const error = new Error(`HTTP ${response.status}`);
      error.status = response.status;
      throw error;
    }

    return response.json();
  }

  async function deleteScript(scriptId) {
    const response = await fetch(`/files/${scriptId}`, { method: 'DELETE' });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const result = await response.json();
    return result.success;
  }

  async function toggleFavorite(scriptId) {
    const response = await fetch(`/files/${scriptId}/favorite`, { method: 'PUT' });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  }

  // Document Bar Management
  function setupDocumentBar() {
    if (!el.documentBar) return;


    // Handle close button
    el.docCloseBtn.addEventListener('click', () => {
      handleNew();
    });

  }

  // UI update functions
  function updateUIForSavedState() {
    document.title = currentScript ? `AtomForge - ${currentScript.name}` : 'AtomForge';
    updateStatusBar();
  }

  function updateUIForUnsavedChanges() {
    const title = currentScript ? currentScript.name : 'Untitled';
    document.title = hasUnsavedChanges ? `AtomForge - ${title}*` : `AtomForge - ${title}`;
  }

  function updateUIForLoadedScript() {
    updateUIForSavedState();
  }

  function updateUIForNewFile() {
    document.title = 'AtomForge';
    updateStatusBar();
  }

  // Status Bar Management
  function updateStatusBar() {
    if (!el.statusStats) return;

    if (st.mode === 'compile') {
      // Compile mode: show lines and chars
      const content = el.fdoInput.value || '';
      const lines = content ? content.split('\n').length : 0;
      const chars = content.length;

      // Show editor statistics with save status
      let saveIndicator = '';
      if (hasUnsavedChanges) {
        saveIndicator = ' • modified';
      }

      el.statusStats.textContent = `${lines} lines, ${chars.toLocaleString()} chars${saveIndicator}`;
    } else if (st.mode === 'decompile') {
      // Decompile mode: show byte count based on hex input
      const hexInput = el.hexInput.value || '';
      const cleanHex = hexInput.replace(/[^0-9A-Fa-f]/g, '');
      const isValidHex = cleanHex.length > 0 && cleanHex.length % 2 === 0;
      const byteCount = Math.floor(cleanHex.length / 2);

      if (isValidHex) {
        el.statusStats.textContent = `Decoded: ${byteCount.toLocaleString()} bytes`;
      } else if (cleanHex.length > 0) {
        el.statusStats.textContent = `Input: ${byteCount.toLocaleString()} bytes`;
      } else {
        el.statusStats.textContent = `Decoded: 0 bytes`;
      }
    }

    updateStatusFilename();
  }

  function setStatusOperation(message, duration = 3000) {
    if (!el.statusOperation) return;

    el.statusOperation.textContent = message;

    // Clear after duration
    if (duration > 0) {
      setTimeout(() => {
        updateStatusFilename(); // Restore filename display
      }, duration);
    }
  }

  function updateStatusFilename() {
    if (!el.statusOperation) return;

    if (currentScript) {
      el.statusOperation.textContent = `Loaded: ${currentScript.name}`;
    } else {
      el.statusOperation.textContent = 'Untitled';
    }
  }

  // Compilation Status Checking
  async function checkCompilationStatus(source) {
    try {
      const response = await fetch('/compile', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source })
      });

      return response.ok;
    } catch (error) {
      return false;
    }
  }

  async function checkDecompilationStatus(input) {
    try {
      // For hex input, try to convert it to base64
      let binaryData;
      if (typeof input === 'string' && input.trim()) {
        // Clean up hex input (remove spaces, ensure even length)
        const hexClean = input.replace(/\s+/g, '').replace(/^0x/i, '');
        if (hexClean.length % 2 !== 0 || !/^[0-9a-fA-F]*$/.test(hexClean)) {
          return false; // Invalid hex format
        }

        // Convert hex to base64
        const bytes = [];
        for (let i = 0; i < hexClean.length; i += 2) {
          bytes.push(parseInt(hexClean.substr(i, 2), 16));
        }
        binaryData = btoa(String.fromCharCode.apply(null, bytes));
      } else {
        return false; // No input
      }

      const response = await fetch('/decompile', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          binary_data: binaryData,
          pre_normalize: false
        })
      });

      return response.ok;
    } catch (error) {
      return false;
    }
  }

  function updateValidationStatus() {
    // Check validation status for both compile and decompile modes
    clearTimeout(compileCheckTimer);
    compileCheckTimer = setTimeout(async () => {
      if (st.mode === 'compile') {
        const source = el.fdoInput.value || '';
        if (!source.trim()) {
          // Empty source - neutral state
          el.statusMode.className = 'status-mode';
          el.statusMode.textContent = 'Compile';
          return;
        }

        const isValid = await checkCompilationStatus(source);
        if (isValid) {
          el.statusMode.className = 'status-mode compile-valid';
          el.statusMode.textContent = 'Compile';
        } else {
          el.statusMode.className = 'status-mode compile-invalid';
          el.statusMode.textContent = 'Compile';
        }
      } else if (st.mode === 'decompile') {
        const hexInput = el.hexInput.value || '';
        if (!hexInput.trim()) {
          // Empty input - neutral state
          el.statusMode.className = 'status-mode';
          el.statusMode.textContent = 'Decompile';
          return;
        }

        // Check for hex format validity (uneven pairs)
        const cleanHex = hexInput.replace(/[^0-9A-Fa-f]/g, '');
        const hasUnevenPairs = cleanHex.length > 0 && cleanHex.length % 2 !== 0;

        if (hasUnevenPairs) {
          // Invalid hex format - show format error
          el.statusMode.className = 'status-mode decompile-invalid';
          el.statusMode.textContent = 'Decompile (invalid hex)';
          return;
        }

        // Valid hex format - check if it will decompile successfully
        const isValid = await checkDecompilationStatus(hexInput);
        if (isValid) {
          el.statusMode.className = 'status-mode decompile-valid';
          el.statusMode.textContent = 'Decompile';
        } else {
          el.statusMode.className = 'status-mode decompile-invalid';
          el.statusMode.textContent = 'Decompile';
        }
      }
    }, 1000); // Check 1 second after user stops typing
  }

  // Toast notification system
  function showToast(message, type = 'info', duration = 3000) {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
      <div class="toast-message">${message}</div>
      <button class="toast-close" type="button" aria-label="Close notification">×</button>
    `;

    // Add to container
    el.toastContainer.appendChild(toast);

    // Close button handler
    const closeBtn = toast.querySelector('.toast-close');
    closeBtn.addEventListener('click', () => removeToast(toast));

    // Auto-remove after duration
    setTimeout(() => removeToast(toast), duration);

    // Return toast for manual control if needed
    return toast;
  }

  function removeToast(toast) {
    if (!toast || !toast.parentNode) return;

    toast.classList.add('removing');
    setTimeout(() => {
      if (toast.parentNode) {
        toast.parentNode.removeChild(toast);
      }
    }, 300);
  }


  // init
  window.addEventListener('hashchange', ()=>{
    const h = location.hash.replace('#','');
    if (h==='compile'||h==='decompile') setMode(h);
  });

  window.addEventListener('DOMContentLoaded', init);
  return { init };
})();