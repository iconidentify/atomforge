/*
 * Test __cdecl calling convention and very simple data
 */
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>

// Test both calling conventions
typedef int (__stdcall *DBOpen_stdcall_t)(const char* filename);
typedef int (__stdcall *DBClose_stdcall_t)(int handle);
typedef int (__stdcall *DBUpdateRecord_stdcall_t)(int handle, int recordId, void* data, int dataSize);
typedef int (__stdcall *DBExtractRecord_stdcall_t)(int handle, int recordId, void* buffer, int* bufferSize);

typedef int (__cdecl *DBUpdateRecord_cdecl_t)(int handle, int recordId, void* data, int dataSize);
typedef int (__cdecl *DBExtractRecord_cdecl_t)(int handle, int recordId, void* buffer, int* bufferSize);

int test_very_simple_update(int dbHandle, void* update_func, void* extract_func, int use_cdecl) {
    printf("\\n=== Testing with very simple data (%s) ===\\n", use_cdecl ? "__cdecl" : "__stdcall");
    
    // Try the simplest possible data - just a few bytes
    char simple_data[] = {0x40, 0x01, 0x01, 0x00};  // FDO-like header
    int simple_size = sizeof(simple_data);
    
    printf("Testing %d-byte minimal data...\\n", simple_size);
    
    int test_record_id = 500000;  // Use a high ID
    int update_result = 0;
    
    if (use_cdecl) {
        update_result = ((DBUpdateRecord_cdecl_t)update_func)(dbHandle, test_record_id, simple_data, simple_size);
    } else {
        update_result = ((DBUpdateRecord_stdcall_t)update_func)(dbHandle, test_record_id, simple_data, simple_size);
    }
    
    printf("DBUpdateRecord result: %d\\n", update_result);
    
    if (update_result > 0) {
        printf("✅ Update succeeded with simple data!\\n");
        
        // Try to extract it
        char extracted[256];
        int extracted_size = sizeof(extracted);
        int extract_result = 0;
        
        if (use_cdecl) {
            extract_result = ((DBExtractRecord_cdecl_t)extract_func)(dbHandle, test_record_id, extracted, &extracted_size);
        } else {
            extract_result = ((DBExtractRecord_stdcall_t)extract_func)(dbHandle, test_record_id, extracted, &extracted_size);
        }
        
        printf("Extract result: %d, size: %d\\n", extract_result, extracted_size);
        
        if (extract_result > 0) {
            printf("🎉 ROUND-TRIP WORKS!\\n");
            printf("Stored %d bytes, extracted %d bytes\\n", simple_size, extracted_size);
            
            printf("Extracted data: ");
            for (int i = 0; i < extracted_size && i < 16; i++) {
                printf("%02x ", (unsigned char)extracted[i]);
            }
            printf("\\n");
            
            return 1;  // Success!
        }
    } else {
        printf("❌ Update failed with %s\\n", use_cdecl ? "__cdecl" : "__stdcall");
    }
    
    return 0;
}

int test_different_record_ids(int dbHandle, void* update_func, int use_cdecl) {
    printf("\\n=== Testing different record ID ranges ===\\n");
    
    char test_data[] = "TEST";
    int test_size = 4;
    
    // Try a range of record IDs to see if any work
    int test_ids[] = {
        0, 1, 2, 3, 4, 5,           // Very low
        100, 101, 102,              // Low
        1000, 1001, 1002,           // Medium
        10000, 10001, 10002,        // High
        100000, 100001,             // Very high
        1000000, 1000001            // Extremely high
    };
    
    int num_tests = sizeof(test_ids) / sizeof(test_ids[0]);
    
    for (int i = 0; i < num_tests; i++) {
        int record_id = test_ids[i];
        int result = 0;
        
        if (use_cdecl) {
            result = ((DBUpdateRecord_cdecl_t)update_func)(dbHandle, record_id, test_data, test_size);
        } else {
            result = ((DBUpdateRecord_stdcall_t)update_func)(dbHandle, record_id, test_data, test_size);
        }
        
        printf("ID %7d: result=%d", record_id, result);
        
        if (result > 0) {
            printf(" ✅ SUCCESS!\\n");
            return record_id;  // Return successful ID
        } else if (result < 0) {
            printf(" (error %d)\\n", result);
        } else {
            printf("\\n");
        }
    }
    
    return -1;  // No success
}

int main() {
    printf("=== Testing __cdecl and Simple Data ===\\n");
    
    HMODULE hDll = LoadLibrary("Dbaol32.dll");
    if (!hDll) {
        printf("❌ Failed to load Dbaol32.dll\\n");
        return 1;
    }
    
    DBOpen_stdcall_t DBOpen = (DBOpen_stdcall_t)GetProcAddress(hDll, "DBOpen");
    DBClose_stdcall_t DBClose = (DBClose_stdcall_t)GetProcAddress(hDll, "DBClose");
    void* DBUpdateRecord = GetProcAddress(hDll, "DBUpdateRecord");
    void* DBExtractRecord = GetProcAddress(hDll, "DBExtractRecord");
    
    if (!DBOpen || !DBUpdateRecord || !DBExtractRecord) {
        printf("❌ Functions not found\\n");
        FreeLibrary(hDll);
        return 1;
    }
    
    // Use our working copy from previous test
    int dbHandle = DBOpen("working_copy.IDX");
    printf("DBOpen result: %d\\n", dbHandle);
    
    if (dbHandle <= 0) {
        printf("❌ Failed to open database\\n");
        FreeLibrary(hDll);
        return 1;
    }
    
    printf("✅ Database opened\\n");
    
    // Test 1: Simple data with __stdcall
    int stdcall_success = test_very_simple_update(dbHandle, DBUpdateRecord, DBExtractRecord, 0);
    
    // Test 2: Simple data with __cdecl  
    int cdecl_success = test_very_simple_update(dbHandle, DBUpdateRecord, DBExtractRecord, 1);
    
    // Test 3: Try different record ID ranges with both calling conventions
    if (!stdcall_success && !cdecl_success) {
        printf("\\n=== Testing Record ID Ranges ===\\n");
        
        printf("Testing __stdcall with different IDs...\\n");
        int working_stdcall_id = test_different_record_ids(dbHandle, DBUpdateRecord, 0);
        
        printf("\\nTesting __cdecl with different IDs...\\n");
        int working_cdecl_id = test_different_record_ids(dbHandle, DBUpdateRecord, 1);
        
        if (working_stdcall_id >= 0) {
            printf("\\n✅ __stdcall works with record ID %d\\n", working_stdcall_id);
        }
        
        if (working_cdecl_id >= 0) {
            printf("\\n✅ __cdecl works with record ID %d\\n", working_cdecl_id);
        }
        
        if (working_stdcall_id < 0 && working_cdecl_id < 0) {
            printf("\\n❌ No working calling convention found\\n");
        }
    }
    
    printf("\\n=== SUMMARY ===\\n");
    printf("Simple __stdcall: %s\\n", stdcall_success ? "✅ WORKS" : "❌ Failed");
    printf("Simple __cdecl: %s\\n", cdecl_success ? "✅ WORKS" : "❌ Failed");
    
    if (stdcall_success || cdecl_success) {
        printf("\\n🎯 SUCCESS! We found a working calling convention!\\n");
        printf("Next: Test with our actual Ada32 data using the working method\\n");
    } else {
        printf("\\n⚠️  Still debugging - may need different approach\\n");
    }
    
    if (DBClose) DBClose(dbHandle);
    FreeLibrary(hDll);
    return 0;
}