/*
 * Final attempt to get database encoding working
 * Try copying database and using different function approaches
 */
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef int (__stdcall *DBOpen_t)(const char* filename);
typedef int (__stdcall *DBClose_t)(int handle);
typedef int (__stdcall *DBAddRecord_t)(int handle, void* data, int dataSize, int* recordId);
typedef int (__stdcall *DBUpdateRecord_t)(int handle, int recordId, void* data, int dataSize);
typedef int (__stdcall *DBExtractRecord_t)(int handle, int recordId, void* buffer, int* bufferSize);

// Alternative function signatures (different parameter orders)
typedef int (__stdcall *DBAddRecord2_t)(int handle, int* recordId, void* data, int dataSize);
typedef int (__stdcall *DBExtractRecord2_t)(int handle, void* buffer, int* bufferSize, int recordId);

int main() {
    printf("=== Final Database Encoding Test ===\n");
    
    HMODULE hDbaol = LoadLibrary("Dbaol32.dll");
    if (!hDbaol) {
        printf("❌ Failed to load Dbaol32.dll\n");
        return 1;
    }
    
    DBOpen_t DBOpen = (DBOpen_t)GetProcAddress(hDbaol, "DBOpen");
    DBClose_t DBClose = (DBClose_t)GetProcAddress(hDbaol, "DBClose");
    DBAddRecord_t DBAddRecord = (DBAddRecord_t)GetProcAddress(hDbaol, "DBAddRecord");
    DBUpdateRecord_t DBUpdateRecord = (DBUpdateRecord_t)GetProcAddress(hDbaol, "DBUpdateRecord");
    DBExtractRecord_t DBExtractRecord = (DBExtractRecord_t)GetProcAddress(hDbaol, "DBExtractRecord");
    
    if (!DBOpen || !DBAddRecord || !DBExtractRecord) {
        printf("❌ Required functions not found\n");
        FreeLibrary(hDbaol);
        return 1;
    }
    
    // Load our 413-byte raw Ada32 output
    FILE* fp = fopen("test_output/clean_AdaAssembleAtomStream.str", "rb");
    if (!fp) {
        printf("❌ Raw Ada32 output not found\n");
        FreeLibrary(hDbaol);
        return 1;
    }
    
    fseek(fp, 0, SEEK_END);
    long raw_size = ftell(fp);
    fseek(fp, 0, SEEK_SET);
    
    char* raw_data = malloc(raw_size);
    fread(raw_data, 1, raw_size, fp);
    fclose(fp);
    
    printf("📝 Loaded %ld-byte raw Ada32 output\n", raw_size);
    
    // Create a working copy of the database
    printf("📋 Creating database copy for testing...\n");
    system("cp golden_tests/main.IDX test_working.idx");
    
    // Try opening the copy for modification
    int dbHandle = DBOpen("test_working.idx");
    if (dbHandle <= 0) {
        printf("❌ Failed to open working database copy\n");
        
        // Try creating a completely new database
        printf("🔧 Trying to create new database...\n");
        dbHandle = DBOpen("test_new.idx");
        if (dbHandle <= 0) {
            printf("❌ Cannot create new database either\n");
            free(raw_data);
            FreeLibrary(hDbaol);
            return 1;
        }
    }
    
    printf("✅ Database opened: handle %d\n", dbHandle);
    
    // Try adding our record with different approaches
    printf("\n🧪 Attempting to add record...\n");
    
    // Approach 1: Standard DBAddRecord
    int new_record_id = 0;
    int add_result = DBAddRecord(dbHandle, raw_data, (int)raw_size, &new_record_id);
    printf("DBAddRecord result: %d, record ID: %d\n", add_result, new_record_id);
    
    if (add_result <= 0) {
        // Approach 2: Try with record ID pre-set
        printf("Trying with pre-set record ID...\n");
        new_record_id = 999999;  // Use a high ID that shouldn't conflict
        add_result = DBAddRecord(dbHandle, raw_data, (int)raw_size, &new_record_id);
        printf("DBAddRecord with preset ID result: %d\n", add_result);
    }
    
    if (add_result <= 0) {
        // Approach 3: Try DBUpdateRecord on an existing record
        printf("Trying DBUpdateRecord on existing record...\n");
        // We know record 1 exists from our scanning
        int update_result = DBUpdateRecord(dbHandle, 1, raw_data, (int)raw_size);
        printf("DBUpdateRecord result: %d\n", update_result);
        
        if (update_result > 0) {
            new_record_id = 1;
            add_result = 1;  // Mark as success
        }
    }
    
    // If any approach worked, try to extract the result
    if (add_result > 0) {
        printf("🎯 Record saved successfully! Extracting...\n");
        
        char extracted_data[1024];
        int extracted_size = sizeof(extracted_data);
        
        int extract_result = DBExtractRecord(dbHandle, new_record_id, extracted_data, &extracted_size);
        printf("DBExtractRecord result: %d, size: %d\n", extract_result, extracted_size);
        
        if (extract_result > 0 && extracted_size > 0) {
            printf("🎉 EXTRACTION SUCCESS!\n");
            printf("Original raw size: %ld bytes\n", raw_size);
            printf("Encoded size: %d bytes\n", extracted_size);
            printf("Size reduction: %ld bytes\n", raw_size - extracted_size);
            
            printf("First 16 bytes: ");
            for (int i = 0; i < 16 && i < extracted_size; i++) {
                printf("%02x ", (unsigned char)extracted_data[i]);
            }
            printf("\\n");
            
            // Check if it's FDO format
            if (extracted_size >= 2 && (unsigned char)extracted_data[0] == 0x40 && (unsigned char)extracted_data[1] == 0x01) {
                printf("✅ FDO FORMAT CONFIRMED!\n");
                
                if (extracted_size == 356) {
                    printf("🏆 PERFECT SIZE - ENCODING COMPLETE!\n");
                } else {
                    printf("⚠️  Size %d (target 356)\n", extracted_size);
                }
                
                // Save the final encoded result
                FILE* out_fp = fopen("test_output/final_encoded_result.str", "wb");
                if (out_fp) {
                    fwrite(extracted_data, 1, extracted_size, out_fp);
                    fclose(out_fp);
                    printf("💾 Saved final encoded result\n");
                    
                    // Compare with golden file
                    FILE* golden_fp = fopen("golden_tests/32-105.str", "rb");
                    if (golden_fp) {
                        fseek(golden_fp, 0, SEEK_END);
                        int golden_size = ftell(golden_fp);
                        fseek(golden_fp, 0, SEEK_SET);
                        
                        char* golden_data = malloc(golden_size);
                        fread(golden_data, 1, golden_size, golden_fp);
                        fclose(golden_fp);
                        
                        if (extracted_size == golden_size && memcmp(extracted_data, golden_data, golden_size) == 0) {
                            printf("🎉🎉🎉 PERFECT MATCH WITH GOLDEN FILE! 🎉🎉🎉\n");
                            printf("✅ AUTHENTIC .txt TO .str COMPILER COMPLETE!\n");
                        } else {
                            printf("❌ Differs from golden file\n");
                        }
                        
                        free(golden_data);
                    }
                }
            } else {
                printf("❌ Not FDO format\n");
            }
        } else {
            printf("❌ Extraction failed\n");
        }
    } else {
        printf("❌ All save attempts failed\n");
        printf("The database functions may require specific initialization or parameters\n");
    }
    
    if (DBClose) DBClose(dbHandle);
    free(raw_data);
    FreeLibrary(hDbaol);
    
    return 0;
}