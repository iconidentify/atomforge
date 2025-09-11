/*
 * Focus on reading records first - this might reveal the correct patterns
 */
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>

typedef int (__stdcall *DBOpen_t)(const char* filename);
typedef int (__stdcall *DBClose_t)(int handle);
typedef int (__stdcall *DBGetInfo_t)(int handle, void* info);

// All possible extract/read functions
typedef int (__stdcall *DBExtractRecord_stdcall_t)(int handle, int recordId, void* buffer, int* bufferSize);
typedef int (__cdecl *DBExtractRecord_cdecl_t)(int handle, int recordId, void* buffer, int* bufferSize);
typedef int (__stdcall *DBCopyRecord_stdcall_t)(int handle, int recordId, void* buffer, int* bufferSize);
typedef int (__cdecl *DBCopyRecord_cdecl_t)(int handle, int recordId, void* buffer, int* bufferSize);
typedef int (__stdcall *DBCopyThisRecord_stdcall_t)(int handle, void* buffer, int* bufferSize);
typedef int (__cdecl *DBCopyThisRecord_cdecl_t)(int handle, void* buffer, int* bufferSize);

typedef const char* (__stdcall *DBGetLastError_t)(void);

void test_reading_function(const char* func_name, void* func_ptr, int dbHandle, int use_cdecl, int needs_record_id) {
    printf("\n=== Testing %s (%s) ===\n", func_name, use_cdecl ? "__cdecl" : "__stdcall");
    
    if (!func_ptr) {
        printf("❌ Function not available\n");
        return;
    }
    
    char buffer[1024];
    int buffer_size;
    int successful_reads = 0;
    
    if (needs_record_id) {
        // Test a range of record IDs that might exist
        int test_ids[] = {
            0, 1, 2, 3, 4, 5,                    // Very low
            32, 105, 106, 117,                   // From our golden file names
            100, 101, 102, 200, 300,             // Low hundreds
            1000, 1001, 2000, 3000,              // Thousands
            9736,                                // From our manual analysis
            10000, 20000, 30000,                 // Higher
            23057 / 356,                         // Position-based guess
            64, 65                               // Common starting points
        };
        
        int num_tests = sizeof(test_ids) / sizeof(test_ids[0]);
        
        for (int i = 0; i < num_tests; i++) {
            int record_id = test_ids[i];
            buffer_size = sizeof(buffer);
            int result = 0;
            
            if (use_cdecl) {
                result = ((DBExtractRecord_cdecl_t)func_ptr)(dbHandle, record_id, buffer, &buffer_size);
            } else {
                result = ((DBExtractRecord_stdcall_t)func_ptr)(dbHandle, record_id, buffer, &buffer_size);
            }
            
            if (result > 0 && buffer_size > 0 && buffer_size < 1000) {
                printf("✅ ID %d: SUCCESS! Size: %d bytes\n", record_id, buffer_size);
                
                printf("   Header: ");
                for (int j = 0; j < 16 && j < buffer_size; j++) {
                    printf("%02x ", (unsigned char)buffer[j]);
                }
                printf("\n");
                
                // Check for FDO format
                if (buffer_size >= 2 && (unsigned char)buffer[0] == 0x40 && (unsigned char)buffer[1] == 0x01) {
                    printf("   🎯 FDO FORMAT!\n");
                    if (buffer_size == 356) {
                        printf("   🏆 PERFECT SIZE - TARGET RECORD!\n");
                        
                        // Save this successful read
                        char filename[256];
                        sprintf(filename, "test_output/successful_read_%s_id%d.str", func_name, record_id);
                        FILE* fp = fopen(filename, "wb");
                        if (fp) {
                            fwrite(buffer, 1, buffer_size, fp);
                            fclose(fp);
                            printf("   💾 Saved to %s\n", filename);
                        }
                    }
                }
                
                successful_reads++;
                
                if (successful_reads >= 5) {
                    printf("   (Found %d successful reads, stopping...)\n", successful_reads);
                    break;
                }
            } else if (result != 0 || buffer_size != sizeof(buffer)) {
                // Only show non-zero results or size changes
                printf("   ID %d: result=%d, size=%d\n", record_id, result, buffer_size);
            }
        }
        
        printf("Total successful reads: %d\n", successful_reads);
        
    } else {
        // Function doesn't need record ID (like DBCopyThisRecord)
        buffer_size = sizeof(buffer);
        int result = 0;
        
        if (use_cdecl) {
            result = ((DBCopyThisRecord_cdecl_t)func_ptr)(dbHandle, buffer, &buffer_size);
        } else {
            result = ((DBCopyThisRecord_stdcall_t)func_ptr)(dbHandle, buffer, &buffer_size);
        }
        
        printf("Result: %d, size: %d\n", result, buffer_size);
        
        if (result > 0 && buffer_size > 0) {
            printf("✅ SUCCESS! Current record: %d bytes\n", buffer_size);
            
            printf("Header: ");
            for (int j = 0; j < 16 && j < buffer_size; j++) {
                printf("%02x ", (unsigned char)buffer[j]);
            }
            printf("\n");
        }
    }
}

int main() {
    printf("=== Comprehensive Record Reading Test ===\n");
    
    HMODULE hDll = LoadLibrary("Dbaol32.dll");
    if (!hDll) {
        printf("❌ Failed to load Dbaol32.dll\n");
        return 1;
    }
    
    DBOpen_t DBOpen = (DBOpen_t)GetProcAddress(hDll, "DBOpen");
    DBClose_t DBClose = (DBClose_t)GetProcAddress(hDll, "DBClose");
    DBGetInfo_t DBGetInfo = (DBGetInfo_t)GetProcAddress(hDll, "DBGetInfo");
    DBGetLastError_t DBGetLastError = (DBGetLastError_t)GetProcAddress(hDll, "DBGetLastError");
    
    // Get all reading functions
    void* DBExtractRecord = GetProcAddress(hDll, "DBExtractRecord");
    void* DBCopyRecord = GetProcAddress(hDll, "DBCopyRecord");
    void* DBCopyThisRecord = GetProcAddress(hDll, "DBCopyThisRecord");
    void* DBExtractUndeletedRecord = GetProcAddress(hDll, "DBExtractUndeletedRecord");
    
    printf("Available reading functions:\n");
    printf("  DBExtractRecord: %s\n", DBExtractRecord ? "✅" : "❌");
    printf("  DBCopyRecord: %s\n", DBCopyRecord ? "✅" : "❌");
    printf("  DBCopyThisRecord: %s\n", DBCopyThisRecord ? "✅" : "❌");
    printf("  DBExtractUndeletedRecord: %s\n", DBExtractUndeletedRecord ? "✅" : "❌");
    
    // Open the main database with known records
    int dbHandle = DBOpen("golden_tests/main.IDX");
    printf("\nDBOpen(main.IDX): %d\n", dbHandle);
    
    if (dbHandle <= 0) {
        printf("❌ Failed to open main.IDX, trying working_copy.IDX\n");
        dbHandle = DBOpen("working_copy.IDX");
        printf("DBOpen(working_copy.IDX): %d\n", dbHandle);
    }
    
    if (dbHandle <= 0) {
        printf("❌ Failed to open any database\n");
        FreeLibrary(hDll);
        return 1;
    }
    
    // Get database info first
    if (DBGetInfo) {
        char info[512];
        int info_result = DBGetInfo(dbHandle, info);
        printf("DBGetInfo result: %d\n", info_result);
        if (info_result > 0) {
            printf("Database info (first 64 bytes): ");
            for (int i = 0; i < 64 && i < 512; i++) {
                printf("%02x ", (unsigned char)info[i]);
            }
            printf("\n");
        }
    }
    
    // Test all reading functions with both calling conventions
    test_reading_function("DBExtractRecord", DBExtractRecord, dbHandle, 0, 1);         // __stdcall, needs record ID
    test_reading_function("DBExtractRecord", DBExtractRecord, dbHandle, 1, 1);         // __cdecl, needs record ID
    
    test_reading_function("DBCopyRecord", DBCopyRecord, dbHandle, 0, 1);               // __stdcall, needs record ID
    test_reading_function("DBCopyRecord", DBCopyRecord, dbHandle, 1, 1);               // __cdecl, needs record ID
    
    test_reading_function("DBExtractUndeletedRecord", DBExtractUndeletedRecord, dbHandle, 0, 1);  // __stdcall, needs record ID
    test_reading_function("DBExtractUndeletedRecord", DBExtractUndeletedRecord, dbHandle, 1, 1);  // __cdecl, needs record ID
    
    test_reading_function("DBCopyThisRecord", DBCopyThisRecord, dbHandle, 0, 0);       // __stdcall, no record ID
    test_reading_function("DBCopyThisRecord", DBCopyThisRecord, dbHandle, 1, 0);       // __cdecl, no record ID
    
    // Show any error messages
    if (DBGetLastError) {
        const char* error = DBGetLastError();
        if (error && strlen(error) > 0) {
            printf("\nLast error: '%s'\n", error);
        }
    }
    
    printf("\n=== READING TEST SUMMARY ===\n");
    printf("If any reads succeeded, we now know:\n");
    printf("1. The correct calling convention\n");
    printf("2. Valid record ID ranges\n");
    printf("3. Expected output sizes and formats\n");
    printf("4. This can guide our save/update attempts\n");
    
    if (DBClose) DBClose(dbHandle);
    FreeLibrary(hDll);
    return 0;
}