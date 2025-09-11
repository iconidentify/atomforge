/*
 * Extensive probing of database methods - try EVERY possible calling pattern
 */
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>

typedef int (__stdcall *DBOpen_t)(const char* filename);
typedef int (__stdcall *DBClose_t)(int handle);
typedef int (__stdcall *DBCreate_t)(const char* filename);

void test_extract_signatures(void* func, int dbHandle, const char* func_name) {
    printf("\n=== Extensive Testing: %s ===\n", func_name);
    
    if (!func) {
        printf("❌ Function not available\n");
        return;
    }
    
    char buffer[2048];
    int buffer_size;
    int successful_calls = 0;
    
    // Test various record IDs and parameter combinations
    int test_ids[] = {0, 1, 2, 3, 4, 5, 10, 32, 50, 100, 105, 106, 117, 200, 500, 1000};
    int num_ids = sizeof(test_ids) / sizeof(test_ids[0]);
    
    for (int i = 0; i < num_ids; i++) {
        int record_id = test_ids[i];
        
        // Signature 1: __stdcall (handle, recordId, buffer, bufferSize*)
        buffer_size = sizeof(buffer);
        memset(buffer, 0xCC, sizeof(buffer)); // Fill with pattern to detect changes
        int result1 = ((int (__stdcall *)(int, int, void*, int*))func)(dbHandle, record_id, buffer, &buffer_size);
        
        if (result1 != 0 || buffer_size != sizeof(buffer) || buffer[0] != (char)0xCC) {
            printf("ID %d Sig1 (__stdcall): result=%d, size=%d, buffer[0]=0x%02x\n", 
                   record_id, result1, buffer_size, (unsigned char)buffer[0]);
            if (result1 > 0 && buffer_size > 0 && buffer_size < 2000) {
                successful_calls++;
                printf("  ✅ SUCCESS! Data: ");
                for (int j = 0; j < 16 && j < buffer_size; j++) {
                    printf("%02x ", (unsigned char)buffer[j]);
                }
                printf("\n");
            }
        }
        
        // Signature 2: __cdecl (handle, recordId, buffer, bufferSize*)
        buffer_size = sizeof(buffer);
        memset(buffer, 0xCC, sizeof(buffer));
        int result2 = ((int (__cdecl *)(int, int, void*, int*))func)(dbHandle, record_id, buffer, &buffer_size);
        
        if (result2 != 0 || buffer_size != sizeof(buffer) || buffer[0] != (char)0xCC) {
            printf("ID %d Sig2 (__cdecl): result=%d, size=%d, buffer[0]=0x%02x\n", 
                   record_id, result2, buffer_size, (unsigned char)buffer[0]);
            if (result2 > 0 && buffer_size > 0 && buffer_size < 2000) {
                successful_calls++;
            }
        }
        
        // Signature 3: Different parameter order (handle, buffer, bufferSize*, recordId)
        buffer_size = sizeof(buffer);
        memset(buffer, 0xCC, sizeof(buffer));
        int result3 = ((int (__stdcall *)(int, void*, int*, int))func)(dbHandle, buffer, &buffer_size, record_id);
        
        if (result3 != 0 || buffer_size != sizeof(buffer) || buffer[0] != (char)0xCC) {
            printf("ID %d Sig3 (reorder): result=%d, size=%d, buffer[0]=0x%02x\n", 
                   record_id, result3, buffer_size, (unsigned char)buffer[0]);
        }
        
        // Signature 4: Size as value not pointer (handle, recordId, buffer, bufferSize)
        buffer_size = sizeof(buffer);
        memset(buffer, 0xCC, sizeof(buffer));
        int result4 = ((int (__stdcall *)(int, int, void*, int))func)(dbHandle, record_id, buffer, buffer_size);
        
        if (result4 != 0 || buffer[0] != (char)0xCC) {
            printf("ID %d Sig4 (size val): result=%d, buffer[0]=0x%02x\n", 
                   record_id, result4, (unsigned char)buffer[0]);
        }
        
        // Signature 5: Additional parameter (handle, recordId, buffer, bufferSize*, flags)
        buffer_size = sizeof(buffer);
        memset(buffer, 0xCC, sizeof(buffer));
        int result5 = ((int (__stdcall *)(int, int, void*, int*, int))func)(dbHandle, record_id, buffer, &buffer_size, 0);
        
        if (result5 != 0 || buffer_size != sizeof(buffer) || buffer[0] != (char)0xCC) {
            printf("ID %d Sig5 (w/flags): result=%d, size=%d, buffer[0]=0x%02x\n", 
                   record_id, result5, buffer_size, (unsigned char)buffer[0]);
        }
    }
    
    printf("Total successful calls for %s: %d\n", func_name, successful_calls);
}

void test_update_signatures(void* func, int dbHandle, const char* func_name) {
    printf("\n=== Extensive Testing: %s ===\n", func_name);
    
    if (!func) {
        printf("❌ Function not available\n");
        return;
    }
    
    char test_data[] = "PROBE";
    int test_size = 5;
    int successful_calls = 0;
    
    // Test with various record IDs
    int test_ids[] = {0, 1, 2, 3, 4, 5, 10, 100, 1000, 999999};
    int num_ids = sizeof(test_ids) / sizeof(test_ids[0]);
    
    for (int i = 0; i < num_ids; i++) {
        int record_id = test_ids[i];
        
        // Signature 1: __stdcall (handle, recordId, data, dataSize)
        int result1 = ((int (__stdcall *)(int, int, void*, int))func)(dbHandle, record_id, test_data, test_size);
        if (result1 != 0) {
            printf("ID %d Sig1 (__stdcall): result=%d\n", record_id, result1);
            if (result1 > 0) successful_calls++;
        }
        
        // Signature 2: __cdecl (handle, recordId, data, dataSize)
        int result2 = ((int (__cdecl *)(int, int, void*, int))func)(dbHandle, record_id, test_data, test_size);
        if (result2 != 0) {
            printf("ID %d Sig2 (__cdecl): result=%d\n", record_id, result2);
            if (result2 > 0) successful_calls++;
        }
        
        // Signature 3: Different order (handle, data, dataSize, recordId)
        int result3 = ((int (__stdcall *)(int, void*, int, int))func)(dbHandle, test_data, test_size, record_id);
        if (result3 != 0) {
            printf("ID %d Sig3 (reorder): result=%d\n", record_id, result3);
            if (result3 > 0) successful_calls++;
        }
        
        // Signature 4: Size as pointer (handle, recordId, data, dataSize*)
        int size_param = test_size;
        int result4 = ((int (__stdcall *)(int, int, void*, int*))func)(dbHandle, record_id, test_data, &size_param);
        if (result4 != 0 || size_param != test_size) {
            printf("ID %d Sig4 (size ptr): result=%d, size after=%d\n", record_id, result4, size_param);
            if (result4 > 0) successful_calls++;
        }
        
        // Signature 5: With flags (handle, recordId, data, dataSize, flags)
        int result5 = ((int (__stdcall *)(int, int, void*, int, int))func)(dbHandle, record_id, test_data, test_size, 0);
        if (result5 != 0) {
            printf("ID %d Sig5 (w/flags): result=%d\n", record_id, result5);
            if (result5 > 0) successful_calls++;
        }
        
        // Signature 6: Different flags
        int result6 = ((int (__stdcall *)(int, int, void*, int, int))func)(dbHandle, record_id, test_data, test_size, 1);
        if (result6 != 0) {
            printf("ID %d Sig6 (flags=1): result=%d\n", record_id, result6);
            if (result6 > 0) successful_calls++;
        }
    }
    
    printf("Total successful calls for %s: %d\n", func_name, successful_calls);
}

void test_add_signatures(void* func, int dbHandle, const char* func_name) {
    printf("\n=== Extensive Testing: %s ===\n", func_name);
    
    if (!func) {
        printf("❌ Function not available\n");
        return;
    }
    
    char test_data[] = "ADD_TEST";
    int test_size = 8;
    int successful_calls = 0;
    
    // Signature 1: (handle, data, dataSize, recordId*)
    int new_id = 0;
    int result1 = ((int (__stdcall *)(int, void*, int, int*))func)(dbHandle, test_data, test_size, &new_id);
    if (result1 != 0 || new_id != 0) {
        printf("Sig1: result=%d, newId=%d\n", result1, new_id);
        if (result1 > 0) successful_calls++;
    }
    
    // Signature 2: __cdecl (handle, data, dataSize, recordId*)
    new_id = 0;
    int result2 = ((int (__cdecl *)(int, void*, int, int*))func)(dbHandle, test_data, test_size, &new_id);
    if (result2 != 0 || new_id != 0) {
        printf("Sig2 (__cdecl): result=%d, newId=%d\n", result2, new_id);
        if (result2 > 0) successful_calls++;
    }
    
    // Signature 3: Pre-specified ID (handle, recordId, data, dataSize)
    int preset_id = 50000;
    int result3 = ((int (__stdcall *)(int, int, void*, int))func)(dbHandle, preset_id, test_data, test_size);
    if (result3 != 0) {
        printf("Sig3 (preset ID %d): result=%d\n", preset_id, result3);
        if (result3 > 0) successful_calls++;
    }
    
    // Signature 4: Different parameter order (recordId*, handle, data, dataSize)
    new_id = 0;
    int result4 = ((int (__stdcall *)(int*, int, void*, int))func)(&new_id, dbHandle, test_data, test_size);
    if (result4 != 0 || new_id != 0) {
        printf("Sig4 (reorder): result=%d, newId=%d\n", result4, new_id);
        if (result4 > 0) successful_calls++;
    }
    
    printf("Total successful calls for %s: %d\n", func_name, successful_calls);
}

int main() {
    printf("=== EXTENSIVE DATABASE FUNCTION PROBING ===\n");
    
    HMODULE hDll = LoadLibrary("Dbaol32.dll");
    if (!hDll) {
        printf("❌ Failed to load Dbaol32.dll\n");
        return 1;
    }
    
    DBOpen_t DBOpen = (DBOpen_t)GetProcAddress(hDll, "DBOpen");
    DBClose_t DBClose = (DBClose_t)GetProcAddress(hDll, "DBClose");
    DBCreate_t DBCreate = (DBCreate_t)GetProcAddress(hDll, "DBCreate");
    
    void* DBExtractRecord = GetProcAddress(hDll, "DBExtractRecord");
    void* DBUpdateRecord = GetProcAddress(hDll, "DBUpdateRecord");
    void* DBAddRecord = GetProcAddress(hDll, "DBAddRecord");
    void* DBCopyRecord = GetProcAddress(hDll, "DBCopyRecord");
    void* DBCopyThisRecord = GetProcAddress(hDll, "DBCopyThisRecord");
    
    printf("All functions loaded successfully\n");
    
    // Test 1: With existing main.IDX database
    printf("\n🔍 TESTING WITH EXISTING main.IDX DATABASE\n");
    int mainHandle = DBOpen("golden_tests/main.IDX");
    printf("DBOpen(main.IDX): %d\n", mainHandle);
    
    if (mainHandle > 0) {
        test_extract_signatures(DBExtractRecord, mainHandle, "DBExtractRecord");
        test_extract_signatures(DBCopyRecord, mainHandle, "DBCopyRecord");
        test_extract_signatures(DBCopyThisRecord, mainHandle, "DBCopyThisRecord");
        
        test_update_signatures(DBUpdateRecord, mainHandle, "DBUpdateRecord");
        test_add_signatures(DBAddRecord, mainHandle, "DBAddRecord");
        
        DBClose(mainHandle);
    }
    
    // Test 2: With fresh database
    printf("\n\n🔍 TESTING WITH FRESH DATABASE\n");
    const char* fresh_db = "extensive_probe.idx";
    remove(fresh_db);
    
    int create_result = DBCreate(fresh_db);
    printf("DBCreate result: %d\n", create_result);
    
    if (create_result > 0) {
        int freshHandle = DBOpen(fresh_db);
        printf("DBOpen(fresh): %d\n", freshHandle);
        
        if (freshHandle > 0) {
            test_add_signatures(DBAddRecord, freshHandle, "DBAddRecord (fresh DB)");
            test_update_signatures(DBUpdateRecord, freshHandle, "DBUpdateRecord (fresh DB)");
            
            DBClose(freshHandle);
        }
        
        remove(fresh_db);
    }
    
    // Test 3: With working_copy.IDX
    printf("\n\n🔍 TESTING WITH working_copy.IDX\n");
    int workingHandle = DBOpen("working_copy.IDX");
    printf("DBOpen(working_copy.IDX): %d\n", workingHandle);
    
    if (workingHandle > 0) {
        test_extract_signatures(DBExtractRecord, workingHandle, "DBExtractRecord (working_copy)");
        test_update_signatures(DBUpdateRecord, workingHandle, "DBUpdateRecord (working_copy)");
        
        DBClose(workingHandle);
    }
    
    printf("\n=== PROBING COMPLETE ===\n");
    printf("If ANY function calls showed non-zero results or buffer changes,\n");
    printf("those indicate the correct calling patterns to investigate further.\n");
    
    FreeLibrary(hDll);
    return 0;
}