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
    jsonlSpinner: qs('#jsonlSpinner'),
    hexInput: qs('#hexInput'),
    hexDecoded: qs('#hexDecoded'),
    extractFdoBtn: qs('#extractFdoBtn'),
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
  };

  let currentBinary = null;   // Uint8Array from file OR hex
  let compiledBuffer = null;  // ArrayBuffer
  let decompiledText = '';
  let isJsonlFileLoaded = false; // Track if JSONL file is loaded

  // ASCII atom support
  let asciiAtoms = [];
  let asciiSupportEnabled = false;

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
    setupBottomResize();
    setupASCIISupport();
    setupP3Extraction();
    // Ensure hex input is enabled by default since it's now the default view
    el.hexInput.removeAttribute('disabled');
    setMode(st.mode, {pushHash:false});
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

    // Check if we have a JSONL file loaded and we're in decompile mode
    if (st.mode === 'decompile' && isJsonlFileLoaded && window.currentJsonlContent) {
      return processJsonlFile();
    }

    return decompile();
  }

  // ---------- Compile ----------
  async function compile() {
    const source = (el.fdoInput.value || '').trim();
    if (!source) return log('Enter FDO source to compile.', 'error');
    setBusy(true, 'Compiling…');

    try {
      const res = await fetch('/compile', {
        method: 'POST', headers: {'Content-Type':'application/json'},
        body: JSON.stringify({ source })
      });
      if (!res.ok) {
        const e = await safeJson(res);
        throw new Error(e.error || `HTTP ${res.status}`);
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
      log(`Compilation failed: ${err.message}`, 'error');
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
        throw new Error(e.error || `HTTP ${res.status}`);
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
      log(`Decompilation failed: ${err.message}`, 'error');
      reveal('status');
      modeOutputs.decompile.activeTab = 'status';
    } finally { setBusy(false); }
  }

  function getBinary() {
    // Check if hex view is active (not hidden)
    if (!el.hexInputView.hidden) {
      const raw = (el.hexInput.value || '').trim();
      if (!raw) { log('Paste hex data or choose a file.', 'error'); return null; }
      const clean = raw.replace(/[^0-9A-Fa-f]/g, '');
      if (clean.length % 2 !== 0) { log('Hex length must be even.', 'error'); return null; }
      const bytes = new Uint8Array(clean.length/2);
      for (let i=0;i<clean.length;i+=2) bytes[i/2] = parseInt(clean.substr(i,2),16);
      currentBinary = bytes;
      el.hexDecoded.textContent = bytes.length.toLocaleString();
      return bytes;
    }
    if (!currentBinary) { showToast('Choose a file or paste hex.', 'error'); return null; }
    return currentBinary;
  }

  function bindDecompileInputs() {
    // Toggle File/Hex
    el.toggleBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        el.toggleBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        const showHex = btn.dataset.input === 'hex';

        el.fileView.hidden = showHex;
        el.hexInputView.hidden = !showHex;

        if (showHex) {
          el.hexInput.removeAttribute('disabled');
          el.hexInput.focus();
          refreshHexDecoded();
        } else {
          el.binaryFile.focus();
        }
      });
    });

    // Single-click opens the file picker
    el.binaryDrop.addEventListener('click', (e) => { e.preventDefault(); el.binaryFile.click(); });

    // File -> bytes
    el.binaryFile.addEventListener('change', (e) => {
      const f = e.target.files?.[0]; if (!f) return;

      // Check if this is a JSONL file
      const isJsonl = f.name.toLowerCase().endsWith('.jsonl');

      if (isJsonl) {
        // Handle JSONL file
        const reader = new FileReader();
        reader.onload = ev => {
          const jsonlContent = ev.target.result;
          el.fileDecoded.textContent = `${formatBytes(jsonlContent.length)} JSONL`;
          el.openAsHexBtn.hidden = true;
          isJsonlFileLoaded = true;

          // Store JSONL content for processing
          window.currentJsonlContent = jsonlContent;
          window.currentJsonlFilename = f.name;

          // Visually indicate loaded state on the drop zone
          el.binaryDrop.classList.add('loaded');
          const msgNode = el.binaryDrop.querySelector('span');
          if (msgNode) {
            msgNode.textContent = `${f.name} — ${formatBytes(jsonlContent.length)} JSONL (click to change)`;
          }
          showToast(`Loaded JSONL file: ${f.name}`, 'success');
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

          // Clear any stored JSONL content
          window.currentJsonlContent = null;
          window.currentJsonlFilename = null;

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

    async function loadExamples() {
      try {
        const res = await fetch('/examples');
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const list = await res.json();
        el.examplesMenu.innerHTML = '';
        (list || []).forEach(ex => {
          const b = document.createElement('button');
          b.type = 'button';
          b.setAttribute('role','menuitem');
          b.textContent = ex.label || ex.name || 'Example';
          b.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            el.fdoInput.value = ex.text || ex.source || '';
            el.examplesMenu.hidden = true;
            el.examplesBtn.setAttribute('aria-expanded', 'false');
            setMode('compile');
            el.fdoInput.focus();
            showToast(`Loaded example: ${b.textContent}`, 'success');
          });
          el.examplesMenu.appendChild(b);
        });
      } catch (err) {
        showToast('Failed to load examples', 'error');
      }
    }

    el.examplesBtn.addEventListener('click', async (e) => {
      e.preventDefault();
      e.stopPropagation();
      const isHidden = el.examplesMenu.hasAttribute('hidden') || el.examplesMenu.hidden;
      if (isHidden) await loadExamples();
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

  function setBusy(on, label){
    el.runBtn.disabled = on;
    el.runBtn.classList.toggle('loading', on);
    if(on) log(label||'Working…');
  }

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
  async function setupASCIISupport() {
    try {
      const response = await fetch('/ascii-atoms');
      if (response.ok) {
        const data = await response.json();
        if (data.ascii_support) {
          asciiAtoms = data.atoms;
          asciiSupportEnabled = true;
          setupASCIIInputEnhancements();
          console.log(`ASCII support enabled for ${data.count} atoms:`, asciiAtoms.map(a => a.name));
        }
      }
    } catch (error) {
      console.log('ASCII atom support not available:', error.message);
    }
  }

  function setupASCIIInputEnhancements() {
    if (!asciiSupportEnabled) return;

    // Add ASCII input helpers to the compile input
    addASCIIInputHelper(el.fdoInput);
  }

  function addASCIIInputHelper(textarea) {
    // Add event listeners for intelligent ASCII suggestions
    textarea.addEventListener('input', handleASCIIInput);
    textarea.addEventListener('keydown', handleASCIIKeydown);
  }

  function handleASCIIInput(event) {
    const textarea = event.target;
    const cursorPos = textarea.selectionStart;
    const textBeforeCursor = textarea.value.substring(0, cursorPos);

    // Check if we're typing an ASCII-supported atom
    const currentLine = textBeforeCursor.split('\n').pop();

    for (const atom of asciiAtoms) {
      if (currentLine.trim().startsWith(atom.name)) {
        // Show ASCII input suggestion (could add visual indicator here)
        break;
      }
    }
  }

  function handleASCIIKeydown(event) {
    // Could add special key handling for ASCII input assistance
    // For example, auto-complete or formatting helpers
  }

  function isASCIIAtom(atomName) {
    return asciiAtoms.some(atom => atom.name === atomName);
  }

  function getASCIIAtomInfo(atomName) {
    return asciiAtoms.find(atom => atom.name === atomName);
  }

  // P3 Extraction Support
  function setupP3Extraction() {
    if (!el.extractFdoBtn) return;

    // Show/hide extract button based on hex input content
    el.hexInput.addEventListener('input', updateExtractButtonVisibility);
    el.extractFdoBtn.addEventListener('click', extractFDOFromP3);

    updateExtractButtonVisibility();
  }


  async function processJsonlFile() {
    if (!window.currentJsonlContent) {
      showToast('No JSONL file loaded', 'error');
      return;
    }

    // Show spinner
    el.jsonlSpinner.hidden = false;
    setBusy(true, 'Processing JSONL...');

    log(`Processing JSONL file: ${window.currentJsonlFilename}`);

    try {
      // Process JSONL content line by line
      const lines = window.currentJsonlContent.split('\n').filter(line => line.trim());
      let totalLines = lines.length;
      let processedLines = 0;
      let validFrames = 0;
      let serverToClientFrames = 0;
      let fdoExtractionAttempts = 0;
      let fdoExtractionSuccesses = 0;
      let concatenatedFdoHex = '';

      log(`Found ${totalLines} lines to process`);

      // Process in batches to avoid blocking UI
      const batchSize = 10;
      for (let i = 0; i < lines.length; i += batchSize) {
        const batch = lines.slice(i, i + batchSize);

        for (const line of batch) {
          try {
            const frame = JSON.parse(line);
            processedLines++;

            // Check if this is a server-to-client frame
            if (frame.direction === 'server-to-client' || frame.direction === 'ServerToClient' || frame.dir === 'S->C') {
              serverToClientFrames++;

              // Check if frame has data and is eligible for FDO extraction
              let hexData = null;
              if (frame.data && (frame.data.hex || frame.data.payload)) {
                hexData = frame.data.hex || frame.data.payload;
              } else if (frame.fullHex) {
                hexData = frame.fullHex;
              }

              if (hexData) {
                fdoExtractionAttempts++;

                // Try to extract FDO from this frame's hex data
                try {
                  const extractResult = await extractFDOFromHex(hexData);
                  if (extractResult.success && extractResult.fdo_hex) {
                    fdoExtractionSuccesses++;
                    concatenatedFdoHex += extractResult.fdo_hex;
                    let logMsg = `✓ Frame ${processedLines}: Extracted ${extractResult.total_fdo_bytes} FDO bytes`;
                    if (extractResult.skipped_non_fdo_packets > 0) {
                      logMsg += ` (skipped ${extractResult.skipped_non_fdo_packets} non-FDO)`;
                    }
                    log(logMsg);
                  } else if (extractResult.skipped_non_fdo_packets > 0) {
                    // Even if no FDO was found, report non-FDO packets that were skipped
                    log(`⌐ Frame ${processedLines}: Skipped ${extractResult.skipped_non_fdo_packets} non-FDO packets`);
                  }
                } catch (extractError) {
                  // Silently continue - many frames won't contain FDO data
                }
              }
              validFrames++;
            }

          } catch (parseError) {
            // Skip invalid JSON lines
            processedLines++;
          }
        }

        // Allow UI to update between batches - reduced frequency for cleaner experience
        if (i % 50 === 0) {
          await new Promise(resolve => setTimeout(resolve, 5));
        }
      }

      log(`✓ JSONL processing complete:`);
      log(`  Total lines: ${totalLines}`);
      log(`  Server-to-client frames: ${serverToClientFrames}`);
      log(`  FDO extraction attempts: ${fdoExtractionAttempts}`);
      log(`  Successful extractions: ${fdoExtractionSuccesses}`);

      if (concatenatedFdoHex.length > 0) {
        // Convert concatenated hex to binary for decompilation
        const cleanHex = concatenatedFdoHex.replace(/[^0-9A-Fa-f]/g, '');
        const fdoBytes = new Uint8Array(cleanHex.length / 2);
        for (let i = 0; i < cleanHex.length; i += 2) {
          fdoBytes[i / 2] = parseInt(cleanHex.substr(i, 2), 16);
        }

        // Set as current binary and update UI
        currentBinary = fdoBytes;

        // Populate hex output for reference
        el.compileSize.textContent = formatBytes(fdoBytes.length);
        el.hexOutViewer.textContent = hexdump(fdoBytes);

        // Attempt decompilation of concatenated FDO data
        log(`Attempting decompilation of ${formatBytes(fdoBytes.length)} concatenated FDO data...`);

        try {
          const base64 = btoa(String.fromCharCode.apply(null, fdoBytes));
          const decompileRes = await fetch('/decompile', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ binary_data: base64 })
          });

          if (decompileRes.ok) {
            const decompileData = await decompileRes.json();
            if (decompileData.success) {
              decompiledText = decompileData.source_code || '';
              el.decompileSize.textContent = `${(decompileData.output_size || decompiledText.length).toLocaleString()} chars`;
              el.sourceView.textContent = decompiledText;

              // Save decompile outputs to mode state
              modeOutputs.decompile.hexContent = el.hexOutViewer.textContent;
              modeOutputs.decompile.hexSize = el.compileSize.textContent;
              modeOutputs.decompile.sourceContent = el.sourceView.textContent;
              modeOutputs.decompile.sourceSize = el.decompileSize.textContent;
              modeOutputs.decompile.text = decompiledText;

              reveal('source');
              modeOutputs.decompile.activeTab = 'source';
              log(`✓ Decompilation successful - ${el.decompileSize.textContent}`);
              showToast(`JSONL processed: ${fdoExtractionSuccesses} FDO extractions, decompiled to ${el.decompileSize.textContent}`, 'success');
            } else {
              log(`✗ Decompilation failed: ${decompileData.error}`);
              showToast('FDO data extracted but decompilation failed', 'warning');
            }
          }
        } catch (decompileError) {
          log(`✗ Decompilation error: ${decompileError.message}`);
          showToast('FDO data extracted but decompilation failed', 'warning');
        }
      } else {
        log('No FDO data found in JSONL file');
        showToast(`Processed ${totalLines} lines, but no FDO data was found`, 'warning');
      }

    } catch (error) {
      log(`✗ JSONL processing error: ${error.message}`, 'error');
      showToast(`JSONL processing failed: ${error.message}`, 'error');
      reveal('status');
      modeOutputs.decompile.activeTab = 'status';
    } finally {
      // Hide spinner and restore UI
      el.jsonlSpinner.hidden = true;
      setBusy(false);
    }
  }

  // Helper function for FDO extraction from hex data
  async function extractFDOFromHex(hexData) {
    const response = await fetch('/extract-fdo', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ hex_data: hexData })
    });

    const result = await response.json();
    return result;
  }

  function refreshHexDecoded() {
    const clean = (el.hexInput.value||'').replace(/[^0-9A-Fa-f]/g, '');
    el.hexDecoded.textContent = (clean.length/2|0).toLocaleString();
  }

  function updateExtractButtonVisibility() {
    const hexContent = el.hexInput.value.trim();
    const hasContent = hexContent.length > 0;

    if (hasContent) {
      el.extractFdoBtn.hidden = false;
    } else {
      el.extractFdoBtn.hidden = true;
    }
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
        log(`✓ FDO extracted successfully`);
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

  // init
  window.addEventListener('hashchange', ()=>{
    const h = location.hash.replace('#','');
    if (h==='compile'||h==='decompile') setMode(h);
  });

  window.addEventListener('DOMContentLoaded', init);
  return { init };
})();