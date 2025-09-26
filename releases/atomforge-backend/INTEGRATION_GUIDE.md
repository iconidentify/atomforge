# AtomForge Backend Integration Guide

This guide provides best practices and examples for integrating the AtomForge Backend HTTP API into web applications, IDEs, and other tools.

## Quick Start

### Starting the Daemon

```bash
# Start daemon on default port 8080
fdo_daemon.exe

# Start daemon on custom port
fdo_daemon.exe --port 9000

# Start daemon with verbose logging
fdo_daemon.exe --verbose

# Start daemon quietly (suppress non-error output)
fdo_daemon.exe --quiet
```

### Basic API Usage

```javascript
// Compile FDO source to binary
async function compileFdo(sourceText) {
    const response = await fetch('http://localhost:8080/compile', {
        method: 'POST',
        headers: { 'Content-Type': 'text/plain' },
        body: sourceText
    });

    if (response.ok) {
        return await response.arrayBuffer();
    } else {
        const error = await response.json();
        throw new CompilationError(error);
    }
}

// Decompile binary FDO to source
async function decompileFdo(binaryData) {
    const response = await fetch('http://localhost:8080/decompile', {
        method: 'POST',
        headers: { 'Content-Type': 'application/octet-stream' },
        body: binaryData
    });

    if (response.ok) {
        return await response.text();
    } else {
        const error = await response.json();
        throw new DecompilationError(error);
    }
}
```

## Error Handling Best Practices

### 1. Implement Proper HTTP Status Code Handling

```javascript
async function handleApiRequest(url, options) {
    try {
        const response = await fetch(url, options);

        if (response.ok) {
            // Success - return appropriate data type
            if (response.headers.get('content-type')?.includes('application/octet-stream')) {
                return await response.arrayBuffer();
            } else if (response.headers.get('content-type')?.includes('application/json')) {
                return await response.json();
            } else {
                return await response.text();
            }
        } else {
            // Error - parse JSON error response
            const errorData = await response.json();
            const error = new FdoApiError(errorData.error, response.status);
            throw error;
        }
    } catch (error) {
        if (error instanceof FdoApiError) {
            throw error;
        }
        // Network or other errors
        throw new NetworkError(error.message);
    }
}

class FdoApiError extends Error {
    constructor(errorInfo, statusCode) {
        super(errorInfo.message);
        this.name = 'FdoApiError';
        this.statusCode = statusCode;
        this.errorCode = errorInfo.code;
        this.line = errorInfo.line;
        this.column = errorInfo.column;
        this.kind = errorInfo.kind;
        this.context = errorInfo.context;
        this.hint = errorInfo.hint;
    }

    get isSyntaxError() {
        return this.statusCode === 400;
    }

    get isSemanticError() {
        return this.statusCode === 422;
    }

    get isServerError() {
        return this.statusCode === 500;
    }
}
```

### 2. Display Error Context in UI

```javascript
function displayCompilationError(error, editorInstance) {
    if (error instanceof FdoApiError && error.line) {
        // Highlight error line in editor
        editorInstance.addLineClass(error.line - 1, 'background', 'error-line');

        if (error.column > 0) {
            // Highlight specific column if available
            editorInstance.setCursor(error.line - 1, error.column - 1);
        }

        // Show context tooltip
        const contextHtml = error.context
            .map(line => `<div class="context-line">${escapeHtml(line)}</div>`)
            .join('');

        showTooltip(editorInstance, error.line - 1, {
            title: error.kind || 'Compilation Error',
            content: `
                <div class="error-message">${escapeHtml(error.message)}</div>
                <div class="error-context">${contextHtml}</div>
                ${error.hint ? `<div class="error-hint">${escapeHtml(error.hint)}</div>` : ''}
            `
        });
    } else {
        // Fallback for errors without line information
        showGenericError(error.message);
    }
}
```

### 3. Implement Retry Logic

```javascript
async function compileFdoWithRetry(sourceText, maxRetries = 3) {
    let lastError;

    for (let attempt = 0; attempt < maxRetries; attempt++) {
        try {
            return await compileFdo(sourceText);
        } catch (error) {
            lastError = error;

            if (error instanceof FdoApiError) {
                if (error.isSyntaxError || error.isSemanticError) {
                    // Don't retry client errors
                    throw error;
                }

                if (error.isServerError && attempt < maxRetries - 1) {
                    // Wait before retrying server errors
                    await new Promise(resolve => setTimeout(resolve, 1000 * (attempt + 1)));
                    continue;
                }
            }

            // Network errors - retry with exponential backoff
            if (error instanceof NetworkError && attempt < maxRetries - 1) {
                await new Promise(resolve => setTimeout(resolve, 1000 * Math.pow(2, attempt)));
                continue;
            }

            throw error;
        }
    }

    throw lastError;
}
```

## UI Integration Patterns

### 1. Real-time Syntax Validation

```javascript
class FdoEditor {
    constructor(elementId) {
        this.editor = CodeMirror.fromTextArea(document.getElementById(elementId), {
            mode: 'fdo',
            lineNumbers: true,
            gutters: ['error-gutter', 'CodeMirror-linenumbers']
        });

        // Debounce validation to avoid excessive API calls
        this.validateDebounced = debounce(this.validate.bind(this), 1000);

        this.editor.on('change', () => {
            this.clearErrors();
            this.validateDebounced();
        });
    }

    async validate() {
        const source = this.editor.getValue();
        if (!source.trim()) return;

        try {
            await compileFdo(source);
            this.showSuccess();
        } catch (error) {
            if (error instanceof FdoApiError) {
                this.showError(error);
            } else {
                this.showNetworkError(error);
            }
        }
    }

    showError(error) {
        if (error.line) {
            // Mark error line in gutter
            const marker = document.createElement('div');
            marker.className = 'error-marker';
            marker.title = error.message;
            this.editor.setGutterMarker(error.line - 1, 'error-gutter', marker);

            // Add line styling
            this.editor.addLineClass(error.line - 1, 'background', 'error-line');
        }

        // Update status bar
        this.updateStatus(`Error: ${error.message}`, 'error');
    }

    clearErrors() {
        this.editor.clearGutter('error-gutter');
        for (let i = 0; i < this.editor.lineCount(); i++) {
            this.editor.removeLineClass(i, 'background', 'error-line');
        }
    }
}
```

### 2. Batch Processing with Progress

```javascript
async function processMultipleFdoFiles(files, onProgress) {
    const results = [];
    let completed = 0;

    for (const file of files) {
        try {
            const sourceText = await readFileAsText(file);
            const compiled = await compileFdo(sourceText);

            results.push({
                file: file.name,
                success: true,
                data: compiled
            });
        } catch (error) {
            results.push({
                file: file.name,
                success: false,
                error: error
            });
        }

        completed++;
        onProgress(completed, files.length);
    }

    return results;
}

// Usage
const files = document.getElementById('file-input').files;
const progressBar = document.getElementById('progress');

const results = await processMultipleFdoFiles(files, (completed, total) => {
    const percentage = (completed / total) * 100;
    progressBar.style.width = `${percentage}%`;
    progressBar.textContent = `${completed}/${total} files processed`;
});

// Handle results
const errors = results.filter(r => !r.success);
if (errors.length > 0) {
    displayBatchErrors(errors);
}
```

### 3. Auto-save with Compilation Status

```javascript
class AutoSaveFdoEditor extends FdoEditor {
    constructor(elementId, saveEndpoint) {
        super(elementId);
        this.saveEndpoint = saveEndpoint;
        this.autoSaveDebounced = debounce(this.autoSave.bind(this), 2000);

        this.editor.on('change', () => {
            this.autoSaveDebounced();
        });
    }

    async autoSave() {
        const source = this.editor.getValue();

        // First validate the syntax
        let compilationStatus = 'unknown';
        try {
            await compileFdo(source);
            compilationStatus = 'valid';
        } catch (error) {
            if (error instanceof FdoApiError) {
                compilationStatus = 'invalid';
                this.lastError = error;
            } else {
                compilationStatus = 'error';
            }
        }

        // Save to server with compilation status
        await fetch(this.saveEndpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                source: source,
                compilationStatus: compilationStatus,
                lastError: compilationStatus === 'invalid' ? this.lastError : null,
                timestamp: new Date().toISOString()
            })
        });

        this.updateSaveStatus(compilationStatus);
    }
}
```

## Performance Considerations

### 1. Connection Pooling

```javascript
class FdoApiClient {
    constructor(baseUrl = 'http://localhost:8080') {
        this.baseUrl = baseUrl;
        this.activeRequests = 0;
        this.maxConcurrentRequests = 4;
        this.requestQueue = [];
    }

    async makeRequest(endpoint, options) {
        return new Promise((resolve, reject) => {
            const request = { endpoint, options, resolve, reject };

            if (this.activeRequests < this.maxConcurrentRequests) {
                this.processRequest(request);
            } else {
                this.requestQueue.push(request);
            }
        });
    }

    async processRequest({ endpoint, options, resolve, reject }) {
        this.activeRequests++;

        try {
            const response = await fetch(`${this.baseUrl}${endpoint}`, options);
            resolve(response);
        } catch (error) {
            reject(error);
        } finally {
            this.activeRequests--;

            if (this.requestQueue.length > 0) {
                const nextRequest = this.requestQueue.shift();
                this.processRequest(nextRequest);
            }
        }
    }
}
```

### 2. Caching Compilation Results

```javascript
class CachedFdoCompiler {
    constructor() {
        this.cache = new Map();
        this.maxCacheSize = 100;
    }

    getCacheKey(sourceText) {
        // Simple hash function for cache key
        let hash = 0;
        for (let i = 0; i < sourceText.length; i++) {
            const char = sourceText.charCodeAt(i);
            hash = ((hash << 5) - hash) + char;
            hash = hash & hash; // Convert to 32-bit integer
        }
        return hash.toString();
    }

    async compile(sourceText) {
        const key = this.getCacheKey(sourceText);

        if (this.cache.has(key)) {
            return this.cache.get(key);
        }

        try {
            const result = await compileFdo(sourceText);

            // Manage cache size
            if (this.cache.size >= this.maxCacheSize) {
                const firstKey = this.cache.keys().next().value;
                this.cache.delete(firstKey);
            }

            this.cache.set(key, result);
            return result;

        } catch (error) {
            // Don't cache errors
            throw error;
        }
    }
}
```

## Testing Integration

### Unit Tests

```javascript
describe('FDO API Integration', () => {
    let mockServer;

    beforeEach(() => {
        mockServer = setupMockServer();
    });

    afterEach(() => {
        mockServer.teardown();
    });

    test('handles compilation success', async () => {
        mockServer.post('/compile')
            .reply(200, new ArrayBuffer(100), {
                'Content-Type': 'application/octet-stream'
            });

        const result = await compileFdo('valid fdo source');
        expect(result).toBeInstanceOf(ArrayBuffer);
        expect(result.byteLength).toBe(100);
    });

    test('handles compilation errors with context', async () => {
        mockServer.post('/compile')
            .reply(400, {
                error: {
                    message: "Missing Quote",
                    code: "0x2F0006",
                    line: 5,
                    context: [">> 5 | invalid line"],
                    hint: "Check for unmatched quotes"
                }
            });

        try {
            await compileFdo('invalid fdo source');
        } catch (error) {
            expect(error).toBeInstanceOf(FdoApiError);
            expect(error.line).toBe(5);
            expect(error.context).toHaveLength(1);
        }
    });
});
```

## Security Considerations

1. **Input Sanitization**: Always validate and sanitize FDO source before sending to API
2. **Network Security**: Use HTTPS in production environments
3. **Error Information**: Be careful not to expose sensitive information in error messages
4. **Rate Limiting**: Implement client-side rate limiting to prevent API abuse
5. **Validation**: Don't rely solely on client-side validation - server will always validate

## Sample Files

The distribution includes sample FDO files in the `samples/` directory. Use these for:

- **Testing integration**: Verify your client handles various FDO patterns correctly
- **Error testing**: Some samples are designed to trigger specific error conditions
- **Performance testing**: Use larger samples for performance validation
- **User documentation**: Show examples of valid FDO syntax

See `samples/README_SAMPLES.md` for detailed information about each sample file.