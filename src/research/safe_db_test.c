/*
 * Safe database function testing with proper error handling
 */
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>

// Try both calling conventions
typedef int (__stdcall *DBOpen_stdcall_t)(const char* filename);
typedef int (__cdecl *DBOpen_cdecl_t)(const char* filename);
typedef int (__stdcall *DBClose_stdcall_t)(int handle);
typedef int (__cdecl *DBClose_cdecl_t)(int handle);
typedef int (__stdcall *DBExtractRecord_stdcall_t)(int handle, int recordId, void* buffer, int* bufferSize);
typedef int (__cdecl *DBExtractRecord_cdecl_t)(int handle, int recordId, void* buffer, int* bufferSize);

int test_extraction_safe(int dbHandle, void* extract_func, int use_stdcall, int record_id) {
    printf("Testing record ID %d with %s calling convention...\n", 
           record_id, use_stdcall ? "__stdcall" : "__cdecl");
    
    // Allocate buffer safely
    char* buffer = malloc(1024);
    if (!buffer) {
        printf("❌ Memory allocation failed\n");
        return 0;
    }
    
    memset(buffer, 0, 1024);
    int buffer_size = 1024;
    int result = 0;
    
    // Try the extraction with proper error handling
    __try {
        if (use_stdcall) {
            result = ((DBExtractRecord_stdcall_t)extract_func)(dbHandle, record_id, buffer, &buffer_size);
        } else {
            result = ((DBExtractRecord_cdecl_t)extract_func)(dbHandle, record_id, buffer, &buffer_size);
        }
        
        printf("  result=%d, buffer_size=%d\n", result, buffer_size);
        
        if (result > 0 && buffer_size > 0 && buffer_size < 1024) {
            printf("  ✅ SUCCESS! Extracted %d bytes\n", buffer_size);
            printf("  First 8 bytes: ");
            for (int i = 0; i < 8 && i < buffer_size; i++) {
                printf("%02x ", (unsigned char)buffer[i]);
            }
            printf("\n");
            
            // Check for FDO format
            if (buffer_size >= 2 && (unsigned char)buffer[0] == 0x40 && (unsigned char)buffer[1] == 0x01) {
                printf("  🎯 FDO FORMAT!\n");
                
                if (buffer_size == 356) {
                    printf("  🎉 PERFECT SIZE - TARGET FOUND!\n");
                    
                    // Save the record
                    char filename[256];
                    sprintf(filename, "test_output/extracted_record_%d.str", record_id);
                    FILE* fp = fopen(filename, "wb");
                    if (fp) {
                        fwrite(buffer, 1, buffer_size, fp);
                        fclose(fp);
                        printf("  💾 Saved to %s\n", filename);
                    }
                    
                    free(buffer);
                    return 1;  // Success!
                }
            }
        } else if (result == 0) {
            // Don't print failure for result=0, it's expected for non-existent records
        } else {
            printf("  ❌ Failed: result=%d, size=%d\n", result, buffer_size);
        }
        
    } __except(EXCEPTION_EXECUTE_HANDLER) {
        printf("  💥 EXCEPTION occurred during extraction\n");
    }
    
    free(buffer);
    return 0;
}

int main() {
    printf("=== Safe Database Function Testing ===\n");
    
    HMODULE hDbaol = LoadLibrary("Dbaol32.dll");
    if (!hDbaol) {
        printf("❌ Failed to load Dbaol32.dll\n");
        return 1;
    }
    
    // Get function pointers
    void* DBOpen_func = GetProcAddress(hDbaol, "DBOpen");
    void* DBClose_func = GetProcAddress(hDbaol, "DBClose");
    void* DBExtractRecord_func = GetProcAddress(hDbaol, "DBExtractRecord");
    
    if (!DBOpen_func || !DBExtractRecord_func) {
        printf("❌ Required functions not found\n");
        FreeLibrary(hDbaol);
        return 1;
    }
    
    printf("✅ Functions loaded successfully\n");
    
    // Try opening database with both calling conventions
    int dbHandle = 0;
    int using_stdcall = 1;
    
    // Try __stdcall first
    printf("\nTrying __stdcall DBOpen...\n");
    dbHandle = ((DBOpen_stdcall_t)DBOpen_func)("golden_tests/main.IDX");
    printf("__stdcall DBOpen result: %d\n", dbHandle);
    
    if (dbHandle <= 0) {
        // Try __cdecl
        printf("Trying __cdecl DBOpen...\n");
        dbHandle = ((DBOpen_cdecl_t)DBOpen_func)("golden_tests/main.IDX");
        printf("__cdecl DBOpen result: %d\n", dbHandle);
        using_stdcall = 0;
    }
    
    if (dbHandle <= 0) {
        printf("❌ Could not open database with either calling convention\n");
        FreeLibrary(hDbaol);
        return 1;
    }
    
    printf("✅ Database opened successfully!\n");
    
    // Test extraction with a small set of record IDs
    int test_ids[] = {0, 1, 2, 3, 4, 5, 100, 105, 106, 1000};
    int num_tests = sizeof(test_ids) / sizeof(test_ids[0]);
    
    printf("\n=== Testing Record Extraction ===\n");
    
    for (int i = 0; i < num_tests; i++) {
        int record_id = test_ids[i];
        
        // Test with current calling convention first
        if (test_extraction_safe(dbHandle, DBExtractRecord_func, using_stdcall, record_id)) {
            printf("🎉 SUCCESS! Found working record extraction!\n");
            break;
        }
        
        // If that failed and we're using stdcall, also try cdecl
        if (using_stdcall) {
            if (test_extraction_safe(dbHandle, DBExtractRecord_func, 0, record_id)) {
                printf("🎉 SUCCESS with __cdecl! Found working record extraction!\n");
                break;
            }
        }
    }
    
    // Close database
    if (DBClose_func) {
        if (using_stdcall) {
            ((DBClose_stdcall_t)DBClose_func)(dbHandle);
        } else {
            ((DBClose_cdecl_t)DBClose_func)(dbHandle);
        }
    }
    
    FreeLibrary(hDbaol);
    return 0;
}