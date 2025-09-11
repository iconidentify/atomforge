/*
 * Simple test with real database - careful error handling
 */
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>

typedef int (__stdcall *DBOpen_t)(const char* filename);
typedef int (__stdcall *DBClose_t)(int handle);
typedef int (__stdcall *DBUpdateRecord_t)(int handle, int recordId, void* data, int dataSize);
typedef int (__stdcall *DBExtractRecord_t)(int handle, int recordId, void* buffer, int* bufferSize);

int copy_database() {
    printf("Copying database file...\n");
    
    FILE* src = fopen("golden_tests/main.IDX", "rb");
    if (!src) {
        printf("❌ Cannot open source database\n");
        return 0;
    }
    
    FILE* dst = fopen("working_copy.IDX", "wb");
    if (!dst) {
        printf("❌ Cannot create destination file\n");
        fclose(src);
        return 0;
    }
    
    // Copy the file
    char buffer[8192];
    size_t bytes;
    while ((bytes = fread(buffer, 1, sizeof(buffer), src)) > 0) {
        fwrite(buffer, 1, bytes, dst);
    }
    
    fclose(src);
    fclose(dst);
    
    printf("✅ Database copied successfully\n");
    return 1;
}

int main() {
    printf("=== Simple Real Database Test ===\n");
    
    // Copy the database
    if (!copy_database()) {
        return 1;
    }
    
    HMODULE hDll = LoadLibrary("Dbaol32.dll");
    if (!hDll) {
        printf("❌ Failed to load Dbaol32.dll\n");
        return 1;
    }
    
    DBOpen_t DBOpen = (DBOpen_t)GetProcAddress(hDll, "DBOpen");
    DBClose_t DBClose = (DBClose_t)GetProcAddress(hDll, "DBClose");
    DBUpdateRecord_t DBUpdateRecord = (DBUpdateRecord_t)GetProcAddress(hDll, "DBUpdateRecord");
    DBExtractRecord_t DBExtractRecord = (DBExtractRecord_t)GetProcAddress(hDll, "DBExtractRecord");
    
    if (!DBOpen || !DBUpdateRecord || !DBExtractRecord) {
        printf("❌ Required functions not found\n");
        FreeLibrary(hDll);
        return 1;
    }
    
    printf("✅ Functions loaded\n");
    
    // Open the working copy
    printf("Opening working database copy...\n");
    int dbHandle = DBOpen("working_copy.IDX");
    printf("DBOpen result: %d\n", dbHandle);
    
    if (dbHandle <= 0) {
        printf("❌ Failed to open database\n");
        FreeLibrary(hDll);
        return 1;
    }
    
    printf("✅ Database opened successfully\n");
    
    // Load our raw Ada32 data
    FILE* fp = fopen("test_output/clean_AdaAssembleAtomStream.str", "rb");
    if (!fp) {
        printf("❌ Raw data not found\n");
        if (DBClose) DBClose(dbHandle);
        FreeLibrary(hDll);
        return 1;
    }
    
    fseek(fp, 0, SEEK_END);
    long raw_size = ftell(fp);
    fseek(fp, 0, SEEK_SET);
    
    char* raw_data = malloc(raw_size);
    fread(raw_data, 1, raw_size, fp);
    fclose(fp);
    
    printf("✅ Loaded %ld bytes of raw data\n", raw_size);
    
    // Try to update a high-numbered record to avoid breaking anything important
    int test_record_id = 999999;
    printf("\\nTesting DBUpdateRecord with record ID %d...\n", test_record_id);
    
    int update_result = DBUpdateRecord(dbHandle, test_record_id, raw_data, (int)raw_size);
    printf("DBUpdateRecord result: %d\n", update_result);
    
    if (update_result > 0) {
        printf("✅ Update succeeded! Testing extraction...\n");
        
        char extracted[1024];
        int extracted_size = sizeof(extracted);
        
        int extract_result = DBExtractRecord(dbHandle, test_record_id, extracted, &extracted_size);
        printf("DBExtractRecord result: %d, size: %d\n", extract_result, extracted_size);
        
        if (extract_result > 0 && extracted_size > 0) {
            printf("🎉 ROUND-TRIP SUCCESS!\n");
            printf("Input: %ld bytes → Output: %d bytes\n", raw_size, extracted_size);
            printf("Compression: %ld bytes (%.1f%%)\n", raw_size - extracted_size, 
                   (float)(raw_size - extracted_size) / raw_size * 100);
            
            printf("Output header: ");
            for (int i = 0; i < 8 && i < extracted_size; i++) {
                printf("%02x ", (unsigned char)extracted[i]);
            }
            printf("\n");
            
            // Check for FDO format
            if (extracted_size >= 2 && (unsigned char)extracted[0] == 0x40 && (unsigned char)extracted[1] == 0x01) {
                printf("🎯 CONVERTED TO FDO FORMAT!\n");
                
                if (extracted_size == 356) {
                    printf("🏆 PERFECT! Exact target size achieved!\n");
                } else {
                    printf("Size: %d bytes (target: 356)\n", extracted_size);
                }
                
                // Save the result
                FILE* out_fp = fopen("test_output/database_encoded.str", "wb");
                if (out_fp) {
                    fwrite(extracted, 1, extracted_size, out_fp);
                    fclose(out_fp);
                    printf("💾 Saved database-encoded result\n");
                }
                
                printf("\\n🎉 DATABASE ENCODING WORKS!\n");
                printf("We have proven the encoding mechanism!\n");
            } else {
                printf("❌ Not FDO format (starts with %02x %02x)\n", 
                       (unsigned char)extracted[0], (unsigned char)extracted[1]);
            }
        } else {
            printf("❌ Extraction failed\n");
        }
    } else {
        printf("❌ Update failed\n");
        
        // Try with a smaller record ID
        printf("\\nTrying with smaller record ID...\n");
        int small_id = 1000;
        
        update_result = DBUpdateRecord(dbHandle, small_id, raw_data, (int)raw_size);
        printf("DBUpdateRecord (ID %d) result: %d\n", small_id, update_result);
        
        if (update_result > 0) {
            printf("✅ Smaller ID worked!\n");
        }
    }
    
    free(raw_data);
    if (DBClose) DBClose(dbHandle);
    FreeLibrary(hDll);
    return 0;
}