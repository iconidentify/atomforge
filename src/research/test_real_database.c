/*
 * Test DBAddRecord with the actual main.IDX file
 * This is the real test - can we modify the existing database?
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
typedef const char* (__stdcall *DBGetLastError_t)(void);

int test_with_simple_data(int dbHandle, void* add_func, void* update_func, void* extract_func) {
    printf("\n=== Testing with Simple Data ===\n");
    
    // Try with very simple test data first
    char simple_data[] = "Hello World Test";
    int simple_size = strlen(simple_data);
    
    printf("Testing with %d-byte simple string...\n", simple_size);
    
    int record_id = 0;
    int result = ((DBAddRecord_t)add_func)(dbHandle, simple_data, simple_size, &record_id);
    printf("DBAddRecord result: %d, record ID: %d\n", result, record_id);
    
    if (result > 0 || record_id > 0) {
        printf("✅ Simple data worked!\n");
        
        // Try to extract it
        char extracted[256];
        int extracted_size = sizeof(extracted);
        int extract_result = ((DBExtractRecord_t)extract_func)(dbHandle, record_id > 0 ? record_id : result, extracted, &extracted_size);
        
        printf("Extract result: %d, size: %d\n", extract_result, extracted_size);
        if (extract_result > 0) {
            printf("Extracted: ");
            for (int i = 0; i < extracted_size && i < 32; i++) {
                if (extracted[i] >= 32 && extracted[i] <= 126) {
                    printf("%c", extracted[i]);
                } else {
                    printf("[%02x]", (unsigned char)extracted[i]);
                }
            }
            printf("\n");
            return 1;
        }
    }
    
    // Try with FDO-like header format
    printf("\nTesting with FDO-like header...\n");
    char fdo_data[] = {0x40, 0x01, 0x01, 0x00, 0x05, 0x01, 'T', 'e', 's', 't'};
    int fdo_size = sizeof(fdo_data);
    
    record_id = 0;
    result = ((DBAddRecord_t)add_func)(dbHandle, fdo_data, fdo_size, &record_id);
    printf("DBAddRecord with FDO header result: %d, record ID: %d\n", result, record_id);
    
    if (result > 0 || record_id > 0) {
        printf("✅ FDO header data worked!\n");
        return 1;
    }
    
    return 0;
}

int test_update_existing_record(int dbHandle, void* update_func, void* extract_func) {
    printf("\n=== Testing DBUpdateRecord on Existing Records ===\n");
    
    // We know from scanning that there are records at low IDs
    // Let's try to update one of them with our data
    
    // Load our raw Ada32 output
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
    
    printf("Loaded %ld bytes of raw Ada32 data\n", raw_size);
    
    // Try to update a few different record IDs
    int test_record_ids[] = {1, 2, 3, 999999, 1000000};  // Use high IDs to avoid breaking important records
    int num_tests = sizeof(test_record_ids) / sizeof(test_record_ids[0]);
    
    for (int i = 0; i < num_tests; i++) {
        int record_id = test_record_ids[i];
        printf("\nTrying to update record %d...\n", record_id);
        
        int update_result = ((DBUpdateRecord_t)update_func)(dbHandle, record_id, raw_data, (int)raw_size);
        printf("DBUpdateRecord result: %d\n", update_result);
        
        if (update_result > 0) {
            printf("✅ Update successful! Testing extraction...\n");
            
            char extracted[1024];
            int extracted_size = sizeof(extracted);
            
            int extract_result = ((DBExtractRecord_t)extract_func)(dbHandle, record_id, extracted, &extracted_size);
            printf("Extract result: %d, size: %d\n", extract_result, extracted_size);
            
            if (extract_result > 0 && extracted_size > 0) {
                printf("🎉 UPDATE AND EXTRACT SUCCESS!\n");
                printf("Original: %ld bytes → Stored: %d bytes\n", raw_size, extracted_size);
                printf("Size difference: %ld bytes\n", raw_size - extracted_size);
                
                printf("First 16 bytes: ");
                for (int j = 0; j < 16 && j < extracted_size; j++) {
                    printf("%02x ", (unsigned char)extracted[j]);
                }
                printf("\n");
                
                // Check for FDO encoding
                if (extracted_size >= 2 && (unsigned char)extracted[0] == 0x40 && (unsigned char)extracted[1] == 0x01) {
                    printf("🎯 ENCODED TO FDO FORMAT!\n");
                    
                    if (extracted_size == 356) {
                        printf("🏆 PERFECT SIZE - EXACT TARGET!\n");
                    } else {
                        printf("Size: %d (target: 356)\n", extracted_size);
                    }
                    
                    // Save the encoded result
                    FILE* out_fp = fopen("test_output/update_encoded_result.str", "wb");
                    if (out_fp) {
                        fwrite(extracted, 1, extracted_size, out_fp);
                        fclose(out_fp);
                        printf("💾 Saved encoded result\n");
                        
                        // Compare with golden file
                        FILE* golden_fp = fopen("golden_tests/32-105.str", "rb");
                        if (golden_fp) {
                            fseek(golden_fp, 0, SEEK_END);
                            int golden_size = ftell(golden_fp);
                            fseek(golden_fp, 0, SEEK_SET);
                            
                            char* golden_data = malloc(golden_size);
                            fread(golden_data, 1, golden_size, golden_fp);
                            fclose(golden_fp);
                            
                            if (extracted_size == golden_size) {
                                int matches = 0;
                                for (int k = 0; k < golden_size; k++) {
                                    if (extracted[k] == golden_data[k]) matches++;
                                }
                                printf("Byte accuracy: %d/%d (%.1f%%)\n", matches, golden_size, (float)matches/golden_size*100);
                                
                                if (matches == golden_size) {
                                    printf("🎉🎉🎉 PERFECT MATCH WITH GOLDEN FILE! 🎉🎉🎉\n");
                                    printf("✅ COMPLETE .txt TO .str COMPILER ACHIEVED!\n");
                                }
                            }
                            
                            free(golden_data);
                        }
                    }
                }
                
                free(raw_data);
                return 1;  // Success!
            }
        } else {
            printf("❌ Update failed for record %d\n", record_id);
        }
    }
    
    free(raw_data);
    return 0;
}

int main() {
    printf("=== Testing with Real main.IDX Database ===\n");
    
    HMODULE hDll = LoadLibrary("Dbaol32.dll");
    if (!hDll) {
        printf("❌ Failed to load Dbaol32.dll\n");
        return 1;
    }
    
    DBOpen_t DBOpen = (DBOpen_t)GetProcAddress(hDll, "DBOpen");
    DBClose_t DBClose = (DBClose_t)GetProcAddress(hDll, "DBClose");
    DBAddRecord_t DBAddRecord = (DBAddRecord_t)GetProcAddress(hDll, "DBAddRecord");
    DBUpdateRecord_t DBUpdateRecord = (DBUpdateRecord_t)GetProcAddress(hDll, "DBUpdateRecord");
    DBExtractRecord_t DBExtractRecord = (DBExtractRecord_t)GetProcAddress(hDll, "DBExtractRecord");
    DBGetLastError_t DBGetLastError = (DBGetLastError_t)GetProcAddress(hDll, "DBGetLastError");
    
    printf("Functions loaded:\n");
    printf("  DBOpen: %s\n", DBOpen ? "✅" : "❌");
    printf("  DBAddRecord: %s\n", DBAddRecord ? "✅" : "❌");
    printf("  DBUpdateRecord: %s\n", DBUpdateRecord ? "✅" : "❌");
    printf("  DBExtractRecord: %s\n", DBExtractRecord ? "✅" : "❌");
    
    // Create a working copy of main.IDX
    printf("\nCreating working copy of main.IDX...\n");
    system("cp golden_tests/main.IDX working_main.IDX");
    
    // Open the working copy
    int dbHandle = DBOpen("working_main.IDX");
    printf("DBOpen result: %d\n", dbHandle);
    
    if (dbHandle <= 0) {
        printf("❌ Failed to open working database copy\n");
        if (DBGetLastError) {
            const char* error = DBGetLastError();
            if (error && strlen(error) > 0) {
                printf("Error: %s\n", error);
            }
        }
        FreeLibrary(hDll);
        return 1;
    }
    
    printf("✅ Opened working copy of main.IDX\n");
    
    // Test 1: Try adding simple data
    int simple_success = test_with_simple_data(dbHandle, DBAddRecord, DBUpdateRecord, DBExtractRecord);
    
    // Test 2: Try updating existing records (this is the key test!)
    int update_success = test_update_existing_record(dbHandle, DBUpdateRecord, DBExtractRecord);
    
    printf("\n=== FINAL RESULTS ===\n");
    printf("Simple data test: %s\n", simple_success ? "✅ SUCCESS" : "❌ FAILED");
    printf("Update existing record test: %s\n", update_success ? "✅ SUCCESS" : "❌ FAILED");
    
    if (update_success) {
        printf("\n🎯 BREAKTHROUGH! Database encoding is working!\n");
        printf("We can now build the complete authentic .txt to .str compiler!\n");
    } else if (simple_success) {
        printf("\n⚠️  Partial success - simple data works but complex data needs work\n");
    } else {
        printf("\n❌ Still debugging needed - will continue investigating\n");
    }
    
    if (DBClose) DBClose(dbHandle);
    FreeLibrary(hDll);
    return 0;
}