/*
 * Test database setup functions before attempting add/update
 */
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>

typedef int (__stdcall *DBOpen_t)(const char* filename);
typedef int (__stdcall *DBClose_t)(int handle);
typedef int (__stdcall *DBCreate_t)(const char* filename);
typedef int (__stdcall *DBGetInfo_t)(int handle, void* info);

// Setup functions
typedef int (__stdcall *DBSetVersion_t)(int handle, int version);
typedef int (__stdcall *DBSetPurge_t)(int handle, int purge);
typedef int (__stdcall *DBSetMaxSize_t)(int handle, int maxSize);
typedef int (__stdcall *DBSetMinSize_t)(int handle, int minSize);
typedef int (__stdcall *DBCopyResultSize_t)(int handle, int* size);

// Record functions (try both calling conventions)
typedef int (__stdcall *DBAddRecord_stdcall_t)(int handle, void* data, int dataSize, int* recordId);
typedef int (__stdcall *DBUpdateRecord_stdcall_t)(int handle, int recordId, void* data, int dataSize);
typedef int (__cdecl *DBAddRecord_cdecl_t)(int handle, void* data, int dataSize, int* recordId);
typedef int (__cdecl *DBUpdateRecord_cdecl_t)(int handle, int recordId, void* data, int dataSize);

typedef const char* (__stdcall *DBGetLastError_t)(void);

int test_setup_sequence(int dbHandle, void* setVersion, void* setPurge, void* setMaxSize, void* setMinSize, void* copyResultSize) {
    printf("\n=== Testing Database Setup Sequence ===\n");
    
    // Step 1: Set version
    if (setVersion) {
        int version_result = ((DBSetVersion_t)setVersion)(dbHandle, 1);
        printf("DBSetVersion(1): %d\n", version_result);
        
        // Try version 2 as well
        version_result = ((DBSetVersion_t)setVersion)(dbHandle, 2);
        printf("DBSetVersion(2): %d\n", version_result);
    }
    
    // Step 2: Set purge mode
    if (setPurge) {
        int purge_result = ((DBSetPurge_t)setPurge)(dbHandle, 0);  // Disable purging
        printf("DBSetPurge(0): %d\n", purge_result);
        
        purge_result = ((DBSetPurge_t)setPurge)(dbHandle, 1);  // Enable purging
        printf("DBSetPurge(1): %d\n", purge_result);
    }
    
    // Step 3: Set size limits
    if (setMaxSize && setMinSize) {
        int max_result = ((DBSetMaxSize_t)setMaxSize)(dbHandle, 1024);  // 1KB max
        printf("DBSetMaxSize(1024): %d\n", max_result);
        
        int min_result = ((DBSetMinSize_t)setMinSize)(dbHandle, 64);    // 64B min
        printf("DBSetMinSize(64): %d\n", min_result);
    }
    
    // Step 4: Check result size
    if (copyResultSize) {
        int result_size = 0;
        int size_result = ((DBCopyResultSize_t)copyResultSize)(dbHandle, &result_size);
        printf("DBCopyResultSize: %d, size=%d\n", size_result, result_size);
    }
    
    printf("Setup sequence completed\n");
    return 1;
}

int test_after_setup(int dbHandle, void* addRecord, void* updateRecord) {
    printf("\n=== Testing Add/Update After Setup ===\n");
    
    char test_data[] = "SETUP";
    int test_size = strlen(test_data);
    
    // Test 1: Try __stdcall DBAddRecord
    printf("Testing __stdcall DBAddRecord...\n");
    int record_id = 0;
    int add_stdcall = ((DBAddRecord_stdcall_t)addRecord)(dbHandle, test_data, test_size, &record_id);
    printf("DBAddRecord (__stdcall): result=%d, recordId=%d\n", add_stdcall, record_id);
    
    // Test 2: Try __cdecl DBAddRecord
    printf("Testing __cdecl DBAddRecord...\n");
    record_id = 0;
    int add_cdecl = ((DBAddRecord_cdecl_t)addRecord)(dbHandle, test_data, test_size, &record_id);
    printf("DBAddRecord (__cdecl): result=%d, recordId=%d\n", add_cdecl, record_id);
    
    // Test 3: Try __stdcall DBUpdateRecord with specific IDs
    printf("Testing __stdcall DBUpdateRecord...\n");
    int test_ids[] = {1, 2, 10, 100, 1000, 10000};
    for (int i = 0; i < 6; i++) {
        int id = test_ids[i];
        int update_stdcall = ((DBUpdateRecord_stdcall_t)updateRecord)(dbHandle, id, test_data, test_size);
        printf("DBUpdateRecord (__stdcall, ID %d): %d\n", id, update_stdcall);
        if (update_stdcall > 0) {
            printf("✅ SUCCESS with __stdcall at ID %d!\n", id);
            return id;
        }
    }
    
    // Test 4: Try __cdecl DBUpdateRecord with specific IDs
    printf("Testing __cdecl DBUpdateRecord...\n");
    for (int i = 0; i < 6; i++) {
        int id = test_ids[i];
        int update_cdecl = ((DBUpdateRecord_cdecl_t)updateRecord)(dbHandle, id, test_data, test_size);
        printf("DBUpdateRecord (__cdecl, ID %d): %d\n", id, update_cdecl);
        if (update_cdecl > 0) {
            printf("✅ SUCCESS with __cdecl at ID %d!\n", id);
            return id;
        }
    }
    
    return -1;  // No success
}

int main() {
    printf("=== Database Setup and Configuration Test ===\n");
    
    HMODULE hDll = LoadLibrary("Dbaol32.dll");
    if (!hDll) {
        printf("❌ Failed to load Dbaol32.dll\n");
        return 1;
    }
    
    // Get basic functions
    DBOpen_t DBOpen = (DBOpen_t)GetProcAddress(hDll, "DBOpen");
    DBClose_t DBClose = (DBClose_t)GetProcAddress(hDll, "DBClose");
    DBCreate_t DBCreate = (DBCreate_t)GetProcAddress(hDll, "DBCreate");
    DBGetInfo_t DBGetInfo = (DBGetInfo_t)GetProcAddress(hDll, "DBGetInfo");
    DBGetLastError_t DBGetLastError = (DBGetLastError_t)GetProcAddress(hDll, "DBGetLastError");
    
    // Get setup functions
    void* DBSetVersion = GetProcAddress(hDll, "DBSetVersion");
    void* DBSetPurge = GetProcAddress(hDll, "DBSetPurge");
    void* DBSetMaxSize = GetProcAddress(hDll, "DBSetMaxSize");
    void* DBSetMinSize = GetProcAddress(hDll, "DBSetMinSize");
    void* DBCopyResultSize = GetProcAddress(hDll, "DBCopyResultSize");
    
    // Get record functions
    void* DBAddRecord = GetProcAddress(hDll, "DBAddRecord");
    void* DBUpdateRecord = GetProcAddress(hDll, "DBUpdateRecord");
    
    printf("Setup functions available:\n");
    printf("  DBSetVersion: %s\n", DBSetVersion ? "✅" : "❌");
    printf("  DBSetPurge: %s\n", DBSetPurge ? "✅" : "❌");
    printf("  DBSetMaxSize: %s\n", DBSetMaxSize ? "✅" : "❌");
    printf("  DBSetMinSize: %s\n", DBSetMinSize ? "✅" : "❌");
    printf("  DBCopyResultSize: %s\n", DBCopyResultSize ? "✅" : "❌");
    
    // Test 1: Open existing database and setup
    int dbHandle = DBOpen("working_copy.IDX");
    printf("\nDBOpen(working_copy.IDX): %d\n", dbHandle);
    
    if (dbHandle > 0) {
        // Get initial database info
        if (DBGetInfo) {
            char info[256];
            int info_result = DBGetInfo(dbHandle, info);
            printf("Initial DBGetInfo: %d\n", info_result);
        }
        
        // Run setup sequence
        test_setup_sequence(dbHandle, DBSetVersion, DBSetPurge, DBSetMaxSize, DBSetMinSize, DBCopyResultSize);
        
        // Test add/update after setup
        int working_id = test_after_setup(dbHandle, DBAddRecord, DBUpdateRecord);
        
        if (working_id >= 0) {
            printf("\n🎉 BREAKTHROUGH! Working record ID: %d\n", working_id);
        } else {
            printf("\n❌ Still no working add/update operations\n");
        }
        
        // Show any errors
        if (DBGetLastError) {
            const char* error = DBGetLastError();
            if (error && strlen(error) > 0) {
                printf("Last error: '%s'\n", error);
            }
        }
        
        DBClose(dbHandle);
    }
    
    // Test 2: Try with fresh database
    printf("\n=== Testing with Fresh Database ===\n");
    const char* fresh_db = "fresh_setup_test.idx";
    remove(fresh_db);
    
    if (DBCreate) {
        int create_result = DBCreate(fresh_db);
        printf("DBCreate(%s): %d\n", fresh_db, create_result);
        
        if (create_result > 0) {
            int fresh_handle = DBOpen(fresh_db);
            printf("DBOpen(fresh): %d\n", fresh_handle);
            
            if (fresh_handle > 0) {
                // Setup fresh database
                test_setup_sequence(fresh_handle, DBSetVersion, DBSetPurge, DBSetMaxSize, DBSetMinSize, DBCopyResultSize);
                
                // Test on fresh database
                int fresh_working_id = test_after_setup(fresh_handle, DBAddRecord, DBUpdateRecord);
                
                if (fresh_working_id >= 0) {
                    printf("\n🎯 FRESH DATABASE SUCCESS! ID: %d\n", fresh_working_id);
                }
                
                DBClose(fresh_handle);
            }
        }
    }
    
    FreeLibrary(hDll);
    return 0;
}