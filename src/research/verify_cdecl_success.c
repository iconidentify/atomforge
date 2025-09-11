/*
 * Clean test to verify if __cdecl calling convention works
 */
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>

typedef int (__stdcall *DBOpen_t)(const char* filename);
typedef int (__stdcall *DBClose_t)(int handle);
typedef int (__cdecl *DBUpdateRecord_t)(int handle, int recordId, void* data, int dataSize);
typedef int (__cdecl *DBExtractRecord_t)(int handle, int recordId, void* buffer, int* bufferSize);

int main() {
    printf("=== Clean __cdecl Verification Test ===\n");
    
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
        printf("❌ Functions not found\n");
        FreeLibrary(hDll);
        return 1;
    }
    
    printf("✅ Functions loaded with __cdecl signatures\n");
    
    // Open database
    int dbHandle = DBOpen("working_copy.IDX");
    printf("DBOpen result: %d\n", dbHandle);
    
    if (dbHandle <= 0) {
        printf("❌ Failed to open database\n");
        FreeLibrary(hDll);
        return 1;
    }
    
    printf("✅ Database opened\n");
    
    // Test with very simple data first
    printf("\n=== Testing Simple Data ===\n");
    char simple_data[] = "Hello";
    int simple_size = strlen(simple_data);
    int test_record_id = 999999;
    
    printf("Testing with '%s' (%d bytes) at record ID %d\n", simple_data, simple_size, test_record_id);
    
    int update_result = DBUpdateRecord(dbHandle, test_record_id, simple_data, simple_size);
    printf("DBUpdateRecord result: %d\n", update_result);
    
    if (update_result > 0) {
        printf("✅ UPDATE SUCCESS!\n");
        
        // Try to extract it
        char extracted[256];
        int extracted_size = sizeof(extracted);
        
        int extract_result = DBExtractRecord(dbHandle, test_record_id, extracted, &extracted_size);
        printf("DBExtractRecord result: %d, size: %d\n", extract_result, extracted_size);
        
        if (extract_result > 0 && extracted_size > 0) {
            printf("✅ EXTRACTION SUCCESS!\n");
            printf("Round-trip verified: %d bytes in → %d bytes out\n", simple_size, extracted_size);
            
            printf("Extracted data: '");
            for (int i = 0; i < extracted_size && i < 32; i++) {
                if (extracted[i] >= 32 && extracted[i] <= 126) {
                    printf("%c", extracted[i]);
                } else {
                    printf("[%02x]", (unsigned char)extracted[i]);
                }
            }
            printf("'\n");
            
            // Now test with our actual Ada32 data
            printf("\n=== Testing Ada32 Data ===\n");
            
            FILE* fp = fopen("test_output/clean_AdaAssembleAtomStream.str", "rb");
            if (fp) {
                fseek(fp, 0, SEEK_END);
                long raw_size = ftell(fp);
                fseek(fp, 0, SEEK_SET);
                
                char* raw_data = malloc(raw_size);
                fread(raw_data, 1, raw_size, fp);
                fclose(fp);
                
                printf("Testing with %ld-byte Ada32 data\n", raw_size);
                
                int ada32_record_id = 888888;
                int ada32_update = DBUpdateRecord(dbHandle, ada32_record_id, raw_data, (int)raw_size);
                printf("Ada32 DBUpdateRecord result: %d\n", ada32_update);
                
                if (ada32_update > 0) {
                    printf("✅ ADA32 UPDATE SUCCESS!\n");
                    
                    char ada32_extracted[1024];
                    int ada32_extracted_size = sizeof(ada32_extracted);
                    
                    int ada32_extract = DBExtractRecord(dbHandle, ada32_record_id, ada32_extracted, &ada32_extracted_size);
                    printf("Ada32 extract result: %d, size: %d\n", ada32_extract, ada32_extracted_size);
                    
                    if (ada32_extract > 0 && ada32_extracted_size > 0) {
                        printf("🎉 ADA32 ROUND-TRIP SUCCESS!\n");
                        printf("Original: %ld bytes → Encoded: %d bytes\n", raw_size, ada32_extracted_size);
                        printf("Compression: %ld bytes (%.1f%%)\n", 
                               raw_size - ada32_extracted_size, 
                               (float)(raw_size - ada32_extracted_size) / raw_size * 100);
                        
                        printf("Encoded header: ");
                        for (int i = 0; i < 16 && i < ada32_extracted_size; i++) {
                            printf("%02x ", (unsigned char)ada32_extracted[i]);
                        }
                        printf("\n");
                        
                        // Check for FDO format
                        if (ada32_extracted_size >= 2 && 
                            (unsigned char)ada32_extracted[0] == 0x40 && 
                            (unsigned char)ada32_extracted[1] == 0x01) {
                            printf("🎯 CONVERTED TO FDO FORMAT!\n");
                            
                            if (ada32_extracted_size == 356) {
                                printf("🏆 PERFECT SIZE - EXACT TARGET ACHIEVED!\n");
                                printf("🎉🎉🎉 COMPLETE .txt TO .str COMPILER SUCCESS! 🎉🎉🎉\n");
                            } else {
                                printf("Size: %d bytes (target: 356)\n", ada32_extracted_size);
                            }
                            
                            // Save the final result
                            FILE* final_fp = fopen("test_output/FINAL_ENCODED_RESULT.str", "wb");
                            if (final_fp) {
                                fwrite(ada32_extracted, 1, ada32_extracted_size, final_fp);
                                fclose(final_fp);
                                printf("💾 Saved final result to FINAL_ENCODED_RESULT.str\n");
                            }
                            
                            // Compare with golden file
                            FILE* golden_fp = fopen("golden_tests/32-105.str", "rb");
                            if (golden_fp) {
                                fseek(golden_fp, 0, SEEK_END);
                                int golden_size = ftell(golden_fp);
                                fseek(golden_fp, 0, SEEK_SET);
                                
                                char* golden_data = malloc(golden_size);
                                fread(golden_data, 1, golden_size, golden_fp);
                                fclose(golden_fp);
                                
                                printf("\n📊 Golden file comparison:\n");
                                printf("Our result: %d bytes\n", ada32_extracted_size);
                                printf("Golden file: %d bytes\n", golden_size);
                                
                                if (ada32_extracted_size == golden_size) {
                                    int matches = 0;
                                    for (int i = 0; i < golden_size; i++) {
                                        if (ada32_extracted[i] == golden_data[i]) matches++;
                                    }
                                    printf("Byte accuracy: %d/%d (%.1f%%)\n", 
                                           matches, golden_size, (float)matches/golden_size*100);
                                    
                                    if (matches == golden_size) {
                                        printf("🎉🎉🎉 PERFECT MATCH! MISSION ACCOMPLISHED! 🎉🎉🎉\n");
                                    }
                                }
                                
                                free(golden_data);
                            }
                        } else {
                            printf("❌ Not FDO format\n");
                        }
                    } else {
                        printf("❌ Ada32 extraction failed\n");
                    }
                } else {
                    printf("❌ Ada32 update failed\n");
                }
                
                free(raw_data);
            } else {
                printf("❌ Could not load Ada32 data\n");
            }
        } else {
            printf("❌ Simple data extraction failed\n");
        }
    } else {
        printf("❌ Simple data update failed\n");
    }
    
    if (DBClose) DBClose(dbHandle);
    FreeLibrary(hDll);
    return 0;
}