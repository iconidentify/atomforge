/*
 * Fix DBAddRecord function signature and parameters
 */
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>

typedef int (__stdcall *DBOpen_t)(const char* filename);
typedef int (__stdcall *DBClose_t)(int handle);
typedef int (__stdcall *DBCreate_t)(const char* filename);
typedef int (__stdcall *DBExtractRecord_t)(int handle, int recordId, void* buffer, int* bufferSize);

// Different possible signatures for DBAddRecord
typedef int (__stdcall *DBAddRecord1_t)(int handle, void* data, int dataSize, int* recordId);
typedef int (__stdcall *DBAddRecord2_t)(int handle, int* recordId, void* data, int dataSize);
typedef int (__stdcall *DBAddRecord3_t)(int handle, void* data, int dataSize);
typedef int (__stdcall *DBAddRecord4_t)(int handle, int dataSize, void* data, int* recordId);
typedef int (__cdecl *DBAddRecord_cdecl_t)(int handle, void* data, int dataSize, int* recordId);

int test_add_function(int dbHandle, void* add_func, void* data, int dataSize, const char* signature_name) {
    printf("\n--- Testing %s ---\n", signature_name);
    
    int record_id = 0;
    int result = 0;
    
    if (strcmp(signature_name, "stdcall_1") == 0) {
        // handle, data, dataSize, recordId
        result = ((DBAddRecord1_t)add_func)(dbHandle, data, dataSize, &record_id);
    } else if (strcmp(signature_name, "stdcall_2") == 0) {
        // handle, recordId, data, dataSize
        result = ((DBAddRecord2_t)add_func)(dbHandle, &record_id, data, dataSize);
    } else if (strcmp(signature_name, "stdcall_3") == 0) {
        // handle, data, dataSize (no recordId output)
        result = ((DBAddRecord3_t)add_func)(dbHandle, data, dataSize);
        record_id = result; // Maybe function returns the record ID
    } else if (strcmp(signature_name, "stdcall_4") == 0) {
        // handle, dataSize, data, recordId
        result = ((DBAddRecord4_t)add_func)(dbHandle, dataSize, data, &record_id);
    } else if (strcmp(signature_name, "cdecl") == 0) {
        // __cdecl calling convention
        result = ((DBAddRecord_cdecl_t)add_func)(dbHandle, data, dataSize, &record_id);
    }
    
    printf("Result: %d, Record ID: %d\n", result, record_id);
    
    if (result > 0 || record_id > 0) {
        printf("✅ SUCCESS! %s worked\n", signature_name);
        
        // Try to extract the record we just added
        DBExtractRecord_t DBExtractRecord = (DBExtractRecord_t)GetProcAddress(LoadLibrary("Dbaol32.dll"), "DBExtractRecord");
        if (DBExtractRecord) {
            char extracted[1024];
            int extracted_size = sizeof(extracted);
            
            int extract_result = DBExtractRecord(dbHandle, record_id > 0 ? record_id : result, extracted, &extracted_size);
            printf("Extract result: %d, size: %d\n", extract_result, extracted_size);
            
            if (extract_result > 0 && extracted_size > 0) {
                printf("🎉 ROUND-TRIP SUCCESS!\n");
                printf("Original: %d bytes, Extracted: %d bytes\n", dataSize, extracted_size);
                printf("Size change: %d bytes\n", dataSize - extracted_size);
                
                printf("First 16 bytes: ");
                for (int i = 0; i < 16 && i < extracted_size; i++) {
                    printf("%02x ", (unsigned char)extracted[i]);
                }
                printf("\n");
                
                // Check for FDO encoding
                if (extracted_size >= 2 && (unsigned char)extracted[0] == 0x40 && (unsigned char)extracted[1] == 0x01) {
                    printf("🎯 ENCODED TO FDO FORMAT!\n");
                    if (extracted_size == 356) {
                        printf("🏆 PERFECT SIZE - MISSION ACCOMPLISHED!\n");
                    }
                    
                    // Save the result
                    char filename[256];
                    sprintf(filename, "test_output/encoded_%s.str", signature_name);
                    FILE* fp = fopen(filename, "wb");
                    if (fp) {
                        fwrite(extracted, 1, extracted_size, fp);
                        fclose(fp);
                        printf("💾 Saved to %s\n", filename);
                    }
                }
                
                return 1; // Success
            }
        }
    } else {
        printf("❌ Failed with %s\n", signature_name);
    }
    
    return 0;
}

int main() {
    printf("=== Testing All DBAddRecord Signatures ===\n");
    
    HMODULE hDll = LoadLibrary("Dbaol32.dll");
    if (!hDll) {
        printf("❌ Failed to load Dbaol32.dll\n");
        return 1;
    }
    
    DBCreate_t DBCreate = (DBCreate_t)GetProcAddress(hDll, "DBCreate");
    DBOpen_t DBOpen = (DBOpen_t)GetProcAddress(hDll, "DBOpen");
    DBClose_t DBClose = (DBClose_t)GetProcAddress(hDll, "DBClose");
    void* DBAddRecord = GetProcAddress(hDll, "DBAddRecord");
    
    if (!DBCreate || !DBOpen || !DBAddRecord) {
        printf("❌ Required functions not found\n");
        FreeLibrary(hDll);
        return 1;
    }
    
    // Create a test database
    const char* test_db = "signature_test.idx";
    remove(test_db);
    
    printf("Creating test database...\n");
    int create_result = DBCreate(test_db);
    printf("DBCreate result: %d\n", create_result);
    
    if (create_result <= 0) {
        printf("❌ Failed to create database\n");
        FreeLibrary(hDll);
        return 1;
    }
    
    int dbHandle = DBOpen(test_db);
    printf("DBOpen result: %d\n", dbHandle);
    
    if (dbHandle <= 0) {
        printf("❌ Failed to open database\n");
        FreeLibrary(hDll);
        return 1;
    }
    
    // Load test data (our raw Ada32 output)
    FILE* fp = fopen("test_output/clean_AdaAssembleAtomStream.str", "rb");
    if (!fp) {
        printf("❌ Test data not found\n");
        if (DBClose) DBClose(dbHandle);
        FreeLibrary(hDll);
        return 1;
    }
    
    fseek(fp, 0, SEEK_END);
    long data_size = ftell(fp);
    fseek(fp, 0, SEEK_SET);
    
    char* test_data = malloc(data_size);
    fread(test_data, 1, data_size, fp);
    fclose(fp);
    
    printf("Loaded %ld bytes of test data\n", data_size);
    
    // Test all different function signatures
    const char* signatures[] = {
        "stdcall_1",  // handle, data, dataSize, recordId  
        "stdcall_2",  // handle, recordId, data, dataSize
        "stdcall_3",  // handle, data, dataSize (returns ID)
        "stdcall_4",  // handle, dataSize, data, recordId
        "cdecl"       // __cdecl version
    };
    
    int num_signatures = sizeof(signatures) / sizeof(signatures[0]);
    int success_count = 0;
    
    for (int i = 0; i < num_signatures; i++) {
        if (test_add_function(dbHandle, DBAddRecord, test_data, (int)data_size, signatures[i])) {
            success_count++;
            printf("🎉 FOUND WORKING SIGNATURE: %s\n", signatures[i]);
            // Don't break - test all to see if multiple work
        }
    }
    
    printf("\n=== SUMMARY ===\n");
    printf("Working signatures: %d/%d\n", success_count, num_signatures);
    
    if (success_count > 0) {
        printf("🎯 SUCCESS! Database encoding is working!\n");
        printf("We can now build the complete .txt to .str compiler!\n");
    } else {
        printf("❌ No working signatures found\n");
        printf("Need to investigate further or try different approaches\n");
    }
    
    free(test_data);
    if (DBClose) DBClose(dbHandle);
    FreeLibrary(hDll);
    return 0;
}