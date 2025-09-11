/*
 * Debug database functions systematically
 */
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>

typedef int (__stdcall *DBOpen_t)(const char* filename);
typedef int (__stdcall *DBClose_t)(int handle);
typedef int (__stdcall *DBExtractRecord_t)(int handle, int recordId, void* buffer, int* bufferSize);
typedef const char* (__stdcall *DBGetLastError_t)(void);

// Alternative signatures to test
typedef int (__stdcall *DBExtractRecordAlt1_t)(int handle, void* buffer, int* bufferSize, int recordId);
typedef int (__stdcall *DBExtractRecordAlt2_t)(int handle, int recordId, void* buffer, int bufferSize);
typedef int (__stdcall *DBExtractRecordAlt3_t)(int handle, int recordId, int bufferSize, void* buffer);

int test_record_extraction_patterns(int dbHandle, void* extract_func, const char* func_name, int test_type) {
    printf("\n=== Testing %s (type %d) ===\n", func_name, test_type);
    
    char buffer[1024];
    int buffer_size = sizeof(buffer);
    int result = 0;
    
    // Test with several different record IDs
    int test_ids[] = {0, 1, 2, 3, 105, 106, 117, 1000, 10000};
    int num_ids = sizeof(test_ids) / sizeof(test_ids[0]);
    
    for (int i = 0; i < num_ids; i++) {
        int record_id = test_ids[i];
        buffer_size = sizeof(buffer);
        memset(buffer, 0, sizeof(buffer));
        
        switch (test_type) {
            case 1:  // Standard: handle, recordId, buffer, bufferSize
                result = ((DBExtractRecord_t)extract_func)(dbHandle, record_id, buffer, &buffer_size);
                break;
            case 2:  // Alt1: handle, buffer, bufferSize, recordId  
                result = ((DBExtractRecordAlt1_t)extract_func)(dbHandle, buffer, &buffer_size, record_id);
                break;
            case 3:  // Alt2: handle, recordId, buffer, bufferSize (no pointer)
                result = ((DBExtractRecordAlt2_t)extract_func)(dbHandle, record_id, buffer, buffer_size);
                break;
            case 4:  // Alt3: handle, recordId, bufferSize, buffer
                result = ((DBExtractRecordAlt3_t)extract_func)(dbHandle, record_id, buffer_size, buffer);
                break;
        }
        
        if (result > 0 && buffer_size > 0) {
            printf("✅ ID %d: SUCCESS! result=%d, size=%d\n", record_id, result, buffer_size);
            printf("   First 16 bytes: ");
            for (int j = 0; j < 16 && j < buffer_size; j++) {
                printf("%02x ", (unsigned char)buffer[j]);
            }
            printf("\n");
            
            // Check for FDO format
            if (buffer_size >= 2 && (unsigned char)buffer[0] == 0x40 && (unsigned char)buffer[1] == 0x01) {
                printf("   🎯 FDO FORMAT DETECTED!\n");
                
                if (buffer_size == 356) {
                    printf("   🎉 PERFECT SIZE - FOUND TARGET RECORD!\n");
                    
                    // Save this record
                    char filename[256];
                    sprintf(filename, "test_output/found_record_%s_type%d_id%d.str", func_name, test_type, record_id);
                    FILE* fp = fopen(filename, "wb");
                    if (fp) {
                        fwrite(buffer, 1, buffer_size, fp);
                        fclose(fp);
                        printf("   💾 Saved to %s\n", filename);
                    }
                    
                    return record_id;  // Return the successful record ID
                }
            }
        } else if (result == 0 && buffer_size != sizeof(buffer)) {
            printf("❓ ID %d: result=0, but size changed to %d\n", record_id, buffer_size);
        }
    }
    
    return -1;  // No success
}

int test_with_different_db_modes() {
    printf("=== Testing Different Database Open Modes ===\n");
    
    HMODULE hDbaol = LoadLibrary("Dbaol32.dll");
    if (!hDbaol) {
        printf("❌ Failed to load Dbaol32.dll\n");
        return 0;
    }
    
    DBOpen_t DBOpen = (DBOpen_t)GetProcAddress(hDbaol, "DBOpen");
    DBClose_t DBClose = (DBClose_t)GetProcAddress(hDbaol, "DBClose");
    DBExtractRecord_t DBExtractRecord = (DBExtractRecord_t)GetProcAddress(hDbaol, "DBExtractRecord");
    DBGetLastError_t DBGetLastError = (DBGetLastError_t)GetProcAddress(hDbaol, "DBGetLastError");
    
    if (!DBOpen || !DBExtractRecord) {
        printf("❌ Required functions not found\n");
        FreeLibrary(hDbaol);
        return 0;
    }
    
    // Try opening with different file modes/paths
    const char* db_paths[] = {
        "golden_tests/main.IDX",
        "./golden_tests/main.IDX", 
        "golden_tests\\main.IDX",
        "main.IDX"  // After copying to current dir
    };
    
    int num_paths = sizeof(db_paths) / sizeof(db_paths[0]);
    
    // Copy the database to current directory for the last test
    system("cp golden_tests/main.IDX main.IDX");
    
    for (int i = 0; i < num_paths; i++) {
        printf("\nTrying to open: %s\n", db_paths[i]);
        
        int dbHandle = DBOpen(db_paths[i]);
        printf("DBOpen result: %d\n", dbHandle);
        
        if (dbHandle > 0) {
            printf("✅ Successfully opened database!\n");
            
            // Test different extraction patterns
            int found_record = test_record_extraction_patterns(dbHandle, DBExtractRecord, "DBExtractRecord", 1);
            
            if (found_record >= 0) {
                printf("🎉 FOUND WORKING RECORD ID: %d\n", found_record);
                if (DBClose) DBClose(dbHandle);
                FreeLibrary(hDbaol);
                return found_record;
            }
            
            if (DBClose) DBClose(dbHandle);
        } else {
            printf("❌ Failed to open\n");
            if (DBGetLastError) {
                const char* error = DBGetLastError();
                if (error && strlen(error) > 0) {
                    printf("   Error: %s\n", error);
                }
            }
        }
    }
    
    FreeLibrary(hDbaol);
    return -1;
}

int explore_more_db_functions() {
    printf("\n=== Exploring Additional Database Functions ===\n");
    
    HMODULE hDbaol = LoadLibrary("Dbaol32.dll");
    if (!hDbaol) return 0;
    
    // Test more function names that might exist
    const char* additional_functions[] = {
        "DBGetRecord",
        "DBReadRecord", 
        "DBFetchRecord",
        "DBLoadRecord",
        "DBRetrieveRecord",
        "DBQueryRecord",
        "DBFindRecord",
        "DBSeekRecord",
        "DBGetData",
        "DBGetRecordByIndex",
        "DBGetRecordByID",
        "DBGetRecordData",
        "DBEnum",
        "DBEnumRecords",
        "DBGetFirst",
        "DBGetNext"
    };
    
    int num_funcs = sizeof(additional_functions) / sizeof(additional_functions[0]);
    
    printf("Checking for additional extraction functions:\n");
    for (int i = 0; i < num_funcs; i++) {
        void* func = GetProcAddress(hDbaol, additional_functions[i]);
        printf("%-20s: %s\n", additional_functions[i], func ? "✅ FOUND!" : "❌");
        
        if (func) {
            // If we find a new function, we could test it here
            printf("   Found new function at %p\n", func);
        }
    }
    
    FreeLibrary(hDbaol);
    return 0;
}

int main() {
    printf("=== Systematic Database Function Debugging ===\n");
    
    // Step 1: Try different database opening modes
    int working_record_id = test_with_different_db_modes();
    
    if (working_record_id >= 0) {
        printf("\n🎯 SUCCESS! Found working extraction with record ID %d\n", working_record_id);
        return 0;
    }
    
    // Step 2: Look for additional functions
    explore_more_db_functions();
    
    printf("\n❌ No working extraction method found yet\n");
    printf("Next steps:\n");
    printf("1. Check if database needs specific initialization\n");
    printf("2. Try different calling conventions (__cdecl)\n");
    printf("3. Look for documentation or examples\n");
    
    return 1;
}