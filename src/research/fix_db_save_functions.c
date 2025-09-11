/*
 * Fix database save functions with proper calling conventions
 * Test both __stdcall and __cdecl to find the right one
 */
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>

// Try __cdecl calling convention first
typedef int (__cdecl *DBOpen_cdecl_t)(const char* filename);
typedef int (__cdecl *DBClose_cdecl_t)(int handle);
typedef int (__cdecl *DBAddRecord_cdecl_t)(int handle, void* data, int dataSize, int* recordId);
typedef int (__cdecl *DBExtractRecord_cdecl_t)(int handle, int recordId, void* buffer, int* bufferSize);

// Try __stdcall calling convention
typedef int (__stdcall *DBOpen_stdcall_t)(const char* filename);
typedef int (__stdcall *DBClose_stdcall_t)(int handle);
typedef int (__stdcall *DBAddRecord_stdcall_t)(int handle, void* data, int dataSize, int* recordId);
typedef int (__stdcall *DBExtractRecord_stdcall_t)(int handle, int recordId, void* buffer, int* bufferSize);

int test_cdecl_functions() {
    printf("=== Testing __cdecl calling convention ===\n");
    
    HMODULE hDbaol = LoadLibrary("Dbaol32.dll");
    if (!hDbaol) {
        printf("❌ Failed to load Dbaol32.dll\n");
        return 0;
    }
    
    DBOpen_cdecl_t DBOpen = (DBOpen_cdecl_t)GetProcAddress(hDbaol, "DBOpen");
    DBClose_cdecl_t DBClose = (DBClose_cdecl_t)GetProcAddress(hDbaol, "DBClose");
    DBAddRecord_cdecl_t DBAddRecord = (DBAddRecord_cdecl_t)GetProcAddress(hDbaol, "DBAddRecord");
    DBExtractRecord_cdecl_t DBExtractRecord = (DBExtractRecord_cdecl_t)GetProcAddress(hDbaol, "DBExtractRecord");
    
    if (!DBOpen || !DBAddRecord || !DBExtractRecord) {
        printf("❌ Functions not found\n");
        FreeLibrary(hDbaol);
        return 0;
    }
    
    printf("✅ All functions found\n");
    
    // Try to create a simple test database
    const char* test_db = "test_cdecl.idx";
    remove(test_db);
    
    printf("Attempting DBOpen...\n");
    int dbHandle = DBOpen(test_db);
    printf("DBOpen result: %d\n", dbHandle);
    
    if (dbHandle > 0) {
        printf("✅ __cdecl seems to work!\n");
        if (DBClose) DBClose(dbHandle);
        FreeLibrary(hDbaol);
        return 1;
    } else {
        printf("❌ __cdecl failed\n");
        FreeLibrary(hDbaol);
        return 0;
    }
}

int test_stdcall_functions() {
    printf("\n=== Testing __stdcall calling convention ===\n");
    
    HMODULE hDbaol = LoadLibrary("Dbaol32.dll");
    if (!hDbaol) {
        printf("❌ Failed to load Dbaol32.dll\n");
        return 0;
    }
    
    DBOpen_stdcall_t DBOpen = (DBOpen_stdcall_t)GetProcAddress(hDbaol, "DBOpen");
    DBClose_stdcall_t DBClose = (DBClose_stdcall_t)GetProcAddress(hDbaol, "DBClose");
    DBAddRecord_stdcall_t DBAddRecord = (DBAddRecord_stdcall_t)GetProcAddress(hDbaol, "DBAddRecord");
    DBExtractRecord_stdcall_t DBExtractRecord = (DBExtractRecord_stdcall_t)GetProcAddress(hDbaol, "DBExtractRecord");
    
    if (!DBOpen || !DBAddRecord || !DBExtractRecord) {
        printf("❌ Functions not found\n");
        FreeLibrary(hDbaol);
        return 0;
    }
    
    printf("✅ All functions found\n");
    
    // Try to create a simple test database
    const char* test_db = "test_stdcall.idx";
    remove(test_db);
    
    printf("Attempting DBOpen...\n");
    int dbHandle = DBOpen(test_db);
    printf("DBOpen result: %d\n", dbHandle);
    
    if (dbHandle > 0) {
        printf("✅ __stdcall seems to work!\n");
        if (DBClose) DBClose(dbHandle);
        FreeLibrary(hDbaol);
        return 1;
    } else {
        printf("❌ __stdcall failed\n");
        FreeLibrary(hDbaol);
        return 0;
    }
}

int test_save_encoding() {
    printf("\n=== Testing Save-Based Encoding ===\n");
    
    // Load our 413-byte raw Ada32 output
    FILE* fp = fopen("test_output/clean_AdaAssembleAtomStream.str", "rb");
    if (!fp) {
        printf("❌ Raw Ada32 output not found\n");
        return 0;
    }
    
    fseek(fp, 0, SEEK_END);
    long raw_size = ftell(fp);
    fseek(fp, 0, SEEK_SET);
    
    char* raw_data = malloc(raw_size);
    fread(raw_data, 1, raw_size, fp);
    fclose(fp);
    
    printf("📝 Loaded %ld-byte raw Ada32 output\n", raw_size);
    
    HMODULE hDbaol = LoadLibrary("Dbaol32.dll");
    if (!hDbaol) {
        printf("❌ Failed to load Dbaol32.dll\n");
        free(raw_data);
        return 0;
    }
    
    // Use __stdcall (typical for Windows DLLs)
    DBOpen_stdcall_t DBOpen = (DBOpen_stdcall_t)GetProcAddress(hDbaol, "DBOpen");
    DBClose_stdcall_t DBClose = (DBClose_stdcall_t)GetProcAddress(hDbaol, "DBClose");
    DBAddRecord_stdcall_t DBAddRecord = (DBAddRecord_stdcall_t)GetProcAddress(hDbaol, "DBAddRecord");
    DBExtractRecord_stdcall_t DBExtractRecord = (DBExtractRecord_stdcall_t)GetProcAddress(hDbaol, "DBExtractRecord");
    
    const char* test_db = "encoding_test.idx";
    remove(test_db);
    
    int dbHandle = DBOpen(test_db);
    if (dbHandle <= 0) {
        printf("❌ Could not create database\n");
        free(raw_data);
        FreeLibrary(hDbaol);
        return 0;
    }
    
    printf("✅ Database created: handle %d\n", dbHandle);
    
    // Add our raw record
    int new_record_id = 0;
    printf("Adding %ld-byte record...\n", raw_size);
    int add_result = DBAddRecord(dbHandle, raw_data, (int)raw_size, &new_record_id);
    printf("DBAddRecord result: %d, record ID: %d\n", add_result, new_record_id);
    
    if (add_result > 0) {
        // Extract it back
        char extracted_data[1024];
        int extracted_size = sizeof(extracted_data);
        
        int extract_result = DBExtractRecord(dbHandle, new_record_id, extracted_data, &extracted_size);
        printf("DBExtractRecord result: %d, size: %d\n", extract_result, extracted_size);
        
        if (extract_result > 0 && extracted_size > 0) {
            printf("🎯 SUCCESS! Extracted %d bytes\n", extracted_size);
            printf("First 16 bytes: ");
            for (int i = 0; i < 16 && i < extracted_size; i++) {
                printf("%02x ", (unsigned char)extracted_data[i]);
            }
            printf("\n");
            
            // Check if it's FDO format
            if (extracted_size >= 2 && (unsigned char)extracted_data[0] == 0x40 && (unsigned char)extracted_data[1] == 0x01) {
                printf("🎉 FDO FORMAT DETECTED!\n");
                printf("Size: %d bytes (target: 356)\n", extracted_size);
                
                if (extracted_size == 356) {
                    printf("🏆 PERFECT SIZE MATCH - ENCODING SUCCESSFUL!\n");
                }
                
                // Save the result
                FILE* out_fp = fopen("test_output/db_encoded_final.str", "wb");
                if (out_fp) {
                    fwrite(extracted_data, 1, extracted_size, out_fp);
                    fclose(out_fp);
                    printf("💾 Saved final encoded result\n");
                }
            }
        }
    }
    
    if (DBClose) DBClose(dbHandle);
    free(raw_data);
    FreeLibrary(hDbaol);
    return 1;
}

int main() {
    printf("=== Database Function Calling Convention Test ===\n");
    
    // Test both calling conventions
    int cdecl_works = test_cdecl_functions();
    int stdcall_works = test_stdcall_functions();
    
    if (stdcall_works || cdecl_works) {
        printf("\n🎯 Found working calling convention!\n");
        test_save_encoding();
    } else {
        printf("\n❌ Neither calling convention worked\n");
    }
    
    return 0;
}