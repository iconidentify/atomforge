/*
 * Final systematic test of all database approaches
 */
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>

typedef int (__stdcall *DBOpen_t)(const char* filename);
typedef int (__stdcall *DBClose_t)(int handle);
typedef int (__stdcall *DBAddRecord_t)(int handle, void* data, int dataSize, int* recordId);
typedef int (__stdcall *DBUpdateRecord_t)(int handle, int recordId, void* data, int dataSize);
typedef int (__stdcall *DBExtractRecord_t)(int handle, int recordId, void* buffer, int* bufferSize);
typedef int (__stdcall *DBGetInfo_t)(int handle, void* info);
typedef int (__stdcall *DBCreate_t)(const char* filename);
typedef int (__stdcall *DBDeleteRecord_t)(int handle, int recordId);
typedef const char* (__stdcall *DBGetLastError_t)(void);

int test_all_possible_signatures(int dbHandle, void* func, const char* func_name) {
    printf("\\n=== Testing %s with all possible signatures ===\\n", func_name);
    
    char test_data[] = "TEST";
    int test_size = 4;
    int record_id = 777777;
    
    // Signature 1: (handle, recordId, data, size)
    printf("Sig 1 (handle, recordId, data, size): ");
    int result1 = ((int (__stdcall *)(int, int, void*, int))func)(dbHandle, record_id, test_data, test_size);
    printf("%d\\n", result1);
    
    // Signature 2: (handle, data, size, recordId*)
    printf("Sig 2 (handle, data, size, recordId*): ");
    int new_id = 0;
    int result2 = ((int (__stdcall *)(int, void*, int, int*))func)(dbHandle, test_data, test_size, &new_id);
    printf("%d (newID=%d)\\n", result2, new_id);
    
    // Signature 3: (handle, size, data, recordId)
    printf("Sig 3 (handle, size, data, recordId): ");
    int result3 = ((int (__stdcall *)(int, int, void*, int))func)(dbHandle, test_size, test_data, record_id);
    printf("%d\\n", result3);
    
    // Signature 4: (handle, recordId, size, data)
    printf("Sig 4 (handle, recordId, size, data): ");
    int result4 = ((int (__stdcall *)(int, int, int, void*))func)(dbHandle, record_id, test_size, test_data);
    printf("%d\\n", result4);
    
    // Check for any success
    if (result1 > 0 || result2 > 0 || result3 > 0 || result4 > 0) {
        printf("✅ Found working signature!\\n");
        return 1;
    }
    
    return 0;
}

int test_database_prerequisites(int dbHandle, void* getinfo_func) {
    printf("\\n=== Testing Database Prerequisites ===\\n");
    
    if (getinfo_func) {
        // Try to get detailed database info
        char info_buffer[1024];
        memset(info_buffer, 0, sizeof(info_buffer));
        
        int info_result = ((DBGetInfo_t)getinfo_func)(dbHandle, info_buffer);
        printf("DBGetInfo result: %d\\n", info_result);
        
        if (info_result > 0) {
            printf("Database info: '%s'\\n", info_buffer);
            
            // Print as hex to see structure
            printf("Info hex: ");
            for (int i = 0; i < 32; i++) {
                printf("%02x ", (unsigned char)info_buffer[i]);
            }
            printf("\\n");
        }
        
        // Try different info buffer sizes
        for (int size = 4; size <= 64; size *= 2) {
            char* small_buffer = malloc(size);
            memset(small_buffer, 0, size);
            
            int small_result = ((DBGetInfo_t)getinfo_func)(dbHandle, small_buffer);
            if (small_result > 0 && small_result != info_result) {
                printf("Different result with %d-byte buffer: %d\\n", size, small_result);
            }
            free(small_buffer);
        }
    }
    
    return 0;
}

int test_creating_records_from_scratch(void* create_func, void* open_func, void* add_func) {
    printf("\\n=== Testing Record Creation from Scratch ===\\n");
    
    if (!create_func || !open_func || !add_func) {
        printf("Required functions not available\\n");
        return 0;
    }
    
    const char* fresh_db = "fresh_test.idx";
    remove(fresh_db);
    
    printf("Creating fresh database: %s\\n", fresh_db);
    int create_result = ((DBCreate_t)create_func)(fresh_db);
    printf("DBCreate result: %d\\n", create_result);
    
    if (create_result <= 0) {
        printf("❌ Failed to create fresh database\\n");
        return 0;
    }
    
    int fresh_handle = ((DBOpen_t)open_func)(fresh_db);
    printf("DBOpen fresh result: %d\\n", fresh_handle);
    
    if (fresh_handle <= 0) {
        printf("❌ Failed to open fresh database\\n");
        return 0;
    }
    
    printf("✅ Fresh database ready\\n");
    
    // Try adding to the fresh database with different approaches
    char simple_data[] = "FIRST";
    int simple_size = 5;
    
    // Try different ways to add the first record
    printf("\\nTrying to add first record...\\n");
    
    // Method 1: Traditional add
    int record_id = 0;
    int add1 = ((int (__stdcall *)(int, void*, int, int*))add_func)(fresh_handle, simple_data, simple_size, &record_id);
    printf("Add method 1: result=%d, recordId=%d\\n", add1, record_id);
    
    // Method 2: Pre-set record ID  
    record_id = 1;
    int add2 = ((int (__stdcall *)(int, void*, int, int*))add_func)(fresh_handle, simple_data, simple_size, &record_id);
    printf("Add method 2: result=%d, recordId=%d\\n", add2, record_id);
    
    // Method 3: Different parameter order
    int add3 = ((int (__stdcall *)(int, int*, void*, int))add_func)(fresh_handle, &record_id, simple_data, simple_size);
    printf("Add method 3: result=%d, recordId=%d\\n", add3, record_id);
    
    if (add1 > 0 || add2 > 0 || add3 > 0) {
        printf("✅ Successfully added record to fresh database!\\n");
        return 1;
    } else {
        printf("❌ Failed to add record even to fresh database\\n");
    }
    
    return 0;
}

int main() {
    printf("=== Final Systematic Database Test ===\\n");
    
    HMODULE hDll = LoadLibrary("Dbaol32.dll");
    if (!hDll) {
        printf("❌ Failed to load Dbaol32.dll\\n");
        return 1;
    }
    
    // Get all available functions
    void* functions[] = {
        GetProcAddress(hDll, "DBOpen"),
        GetProcAddress(hDll, "DBClose"), 
        GetProcAddress(hDll, "DBAddRecord"),
        GetProcAddress(hDll, "DBUpdateRecord"),
        GetProcAddress(hDll, "DBExtractRecord"),
        GetProcAddress(hDll, "DBGetInfo"),
        GetProcAddress(hDll, "DBCreate"),
        GetProcAddress(hDll, "DBDeleteRecord"),
        GetProcAddress(hDll, "DBGetLastError")
    };
    
    const char* func_names[] = {
        "DBOpen", "DBClose", "DBAddRecord", "DBUpdateRecord", 
        "DBExtractRecord", "DBGetInfo", "DBCreate", "DBDeleteRecord", "DBGetLastError"
    };
    
    printf("Available functions:\\n");
    for (int i = 0; i < 9; i++) {
        printf("  %s: %s\\n", func_names[i], functions[i] ? "✅" : "❌");
    }
    
    if (!functions[0] || !functions[2] || !functions[3]) {  // DBOpen, DBAddRecord, DBUpdateRecord
        printf("❌ Essential functions missing\\n");
        FreeLibrary(hDll);
        return 1;
    }
    
    // Test 1: Prerequisites with existing database
    int dbHandle = ((DBOpen_t)functions[0])("working_copy.IDX");
    printf("\\nDBOpen existing result: %d\\n", dbHandle);
    
    if (dbHandle > 0) {
        test_database_prerequisites(dbHandle, functions[5]);  // DBGetInfo
        
        // Test all function signatures
        test_all_possible_signatures(dbHandle, functions[2], "DBAddRecord");
        test_all_possible_signatures(dbHandle, functions[3], "DBUpdateRecord");
        
        if (functions[1]) ((DBClose_t)functions[1])(dbHandle);  // DBClose
    }
    
    // Test 2: Fresh database creation
    test_creating_records_from_scratch(functions[6], functions[0], functions[2]);  // DBCreate, DBOpen, DBAddRecord
    
    printf("\\n=== CONCLUSION ===\\n");
    printf("If none of these approaches worked, the issue might be:\\n");
    printf("1. Function signatures completely different than expected\\n");
    printf("2. Database file format incompatibility\\n");
    printf("3. Missing initialization or authentication steps\\n");
    printf("4. Wine compatibility issues with this specific DLL\\n");
    
    FreeLibrary(hDll);
    return 0;
}