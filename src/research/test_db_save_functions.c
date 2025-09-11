/*
 * Test DBAddRecord and DBUpdateRecord for FDO conversion
 */
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>

typedef int (__stdcall *DBOpen_t)(const char* filename);
typedef int (__stdcall *DBClose_t)(int handle);
typedef int (__stdcall *DBAddRecord_t)(int handle, void* data, int dataSize, int* recordId);
typedef int (__stdcall *DBUpdateRecord_t)(int handle, int recordId, void* data, int dataSize);
typedef int (__stdcall *DBExtractRecord_t)(int handle, int recordId, void* buffer, int* bufferSize);
typedef const char* (__stdcall *DBGetLastError_t)(void);

int main() {
    printf("=== Testing DB Save Functions for FDO Conversion ===\n");
    
    HMODULE hDbaol = LoadLibrary("Dbaol32.dll");
    if (!hDbaol) {
        printf("❌ Failed to load Dbaol32.dll\n");
        return 1;
    }
    
    // Get functions
    DBOpen_t DBOpen = (DBOpen_t)GetProcAddress(hDbaol, "DBOpen");
    DBClose_t DBClose = (DBClose_t)GetProcAddress(hDbaol, "DBClose");
    DBAddRecord_t DBAddRecord = (DBAddRecord_t)GetProcAddress(hDbaol, "DBAddRecord");
    DBUpdateRecord_t DBUpdateRecord = (DBUpdateRecord_t)GetProcAddress(hDbaol, "DBUpdateRecord");
    DBExtractRecord_t DBExtractRecord = (DBExtractRecord_t)GetProcAddress(hDbaol, "DBExtractRecord");
    DBGetLastError_t DBGetLastError = (DBGetLastError_t)GetProcAddress(hDbaol, "DBGetLastError");
    
    printf("Functions available:\n");
    printf("DBOpen: %s\n", DBOpen ? "✅" : "❌");
    printf("DBClose: %s\n", DBClose ? "✅" : "❌");
    printf("DBAddRecord: %s\n", DBAddRecord ? "✅" : "❌");
    printf("DBUpdateRecord: %s\n", DBUpdateRecord ? "✅" : "❌");
    printf("DBExtractRecord: %s\n", DBExtractRecord ? "✅" : "❌");
    
    if (!DBAddRecord || !DBExtractRecord) {
        printf("❌ Missing required functions\n");
        FreeLibrary(hDbaol);
        return 1;
    }
    
    // Read our 413-byte raw Ada32 output
    FILE* fp = fopen("test_output/clean_AdaAssembleAtomStream.str", "rb");
    if (!fp) {
        printf("❌ Need raw Ada32 output file first\n");
        FreeLibrary(hDbaol);
        return 1;
    }
    
    fseek(fp, 0, SEEK_END);
    long raw_size = ftell(fp);
    fseek(fp, 0, SEEK_SET);
    
    char* raw_data = malloc(raw_size);
    fread(raw_data, 1, raw_size, fp);
    fclose(fp);
    
    printf("\n📝 Loaded %ld-byte raw Ada32 output\n", raw_size);
    printf("First 16 bytes: ");
    for (int i = 0; i < 16; i++) {
        printf("%02x ", (unsigned char)raw_data[i]);
    }
    printf("\n");
    
    // Create a temporary database for testing
    const char* test_db = "test_save.idx";
    remove(test_db);  // Remove if exists
    
    printf("\n🔧 Testing save-and-retrieve process...\n");
    
    // This is the key test: Save our raw data and see what format comes back
    int dbHandle = DBOpen(test_db);
    if (dbHandle <= 0) {
        printf("❌ Failed to create/open test database\n");
        if (DBGetLastError) {
            printf("Error: %s\n", DBGetLastError());
        }
        free(raw_data);
        FreeLibrary(hDbaol);
        return 1;
    }
    
    printf("✅ Database opened: handle %d\n", dbHandle);
    
    // Add our raw record
    int new_record_id = 0;
    int add_result = DBAddRecord(dbHandle, raw_data, raw_size, &new_record_id);
    printf("DBAddRecord result: %d, new record ID: %d\n", add_result, new_record_id);
    
    if (add_result > 0) {
        // Now extract it back and see if it got converted to FDO format
        char extracted_data[1024];
        int extracted_size = sizeof(extracted_data);
        
        int extract_result = DBExtractRecord(dbHandle, new_record_id, extracted_data, &extracted_size);
        printf("DBExtractRecord result: %d, size: %d\n", extract_result, extracted_size);
        
        if (extract_result > 0 && extracted_size > 0) {
            printf("Extracted first 16 bytes: ");
            for (int i = 0; i < 16 && i < extracted_size; i++) {
                printf("%02x ", (unsigned char)extracted_data[i]);
            }
            printf("\n");
            
            // Check if it got converted to FDO format
            if (extracted_size >= 2 && (unsigned char)extracted_data[0] == 0x40 && (unsigned char)extracted_data[1] == 0x01) {
                printf("🎯 SUCCESS: Converted to FDO format!\n");
                printf("🎉 Size: %d bytes", extracted_size);
                if (extracted_size == 356) {
                    printf(" - PERFECT PRODUCTION SIZE!");
                }
                printf("\n");
                
                // Save the converted result
                FILE* out_fp = fopen("test_output/db_converted_fdo.str", "wb");
                if (out_fp) {
                    fwrite(extracted_data, 1, extracted_size, out_fp);
                    fclose(out_fp);
                    printf("💾 Saved converted FDO to test_output/db_converted_fdo.str\n");
                }
            } else {
                printf("❌ Still raw format - no conversion happened\n");
            }
        } else {
            printf("❌ Failed to extract record\n");
            if (DBGetLastError) {
                printf("Error: %s\n", DBGetLastError());
            }
        }
    } else {
        printf("❌ Failed to add record\n");
        if (DBGetLastError) {
            printf("Error: %s\n", DBGetLastError());
        }
    }
    
    if (DBClose) DBClose(dbHandle);
    free(raw_data);
    FreeLibrary(hDbaol);
    
    return 0;
}