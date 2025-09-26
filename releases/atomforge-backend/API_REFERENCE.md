# AtomForge Backend API Reference

This document provides complete API reference for the AtomForge Backend HTTP daemon (`fdo_daemon.exe`).

## Base URL

The daemon runs on `http://localhost:8080` by default. Use `--port` and `--host` options to customize.

## Authentication

No authentication is required for the API endpoints.

## Content Types

- **Request bodies**: `text/plain` for compilation, `application/octet-stream` for decompilation
- **Success responses**: `application/octet-stream` for compiled binary, `text/plain` for decompiled source
- **Error responses**: `application/json` with structured error information

## Endpoints

### POST /compile

Compile FDO source text to binary format.

**Request:**
- **Method**: `POST`
- **Content-Type**: `text/plain`
- **Body**: FDO source text

**Success Response:**
- **Status**: `200 OK`
- **Content-Type**: `application/octet-stream`
- **Body**: Compiled binary FDO data

**Error Responses:**

#### 400 Bad Request - Syntax Errors
```json
{
  "error": {
    "message": "Ada32 error rc=0x2F0006 (3145734): Missing Quote",
    "code": "0x2F0006",
    "line": 15,
    "column": 23,
    "kind": "Missing Quote",
    "context": [
      "  13 | uni_start_stream <00x>",
      "  14 |   man_start_object <independent, \"Object Name>",
      ">>15 |     mat_object_id <32-105",
      "  16 |     mat_orientation <vcf>",
      "  17 |   man_end_object"
    ],
    "hint": "unmatched quote — check for odd # of '\"' on this line or a missing closing quote across lines."
  }
}
```

#### 422 Unprocessable Entity - Semantic Errors
```json
{
  "error": {
    "message": "Ada32 error rc=0x2F000A (3145738): Unrecognized Atom",
    "code": "0x2F000A",
    "line": 8,
    "kind": "Unrecognized Atom",
    "context": [
      "   6 | uni_start_stream <00x>",
      "   7 |   man_start_object <independent, \"Valid Object\">",
      ">> 8 |     invalid_command <parameter>",
      "   9 |     mat_orientation <vcf>",
      "  10 |   man_end_object"
    ],
    "hint": "unrecognized atom — first token on this line may not match Ada's atom table; check spelling and protocol."
  }
}
```

#### 500 Internal Server Error - System Errors
```json
{
  "error": {
    "message": "FDO API not initialized",
    "code": "0xffffffff"
  }
}
```

### POST /decompile

Decompile binary FDO data to source text.

**Request:**
- **Method**: `POST`
- **Content-Type**: `application/octet-stream`
- **Body**: Binary FDO data

**Success Response:**
- **Status**: `200 OK`
- **Content-Type**: `text/plain`
- **Body**: Decompiled FDO source text

**Error Responses:**
Similar structure to `/compile` endpoint, but context information is limited for binary input.

### GET /health

Get daemon health status.

**Request:**
- **Method**: `GET`

**Response:**
- **Status**: `200 OK`
- **Content-Type**: `application/json`

```json
{
  "status": "ok",
  "ada32_loaded": true,
  "version": "1.0.0",
  "requests_processed": 1247,
  "successful_requests": 1198,
  "failed_requests": 49,
  "uptime_seconds": 3672
}
```

### GET /stats

Get daemon statistics.

**Request:**
- **Method**: `GET`

**Response:**
- **Status**: `200 OK`
- **Content-Type**: `application/json`

```json
{
  "requests_processed": 1247,
  "successful_requests": 1198,
  "failed_requests": 49,
  "uptime_seconds": 3672
}
```

## Error Response Fields

### Required Fields
- `error.message`: Human-readable error description
- `error.code`: Hexadecimal error code from Ada32.dll

### Optional Context Fields (when available)
- `error.line`: 1-based line number where error occurred
- `error.column`: 1-based column position (estimated, may be -1)
- `error.kind`: Human-readable error type ("Missing Quote", "Unrecognized Atom", etc.)
- `error.context`: Array of strings showing surrounding source lines with error indicator (`>>`)
- `error.hint`: Helpful suggestion for fixing the error

### HTTP Status Code Mapping

| Status | Meaning | When Used |
|--------|---------|-----------|
| 200 | OK | Operation successful |
| 400 | Bad Request | Syntax errors, malformed FDO source |
| 422 | Unprocessable Entity | Semantic errors in valid syntax |
| 500 | Internal Server Error | System errors, API initialization failures |

## Common Error Codes

| Code | Kind | Description | Typical HTTP Status |
|------|------|-------------|-------------------|
| 0x2F0006 | Missing Quote | Unmatched quotes in FDO source | 400 |
| 0x2F000A | Unrecognized Atom | Unknown command or atom name | 400 |
| 0xFFFFFFFF | System Error | API not initialized or internal failure | 500 |

## Usage Examples

### Successful Compilation

```bash
curl -X POST \
  -H "Content-Type: text/plain" \
  --data-binary @example.fdo.source.txt \
  http://localhost:8080/compile \
  -o compiled.bin
```

### Handling Compilation Errors

```bash
# This will return JSON error response with line/column info
curl -X POST \
  -H "Content-Type: text/plain" \
  --data-binary @invalid.fdo.source.txt \
  http://localhost:8080/compile
```

### Successful Decompilation

```bash
curl -X POST \
  -H "Content-Type: application/octet-stream" \
  --data-binary @compiled.bin \
  http://localhost:8080/decompile \
  -o decompiled.txt
```

### Health Check

```bash
curl http://localhost:8080/health
```

## Client Implementation Notes

1. **Always check HTTP status code** first to determine success/failure
2. **Parse JSON error responses** for detailed error information when status is 4xx or 5xx
3. **Use line/column information** to highlight problematic areas in editors
4. **Display context lines** to help users understand the error location
5. **Show hints** to provide actionable guidance for fixing errors
6. **Implement retry logic** for 500 errors but not for 400/422 errors

## Rate Limiting

No rate limiting is currently implemented. Consider implementing client-side throttling for high-volume usage.

## Binary Compatibility

This API is compatible with FDO files from AOL Database systems. The included sample files demonstrate various FDO patterns and can be used for testing integration.