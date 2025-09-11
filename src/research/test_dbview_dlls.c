/*
 * Test the DLLs from the Dbview directory
 */
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>

typedef int (__stdcall *DBOpen_t)(const char* filename);
typedef int (__stdcall *DBClose_t)(int handle);
typedef int (__stdcall *DBExtractRecord_t)(int handle, int recordId, void* buffer, int* bufferSize);

int test_dll_version(const char* dll_path) {
    printf("\n=== Testing %s ===\n", dll_path);
    
    HMODULE hDll = LoadLibrary(dll_path);
    if (!hDll) {
        printf("❌ Failed to load %s\n", dll_path);
        return 0;
    }
    
    printf("✅ Loaded %s\n", dll_path);
    
    DBOpen_t DBOpen = (DBOpen_t)GetProcAddress(hDll, "DBOpen");
    DBClose_t DBClose = (DBClose_t)GetProcAddress(hDll, "DBClose");
    DBExtractRecord_t DBExtractRecord = (DBExtractRecord_t)GetProcAddress(hDll, "DBExtractRecord");
    
    printf("Functions: DBOpen=%s, DBClose=%s, DBExtractRecord=%s\n",
           DBOpen ? "✅" : "❌",
           DBClose ? "✅" : "❌", 
           DBExtractRecord ? "✅" : "❌");
    
    if (!DBOpen || !DBExtractRecord) {
        printf("Required functions missing\n");
        FreeLibrary(hDll);
        return 0;
    }
    
    // Try opening database
    int dbHandle = DBOpen("golden_tests/main.IDX");
    printf("DBOpen result: %d\n", dbHandle);
    
    if (dbHandle <= 0) {
        printf("❌ Failed to open database\n");
        FreeLibrary(hDll);
        return 0;
    }
    
    printf("✅ Database opened successfully\n");
    
    // Quick test of a few record IDs
    int test_ids[] = {1, 2, 3, 105, 1000};
    for (int i = 0; i < 5; i++) {
        char buffer[256];
        int buffer_size = sizeof(buffer);
        
        int result = DBExtractRecord(dbHandle, test_ids[i], buffer, &buffer_size);
        printf("  ID %d: result=%d, size=%d", test_ids[i], result, buffer_size);
        
        if (result > 0 && buffer_size > 0) {
            printf(" ✅ SUCCESS!");
            printf(" bytes: ");
            for (int j = 0; j < 8 && j < buffer_size; j++) {
                printf("%02x ", (unsigned char)buffer[j]);
            }
            
            if (buffer_size >= 2 && (unsigned char)buffer[0] == 0x40 && (unsigned char)buffer[1] == 0x01) {
                printf(" FDO!");
            }
        }
        printf("\n");
    }
    
    if (DBClose) DBClose(dbHandle);
    FreeLibrary(hDll);
    return 1;
}

int explore_all_db_functions() {
    printf("=== Exploring All Database-Related Functions ===\n");
    
    const char* dll_paths[] = {
        "Dbaol32.dll",         // Main directory
        "Dbview/Dbaol32.dll"   // DbView directory
    };
    
    for (int i = 0; i < 2; i++) {
        HMODULE hDll = LoadLibrary(dll_paths[i]);
        if (hDll) {
            printf("\n--- Functions in %s ---\n", dll_paths[i]);
            
            // Test many possible function names
            const char* func_names[] = {
                "DBOpen", "DBClose", "DBExtractRecord", "DBAddRecord", "DBUpdateRecord",
                "DBGetRecord", "DBReadRecord", "DBFetchRecord", "DBRetrieveRecord",
                "DBGetRecordByIndex", "DBGetRecordData", "DBGetData",
                "DBEnum", "DBEnumFirst", "DBEnumNext", "DBFirst", "DBNext",
                "DBFind", "DBSeek", "DBSearch", "DBQuery",
                "DBGetCount", "DBGetRecordCount", "DBCount",
                "DBGetInfo", "DBInfo", "DBStatus", "DBGetStatus",
                "DBCreate", "DBCreateRecord", "DBInsert", "DBInsertRecord",
                "DBDelete", "DBDeleteRecord", "DBRemove", "DBRemoveRecord"
            };
            
            int num_funcs = sizeof(func_names) / sizeof(func_names[0]);
            int found_count = 0;
            
            for (int j = 0; j < num_funcs; j++) {
                void* func = GetProcAddress(hDll, func_names[j]);
                if (func) {
                    printf("  ✅ %s\n", func_names[j]);
                    found_count++;
                }
            }
            
            printf("Total functions found: %d/%d\n", found_count, num_funcs);
            FreeLibrary(hDll);
        }
    }
    
    return 0;
}

int main() {
    printf("=== Testing Different Database DLL Versions ===\n");
    
    // First explore what functions are available
    explore_all_db_functions();
    
    // Test each DLL version
    test_dll_version("Dbaol32.dll");
    test_dll_version("Dbview/Dbaol32.dll");
    
    // Also try opening the database from the Dbview directory
    printf("\n=== Testing with Dbview database files ===\n");
    
    // Check if there are database files in the Dbview directory
    HMODULE hDll = LoadLibrary("Dbaol32.dll");
    if (hDll) {
        DBOpen_t DBOpen = (DBOpen_t)GetProcAddress(hDll, "DBOpen");
        if (DBOpen) {
            printf("Testing Dbview directory files...\n");
            
            // Try some common database file names
            const char* db_files[] = {
                "Dbview/main.idx",
                "Dbview/data.idx", 
                "Dbview/database.idx",
                "Dbview/db.idx"
            };
            
            for (int i = 0; i < 4; i++) {
                printf("Trying %s: ", db_files[i]);
                int handle = DBOpen(db_files[i]);
                printf("result=%d\n", handle);
                
                if (handle > 0) {
                    printf("✅ Opened %s successfully!\n", db_files[i]);
                    // We could test extraction here too
                }
            }
        }
        FreeLibrary(hDll);
    }
    
    return 0;
}