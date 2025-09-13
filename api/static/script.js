// AtomForge Web Interface
class FDOCompiler {
    constructor() {
        this.apiEndpoint = '/compile';
        this.init();
    }

    init() {
        this.bindElements();
        this.bindEvents();
        this.loadExamples();
        this.updateCharCount();
    }

    bindElements() {
        // Input elements
        this.fdoInput = document.getElementById('fdoInput');
        this.charCount = document.getElementById('charCount');
        this.clearBtn = document.getElementById('clearBtn');
        this.fileInput = document.getElementById('fileInput');
        this.dropZone = document.getElementById('dropZone');

        // Examples
        this.examplesBtn = document.getElementById('examplesBtn');
        this.examplesMenu = document.getElementById('examplesMenu');

        // Compile
        this.compileBtn = document.getElementById('compileBtn');

        // Status and output
        this.statusSection = document.getElementById('statusSection');
        this.statusContent = document.getElementById('statusContent');
        this.outputSection = document.getElementById('outputSection');
        this.outputSize = document.getElementById('outputSize');
        this.binaryPreview = document.getElementById('binaryPreview');
        this.downloadBtn = document.getElementById('downloadBtn');
        this.copyHexBtn = document.getElementById('copyHexBtn');

        // Store compiled data
        this.compiledData = null;
    }

    bindEvents() {
        // Input events
        this.fdoInput.addEventListener('input', () => this.updateCharCount());
        this.clearBtn.addEventListener('click', () => this.clearInput());

        // File upload
        this.fileInput.addEventListener('change', (e) => this.handleFileSelect(e));
        this.dropZone.addEventListener('click', () => this.fileInput.click());

        // Drag and drop
        this.setupDragDrop();

        // Examples
        this.examplesBtn.addEventListener('click', (e) => this.toggleExamples(e));
        document.addEventListener('click', (e) => this.closeExamples(e));
        this.examplesMenu.addEventListener('click', (e) => this.selectExample(e));

        // Compile
        this.compileBtn.addEventListener('click', () => this.compileFDO());

        // Download
        this.downloadBtn.addEventListener('click', () => this.downloadFile());
        
        // Copy hex
        this.copyHexBtn.addEventListener('click', () => this.copyHex());

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => this.handleKeyboard(e));
    }

    async loadExamples() {
        try {
            const response = await fetch('/examples');
            if (response.ok) {
                const examples = await response.json();
                this.examples = {};
                
                // Convert API response to examples object
                examples.forEach(example => {
                    this.examples[example.id] = {
                        name: example.name,
                        source: example.source,
                        description: example.description
                    };
                });
                
                // Populate the examples dropdown
                this.populateExamplesMenu();
                console.log(`Loaded ${examples.length} examples from golden tests`);
            } else {
                console.warn('Failed to load examples, using fallback');
                this.setupFallbackExamples();
            }
        } catch (error) {
            console.error('Error loading examples:', error);
            this.setupFallbackExamples();
        }
    }

    populateExamplesMenu() {
        // Clear existing menu items
        this.examplesMenu.innerHTML = '';
        
        // Add examples to menu
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
        // Fallback examples if API fails
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
        this.hideOutput();
        this.hideStatus();
        this.fdoInput.focus();
    }

    setupDragDrop() {
        // Prevent default drag behaviors
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            document.addEventListener(eventName, this.preventDefaults, false);
        });

        // Highlight drop zone when item is dragged over it
        ['dragenter', 'dragover'].forEach(eventName => {
            this.fdoInput.addEventListener(eventName, () => this.showDropZone(), false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            this.fdoInput.addEventListener(eventName, () => this.hideDropZone(), false);
        });

        // Handle dropped files
        this.fdoInput.addEventListener('drop', (e) => this.handleDrop(e), false);
        this.dropZone.addEventListener('drop', (e) => this.handleDrop(e), false);
    }

    preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    showDropZone() {
        this.dropZone.classList.add('active');
    }

    hideDropZone() {
        this.dropZone.classList.remove('active');
    }

    handleDrop(e) {
        this.hideDropZone();
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            this.loadFile(files[0]);
        }
    }

    handleFileSelect(e) {
        const file = e.target.files[0];
        if (file) {
            this.loadFile(file);
        }
    }

    loadFile(file) {
        if (!file.type.match('text.*') && !file.name.match(/\\.(txt|fdo)$/i)) {
            this.showStatus('error', 'Invalid File Type', 'Please select a text file (.txt or .fdo)');
            return;
        }

        const reader = new FileReader();
        reader.onload = (e) => {
            this.fdoInput.value = e.target.result;
            this.updateCharCount();
            this.hideOutput();
            this.hideStatus();
        };
        reader.onerror = () => {
            this.showStatus('error', 'File Read Error', 'Could not read the selected file');
        };
        reader.readAsText(file);
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
                this.hideOutput();
                this.hideStatus();
                this.examplesMenu.classList.remove('show');
            }
        }
    }

    handleKeyboard(e) {
        // Ctrl/Cmd + Enter to compile
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
            e.preventDefault();
            this.compileFDO();
        }

        // Ctrl/Cmd + K to clear
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            this.clearInput();
        }
    }

    async compileFDO() {
        const source = this.fdoInput.value.trim();
        
        if (!source) {
            this.showStatus('error', 'Empty Input', 'Please enter FDO source code to compile');
            return;
        }

        // Show loading state
        this.compileBtn.disabled = true;
        this.compileBtn.classList.add('loading');
        this.hideOutput();
        this.showStatus('loading', 'Compiling...', 'Processing FDO source with native compiler');

        try {
            const response = await fetch(this.apiEndpoint, {
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
                this.showSuccess(parseInt(size));
                this.showStatus('success', 'Compilation Successful', 
                    `Generated ${this.formatBytes(parseInt(size))} of binary FDO data`);
                
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
            this.compileBtn.disabled = false;
            this.compileBtn.classList.remove('loading');
        }
    }

    showSuccess(size) {
        this.outputSize.textContent = this.formatBytes(size);
        this.generateBinaryPreview();
        this.outputSection.style.display = 'block';
        
        // Smooth scroll to output
        setTimeout(() => {
            this.outputSection.scrollIntoView({ 
                behavior: 'smooth', 
                block: 'start' 
            });
        }, 100);
    }

    generateBinaryPreview() {
        if (!this.compiledData) return;
        
        const bytes = new Uint8Array(this.compiledData);
        const lines = [];
        const maxLines = 8; // Show first 8 lines of hex
        
        for (let i = 0; i < Math.min(bytes.length, maxLines * 16); i += 16) {
            const offset = i.toString(16).padStart(8, '0');
            const hexBytes = [];
            const asciiChars = [];
            
            for (let j = 0; j < 16 && i + j < bytes.length; j++) {
                const byte = bytes[i + j];
                hexBytes.push(byte.toString(16).padStart(2, '0'));
                asciiChars.push(byte >= 32 && byte <= 126 ? String.fromCharCode(byte) : '.');
            }
            
            // Pad hex bytes to maintain alignment
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
        
        this.binaryPreview.innerHTML = lines.join('');
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
        
        // Show feedback
        this.showTemporaryMessage('📥 Download started!');
    }

    copyHex() {
        if (!this.compiledData) return;
        
        const bytes = new Uint8Array(this.compiledData);
        const hexString = Array.from(bytes)
            .map(byte => byte.toString(16).padStart(2, '0'))
            .join('');
        
        navigator.clipboard.writeText(hexString).then(() => {
            this.showTemporaryMessage('📋 Hex copied to clipboard!');
        }).catch(() => {
            // Fallback for older browsers
            const textArea = document.createElement('textarea');
            textArea.value = hexString;
            textArea.style.position = 'fixed';
            textArea.style.left = '-999999px';
            textArea.style.top = '-999999px';
            document.body.appendChild(textArea);
            textArea.focus();
            textArea.select();
            
            try {
                document.execCommand('copy');
                this.showTemporaryMessage('📋 Hex copied to clipboard!');
            } catch (err) {
                this.showTemporaryMessage('❌ Failed to copy hex');
            }
            
            document.body.removeChild(textArea);
        });
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

    hideOutput() {
        this.outputSection.style.display = 'none';
    }

    showTemporaryMessage(message) {
        const toast = document.createElement('div');
        toast.textContent = message;
        toast.style.cssText = `
            position: fixed;
            top: 2rem;
            right: 2rem;
            background: var(--success-gradient);
            color: white;
            padding: 1rem 1.5rem;
            border-radius: 8px;
            font-weight: 500;
            box-shadow: var(--shadow-lg);
            z-index: 1000;
            transform: translateX(100%);
            transition: transform 0.3s ease;
        `;
        
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.style.transform = 'translateX(0)';
        }, 100);
        
        setTimeout(() => {
            toast.style.transform = 'translateX(100%)';
            setTimeout(() => document.body.removeChild(toast), 300);
        }, 3000);
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
    new FDOCompiler();
    
    // Add some nice loading animation to the page
    document.body.style.opacity = '0';
    document.body.style.transform = 'translateY(20px)';
    document.body.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
    
    setTimeout(() => {
        document.body.style.opacity = '1';
        document.body.style.transform = 'translateY(0)';
    }, 100);
});