// AtomForge Web Interface - Unified FDO Compiler & Decompiler
class AtomForge {
    constructor() {
        this.mode = localStorage.getItem('atomforge:mode') || 'compile'; // 'compile' or 'decompile'
        this.compileEndpoint = '/compile';
        this.decompileEndpoint = '/decompile';
        this.init();
    }

    init() {
        this.bindElements();
        this.bindEvents();
        this.loadExamples();
        this.updateCharCount();
        this.updateMode();
    }

    bindElements() {
        // Mode switching
        this.modeBtns = document.querySelectorAll('.mode-btn');

        // Input elements - compile mode
        this.fdoInput = document.getElementById('fdoInput');
        this.charCount = document.getElementById('charCount');
        this.clearBtn = document.getElementById('clearBtn');
        this.fileInput = document.getElementById('fileInput');
        this.dropZone = document.getElementById('dropZone');
        this.inputSection = document.querySelector('.input-section');

        // Input elements - decompile mode
        this.decompileSection = document.getElementById('decompileSection');
        this.binaryDropZone = document.getElementById('binaryDropZone');
        this.binaryFileInput = document.getElementById('binaryFileInput');
        this.binaryFilePreview = document.getElementById('binaryFilePreview');
        this.binaryFileName = document.getElementById('binaryFileName');
        this.binaryFileSize = document.getElementById('binaryFileSize');
        this.binaryHexPreview = document.getElementById('binaryHexPreview');
        this.binarySize = document.getElementById('binarySize');
        this.clearBinaryBtn = document.getElementById('clearBinaryBtn');

        // Hex input elements
        this.binaryTabs = document.querySelectorAll('.binary-tab');
        this.hexInput = document.getElementById('hexInput');
        this.hexFormatBtn = document.getElementById('hexFormatBtn');
        this.hexDecodedSize = document.getElementById('hexDecodedSize');
        this.fileTab = document.getElementById('fileTab');
        this.hexTab = document.getElementById('hexTab');

        // Examples
        this.examplesBtn = document.getElementById('examplesBtn');
        this.examplesMenu = document.getElementById('examplesMenu');

        // Action button
        this.actionBtn = document.getElementById('actionBtn');
        this.btnIcon = document.getElementById('btnIcon');
        this.btnText = document.getElementById('btnText');

        // Status and output
        this.statusSection = document.getElementById('statusSection');
        this.statusContent = document.getElementById('statusContent');

        // Result elements
        this.compileResult = document.getElementById('compileResult');
        this.decompileResult = document.getElementById('decompileResult');
        this.compileSize = document.getElementById('compileSize');
        this.decompileSize = document.getElementById('decompileSize');
        this.compileHexPreview = document.getElementById('compileHexPreview');
        this.decompileSourceCode = document.getElementById('decompileSourceCode');
        this.downloadBtn = document.getElementById('downloadBtn');
        this.copyHexBtn = document.getElementById('copyHexBtn');
        this.downloadSourceBtn = document.getElementById('downloadSourceBtn');
        this.copySourceBtn = document.getElementById('copySourceBtn');

        // Output data storage

        // Store processed data
        this.compiledData = null;
        this.binaryData = null;
        this.decompileResultData = null;
    }

    bindEvents() {
        // Mode switching
        this.modeBtns.forEach(btn => {
            btn.addEventListener('click', (e) => {
                const mode = e.currentTarget?.dataset?.mode;
                if (mode === 'compile' || mode === 'decompile') this.switchMode(mode);
            });
        });

        // Compile mode input events
        this.fdoInput.addEventListener('input', () => this.updateCharCount());
        this.clearBtn.addEventListener('click', () => this.clearInput());
        this.fileInput.addEventListener('change', (e) => this.handleFileSelect(e));
        this.dropZone.addEventListener('click', () => this.fileInput.click());

        // Decompile mode input events
        this.binaryFileInput.addEventListener('change', (e) => this.handleBinaryFileSelect(e));
        this.binaryDropZone.addEventListener('click', () => this.binaryFileInput.click());
        this.clearBinaryBtn.addEventListener('click', () => this.clearBinaryInput());

        // Hex input events
        this.binaryTabs.forEach(tab => {
            tab.addEventListener('click', (e) => this.switchBinaryTab(e.currentTarget.dataset.tab));
        });
        this.hexInput.addEventListener('input', () => this.updateHexPreview());
        this.hexFormatBtn.addEventListener('click', () => this.formatHex());

        // Drag and drop for both modes
        this.setupDragDrop();

        // Examples
        this.examplesBtn.addEventListener('click', (e) => this.toggleExamples(e));
        document.addEventListener('click', (e) => this.closeExamples(e));
        this.examplesMenu.addEventListener('click', (e) => this.selectExample(e));

        // Simple result events
        this.downloadBtn.addEventListener('click', () => this.downloadFile());
        this.copyHexBtn.addEventListener('click', () => this.copyHex());
        this.downloadSourceBtn.addEventListener('click', () => this.downloadSource());
        this.copySourceBtn.addEventListener('click', () => this.copySource());

        // Action button
        this.actionBtn.addEventListener('click', () => this.executeAction());

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => this.handleKeyboard(e));
    }

    switchMode(newMode) {
        if (this.mode === newMode) return;

        this.mode = newMode;
        localStorage.setItem('atomforge:mode', newMode);
        this.updateMode();
        this.hideAllOutput();
        this.hideStatus();
    }

    updateMode() {
        // Update button states
        this.modeBtns.forEach(btn => {
            if (btn.dataset.mode === this.mode) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
        });

        // Show/hide appropriate sections
        if (this.mode === 'compile') {
            this.inputSection.style.display = 'block';
            this.decompileSection.style.display = 'none';
            this.examplesBtn.style.display = 'inline-flex';

            // Update action button
            this.btnIcon.innerHTML = '<polygon points="5,3 19,12 5,21"/>';
            this.btnText.textContent = 'Compile FDO (⌘⏎)';
        } else {
            this.inputSection.style.display = 'none';
            this.decompileSection.style.display = 'block';
            this.examplesBtn.style.display = 'none';

            // Update action button
            this.btnIcon.innerHTML = '<path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="7.5,4.21 12,6.81 16.5,4.21"/><polyline points="7.5,19.79 7.5,14.6 3,12"/><polyline points="21,12 16.5,14.6 16.5,19.79"/>';
            this.btnText.textContent = 'Decompile FDO (⌘⏎)';
        }

        // Defensive: collapse any open example menu when switching modes
        this.examplesMenu?.classList?.remove('show');
    }

    async executeAction() {
        if (this.mode === 'compile') {
            await this.compileFDO();
        } else {
            await this.decompileFDO();
        }
    }

    async compileFDO() {
        const source = this.fdoInput.value.trim();

        if (!source) {
            this.showStatus('error', 'Empty Input', 'Please enter FDO source code to compile');
            return;
        }

        // Show loading state
        this.actionBtn.disabled = true;
        this.actionBtn.classList.add('loading');
        this.hideAllOutput();
        this.showStatus('loading', 'Compiling...', 'Processing FDO source with native compiler');

        try {
            const response = await fetch(this.compileEndpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ source })
            });

            if (response.ok) {
                // Successful compilation
                const data = await response.arrayBuffer();
                const size = response.headers.get('X-Output-Size') || data.byteLength;

                this.compiledData = data;
                this.showCompileSuccess(parseInt(size));

            } else {
                // Compilation error
                const errorData = await response.json();
                this.showStatus('error', 'Compilation Failed',
                    errorData.error || 'Unknown compilation error occurred');
            }
        } catch (error) {
            console.error('Compilation error:', error);
            this.showStatus('error', 'Network Error',
                'Could not connect to the FDO compiler service');
        } finally {
            // Reset button state
            this.actionBtn.disabled = false;
            this.actionBtn.classList.remove('loading');
        }
    }

    async decompileFDO() {
        const binaryData = this.getBinaryData();
        if (!binaryData) {
            this.showStatus('error', 'No Binary Data', 'Please select an FDO binary file or paste hex data to decompile');
            return;
        }

        // Show loading state
        this.actionBtn.disabled = true;
        this.actionBtn.classList.add('loading');
        this.hideAllOutput();
        this.showStatus('loading', 'Decompiling...', 'Processing FDO binary with native decompiler');

        try {
            // Convert binary data to base64
            const binaryArray = new Uint8Array(binaryData);
            const base64Data = btoa(String.fromCharCode.apply(null, binaryArray));

            const response = await fetch(this.decompileEndpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ binary_data: base64Data })
            });

            if (response.ok) {
                // Successful decompilation
                const result = await response.json();

                this.decompileResultData = result.source_code;
                this.showDecompileSuccess(result.output_size);

            } else {
                // Decompilation error
                const errorData = await response.json();
                this.showStatus('error', 'Decompilation Failed',
                    errorData.error || 'Unknown decompilation error occurred');
            }
        } catch (error) {
            console.error('Decompilation error:', error);
            this.showStatus('error', 'Network Error',
                'Could not connect to the FDO decompiler service');
        } finally {
            // Reset button state
            this.actionBtn.disabled = false;
            this.actionBtn.classList.remove('loading');
        }
    }

    handleBinaryFileSelect(e) {
        const file = e.target.files[0];
        if (file) {
            this.loadBinaryFile(file);
        }
    }

    loadBinaryFile(file) {
        if (!file.name.match(/\.(fdo|str|bin)$/i)) {
            this.showStatus('error', 'Invalid File Type', 'Please select a binary file (.fdo, .str, or .bin)');
            return;
        }

        const reader = new FileReader();
        reader.onload = (e) => {
            this.binaryData = e.target.result;
            this.showBinaryPreview(file);
            this.hideAllOutput();
            this.hideStatus();
        };
        reader.onerror = () => {
            this.showStatus('error', 'File Read Error', 'Could not read the selected binary file');
        };
        reader.readAsArrayBuffer(file);
    }

    showBinaryPreview(file) {
        this.binaryFileName.textContent = file.name;
        this.binaryFileSize.textContent = this.formatBytes(file.size);
        this.binarySize.textContent = file.size.toLocaleString();

        // Generate hex preview
        const bytes = new Uint8Array(this.binaryData);
        const lines = [];
        const maxLines = 4;

        for (let i = 0; i < Math.min(bytes.length, maxLines * 16); i += 16) {
            const offset = i.toString(16).padStart(8, '0');
            const hexBytes = [];

            for (let j = 0; j < 16 && i + j < bytes.length; j++) {
                const byte = bytes[i + j];
                hexBytes.push(byte.toString(16).padStart(2, '0'));
            }

            while (hexBytes.length < 16) {
                hexBytes.push('  ');
            }

            const hexLine = hexBytes.join(' ');
            lines.push(`<div class="hex-line">
                <span class="hex-offset">${offset}</span>
                <span class="hex-bytes">${hexLine}</span>
            </div>`);
        }

        if (bytes.length > maxLines * 16) {
            lines.push('<div class="hex-line">...</div>');
        }

        this.binaryHexPreview.innerHTML = lines.join('');
        this.binaryFilePreview.style.display = 'block';
    }

    clearBinaryInput() {
        this.binaryData = null;
        this.currentBinaryData = null;
        this.binaryFilePreview.style.display = 'none';
        this.binarySize.textContent = '0';
        this.binaryFileInput.value = '';
        this.hexInput.value = '';
        this.hexDecodedSize.textContent = '0';
        this.hideAllOutput();
        this.hideStatus();
    }

    showCompileSuccess(size) {
        // Hide the status section completely
        this.hideStatus();

        // Show simple compile result
        this.showSimpleCompileResult(size);
    }

    showDecompileSuccess(size) {
        // Hide the status section completely
        this.hideStatus();

        // Show simple decompile result
        this.showSimpleDecompileResult(size);
    }

    showSimpleCompileResult(size) {
        if (this.compileSize) {
            this.compileSize.textContent = this.formatBytes(size);
        }

        // Generate hex preview for compilation
        if (this.compileHexPreview && this.compiledData) {
            this.generateBinaryPreview(this.compiledData, this.compileHexPreview);
        }

        if (this.compileResult) {
            this.compileResult.style.display = 'block';
        }
    }

    showSimpleDecompileResult(size) {
        if (this.decompileSize) {
            this.decompileSize.textContent = `${size.toLocaleString()} characters`;
        }

        // Display decompiled source code
        if (this.decompileSourceCode && this.decompileResultData) {
            this.decompileSourceCode.textContent = this.decompileResultData;
        }

        if (this.decompileResult) {
            this.decompileResult.style.display = 'block';
        }
    }

    downloadFile() {
        if (!this.compiledData) return;

        const blob = new Blob([this.compiledData], { type: 'application/octet-stream' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');

        a.href = url;
        a.download = 'compiled.fdo';
        a.style.display = 'none';

        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);

        URL.revokeObjectURL(url);
    }

    downloadSource() {
        if (!this.decompileResultData) return;

        const blob = new Blob([this.decompileResultData], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');

        a.href = url;
        a.download = 'decompiled.txt';
        a.style.display = 'none';

        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);

        URL.revokeObjectURL(url);
    }

    copyData() {
        if (this.mode === 'compile') {
            this.copyHex();
        }
    }

    copySource() {
        if (!this.decompileResultData) {
            return;
        }

        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(this.decompileResultData).then(() => {
            }).catch((err) => {
                console.warn('Clipboard API failed:', err);
                this.fallbackCopyText(this.decompileResultData);
            });
        } else {
            this.fallbackCopyText(this.decompileResultData);
        }
    }

    copyHex() {
        if (!this.compiledData) {
            return;
        }

        const bytes = new Uint8Array(this.compiledData);
        const hexString = Array.from(bytes)
            .map(byte => byte.toString(16).padStart(2, '0'))
            .join('');

        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(hexString).then(() => {
            }).catch((err) => {
                console.warn('Clipboard API failed:', err);
                this.fallbackCopyText(hexString);
            });
        } else {
            this.fallbackCopyText(hexString);
        }
    }

    fallbackCopyText(text) {
        const textArea = document.createElement('textarea');
        textArea.value = text;
        textArea.style.position = 'fixed';
        textArea.style.left = '-999999px';
        textArea.style.top = '-999999px';
        textArea.style.opacity = '0';
        document.body.appendChild(textArea);

        try {
            textArea.focus();
            textArea.select();
            document.execCommand('copy');
        } catch (err) {
            console.error('Fallback copy failed:', err);
        } finally {
            document.body.removeChild(textArea);
        }
    }

    // Keep existing methods for examples, file handling, drag/drop, status, etc.
    async loadExamples() {
        try {
            const response = await fetch('/examples');
            if (response.ok) {
                const examples = await response.json();
                this.examples = {};

                examples.forEach(example => {
                    this.examples[example.id] = {
                        name: example.name,
                        source: example.source,
                        description: example.description
                    };
                });

                this.populateExamplesMenu();
                console.log(`Loaded ${examples.length} examples from golden tests`);
            } else {
                this.setupFallbackExamples();
            }
        } catch (error) {
            console.error('Error loading examples:', error);
            this.setupFallbackExamples();
        }
    }

    populateExamplesMenu() {
        if (!this.examplesMenu) {
            console.error('Examples menu element not found!');
            return;
        }

        this.examplesMenu.innerHTML = '';

        Object.keys(this.examples).forEach(key => {
            const example = this.examples[key];
            const menuItem = document.createElement('button');
            menuItem.className = 'example-item';
            menuItem.dataset.example = key;
            menuItem.textContent = example.name;
            menuItem.title = example.description || '';
            this.examplesMenu.appendChild(menuItem);
        });
    }

    setupFallbackExamples() {
        this.examples = {
            'basic': {
                name: 'Basic Example',
                source: `uni_start_stream <00x>
  man_start_object <independent, "Basic Example">
    mat_object_id <basic-001>
    mat_orientation <vcf>
    mat_position <center_center>
  man_end_object <>
uni_end_stream <>`,
                description: 'Simple fallback example'
            }
        };
        this.populateExamplesMenu();
    }

    updateCharCount() {
        const count = this.fdoInput.value.length;
        this.charCount.textContent = count.toLocaleString();
    }

    clearInput() {
        this.fdoInput.value = '';
        this.updateCharCount();
        this.hideAllOutput();
        this.hideStatus();
        this.fdoInput.focus();
    }

    setupDragDrop() {
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            document.addEventListener(eventName, this.preventDefaults, false);
        });

        // Compile mode drag/drop
        ['dragenter', 'dragover'].forEach(eventName => {
            this.fdoInput.addEventListener(eventName, () => this.showDropZone(), false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            this.fdoInput.addEventListener(eventName, () => this.hideDropZone(), false);
        });

        this.fdoInput.addEventListener('drop', (e) => this.handleDrop(e), false);
        this.dropZone.addEventListener('drop', (e) => this.handleDrop(e), false);

        // Decompile mode drag/drop
        this.binaryDropZone.addEventListener('drop', (e) => this.handleBinaryDrop(e), false);
    }

    preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    showDropZone() {
        if (this.mode === 'compile') {
            this.dropZone.classList.add('active');
        }
    }

    hideDropZone() {
        if (this.mode === 'compile') {
            this.dropZone.classList.remove('active');
        }
    }

    handleDrop(e) {
        this.hideDropZone();
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            this.loadFile(files[0]);
        }
    }

    handleBinaryDrop(e) {
        e.preventDefault();
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            this.loadBinaryFile(files[0]);
        }
    }

    handleFileSelect(e) {
        const file = e.target.files[0];
        if (file) {
            this.loadFile(file);
        }
    }

    loadFile(file) {
        if (!file.type.match('text.*') && !file.name.match(/\.(txt|fdo)$/i)) {
            this.showStatus('error', 'Invalid File Type', 'Please select a text file (.txt or .fdo)');
            return;
        }

        const reader = new FileReader();
        reader.onload = (e) => {
            this.fdoInput.value = e.target.result;
            this.updateCharCount();
            this.hideAllOutput();
            this.hideStatus();
        };
        reader.onerror = () => {
            this.showStatus('error', 'File Read Error', 'Could not read the selected file');
        };
        reader.readAsText(file);
    }

    handleBinaryFileSelect(e) {
        const file = e.target.files[0];
        if (file) {
            this.loadBinaryFile(file);
        }
    }

    loadBinaryFile(file) {
        if (!file.name.match(/\.(fdo|str|bin)$/i)) {
            this.showStatus('error', 'Invalid File Type', 'Please select a binary file (.fdo, .str, or .bin)');
            return;
        }

        const reader = new FileReader();
        reader.onload = (e) => {
            this.currentBinaryData = new Uint8Array(e.target.result);
            this.showBinaryFilePreview(file, this.currentBinaryData);
            this.hideAllOutput();
            this.hideStatus();
        };
        reader.onerror = () => {
            this.showStatus('error', 'File Read Error', 'Could not read the selected binary file');
        };
        reader.readAsArrayBuffer(file);
    }

    showBinaryFilePreview(file, data) {
        this.binaryFileName.textContent = file.name;
        this.binaryFileSize.textContent = this.formatBytes(data.length);
        this.binarySize.textContent = data.length.toLocaleString();

        // Generate hex preview
        this.generateBinaryPreview(data);
        this.binaryFilePreview.style.display = 'block';
    }

    toggleExamples(e) {
        e.stopPropagation();
        this.examplesMenu.classList.toggle('show');
    }

    closeExamples(e) {
        if (!this.examplesBtn.contains(e.target)) {
            this.examplesMenu.classList.remove('show');
        }
    }

    selectExample(e) {
        if (e.target.classList.contains('example-item')) {
            const exampleKey = e.target.dataset.example;
            if (this.examples[exampleKey]) {
                this.fdoInput.value = this.examples[exampleKey].source;
                this.updateCharCount();
                this.hideAllOutput();
                this.hideStatus();
                this.examplesMenu.classList.remove('show');
            }
        }
    }

    handleKeyboard(e) {
        // Ctrl/Cmd + Enter to execute action
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
            e.preventDefault();
            this.executeAction();
        }

        // Ctrl/Cmd + K to clear
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            if (this.mode === 'compile') {
                this.clearInput();
            } else {
                this.clearBinaryInput();
            }
        }
    }

    generateBinaryPreview(data = null, targetElement = null) {
        const sourceData = data || this.compiledData;
        if (!sourceData) return;

        const bytes = new Uint8Array(sourceData);
        const lines = [];
        const maxLines = 8;

        for (let i = 0; i < Math.min(bytes.length, maxLines * 16); i += 16) {
            const offset = i.toString(16).padStart(8, '0').toUpperCase();
            const hexBytes = [];
            const asciiChars = [];

            for (let j = 0; j < 16 && i + j < bytes.length; j++) {
                const byte = bytes[i + j];
                hexBytes.push(byte.toString(16).padStart(2, '0').toUpperCase());
                asciiChars.push(byte >= 32 && byte <= 126 ? String.fromCharCode(byte) : '.');
            }

            while (hexBytes.length < 16) {
                hexBytes.push('  ');
            }

            const hexLine = hexBytes.join(' ');
            const asciiLine = asciiChars.join('');

            lines.push(`<div class="hex-line">
                <span class="hex-offset">${offset}</span>
                <span class="hex-bytes">${hexLine}</span>
                <span class="hex-ascii">${asciiLine}</span>
            </div>`);
        }

        if (bytes.length > maxLines * 16) {
            lines.push('<div class="hex-line">...</div>');
        }

        // Use target element if provided, otherwise fall back to binaryHexPreview
        const target = targetElement || this.binaryHexPreview;
        if (target) {
            target.innerHTML = lines.join('');
        }
    }

    showStatus(type, title, message) {
        const icons = {
            success: `<svg class="status-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
                <polyline points="22,4 12,14.01 9,11.01"/>
            </svg>`,
            error: `<svg class="status-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10"/>
                <line x1="15" y1="9" x2="9" y2="15"/>
                <line x1="9" y1="9" x2="15" y2="15"/>
            </svg>`,
            loading: `<svg class="status-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 12a9 9 0 1 1-6.219-8.56"/>
            </svg>`
        };

        this.statusContent.innerHTML = `
            <div class="status-content">
                ${icons[type]}
                <div class="status-text">
                    <div class="status-title">${title}</div>
                    <div class="status-message">${message}</div>
                </div>
            </div>
        `;

        this.statusSection.className = `status-section status-${type} show`;
    }

    hideStatus() {
        this.statusSection.classList.remove('show');
    }

    hideAllOutput() {
        // Hide simple result displays
        if (this.compileResult) {
            this.compileResult.style.display = 'none';
        }
        if (this.decompileResult) {
            this.decompileResult.style.display = 'none';
        }
    }


    // Binary input tab switching
    switchBinaryTab(tab) {
        // Update tab buttons
        this.binaryTabs.forEach(btn => btn.classList.remove('active'));
        document.querySelector(`[data-tab="${tab}"]`).classList.add('active');

        // Update tab content
        const allTabs = document.querySelectorAll('.binary-tab-content');
        allTabs.forEach(content => {
            content.classList.remove('active');
            content.style.display = 'none';
        });

        if (tab === 'file') {
            this.fileTab.classList.add('active');
            this.fileTab.style.display = 'block';
        } else if (tab === 'hex') {
            this.hexTab.classList.add('active');
            this.hexTab.style.display = 'block';
        }
    }

    // Update hex preview and size
    updateHexPreview() {
        const hexData = this.hexInput.value.trim();
        if (!hexData) {
            this.hexDecodedSize.textContent = '0';
            this.binarySize.textContent = '0';
            return;
        }

        // Clean hex data (remove spaces and non-hex characters)
        const cleanHex = hexData.replace(/[^0-9A-Fa-f]/g, '');

        if (cleanHex.length % 2 !== 0) {
            // Invalid hex length
            this.hexDecodedSize.textContent = 'Invalid';
            return;
        }

        const byteCount = cleanHex.length / 2;
        this.hexDecodedSize.textContent = byteCount;
        this.binarySize.textContent = byteCount;
    }

    // Format hex input with proper spacing
    formatHex() {
        const hexData = this.hexInput.value.trim();
        if (!hexData) return;

        // Clean and format hex data
        const cleanHex = hexData.replace(/[^0-9A-Fa-f]/g, '').toUpperCase();
        const formattedHex = cleanHex.match(/.{1,2}/g)?.join(' ') || cleanHex;

        this.hexInput.value = formattedHex;
        this.updateHexPreview();
    }

    // Get binary data from current decompile input (file or hex)
    getBinaryData() {
        const activeTab = document.querySelector('.binary-tab.active')?.dataset.tab;

        if (activeTab === 'hex') {
            // Get data from hex input
            const hexData = this.hexInput.value.trim();
            if (!hexData) return null;

            const cleanHex = hexData.replace(/[^0-9A-Fa-f]/g, '');
            if (cleanHex.length % 2 !== 0) return null;

            // Convert hex to binary
            const bytes = [];
            for (let i = 0; i < cleanHex.length; i += 2) {
                bytes.push(parseInt(cleanHex.substr(i, 2), 16));
            }
            return new Uint8Array(bytes);
        } else {
            // Get data from file input (existing functionality)
            return this.currentBinaryData;
        }
    }

    formatBytes(bytes) {
        if (bytes === 0) return '0 bytes';
        const k = 1024;
        const sizes = ['bytes', 'KB', 'MB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new AtomForge();

    // Add loading animation to the page
    document.body.style.opacity = '0';
    document.body.style.transform = 'translateY(20px)';
    document.body.style.transition = 'opacity 0.5s ease, transform 0.5s ease';

    setTimeout(() => {
        document.body.style.opacity = '1';
        document.body.style.transform = 'translateY(0)';
    }, 100);
});