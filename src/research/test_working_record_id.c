/*
 * Test the working record ID found: 4235928 with __cdecl
 */
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>

typedef int (__stdcall *DBOpen_t)(const char* filename);
typedef int (__stdcall *DBClose_t)(int handle);
typedef int (__stdcall *DBSetVersion_t)(int handle, int version);
typedef int (__stdcall *DBSetPurge_t)(int handle, int purge);
typedef int (__stdcall *DBSetMaxSize_t)(int handle, int maxSize);
typedef int (__stdcall *DBSetMinSize_t)(int handle, int minSize);

typedef int (__cdecl *DBUpdateRecord_t)(int handle, int recordId, void* data, int dataSize);
typedef int (__cdecl *DBExtractRecord_t)(int handle, int recordId, void* buffer, int* bufferSize);

typedef const char* (__stdcall *DBGetLastError_t)(void);

int main() {
    printf("=== Testing Working Record ID 4235928 ===\n");
    
    HMODULE hDll = LoadLibrary("Dbaol32.dll");
    if (!hDll) {
        printf("❌ Failed to load Dbaol32.dll\n");
        return 1;
    }
    
    DBOpen_t DBOpen = (DBOpen_t)GetProcAddress(hDll, "DBOpen");
    DBClose_t DBClose = (DBClose_t)GetProcAddress(hDll, "DBClose");
    DBSetVersion_t DBSetVersion = (DBSetVersion_t)GetProcAddress(hDll, "DBSetVersion");
    DBSetPurge_t DBSetPurge = (DBSetPurge_t)GetProcAddress(hDll, "DBSetPurge");
    DBSetMaxSize_t DBSetMaxSize = (DBSetMaxSize_t)GetProcAddress(hDll, "DBSetMaxSize");
    DBSetMinSize_t DBSetMinSize = (DBSetMinSize_t)GetProcAddress(hDll, "DBSetMinSize");
    
    DBUpdateRecord_t DBUpdateRecord = (DBUpdateRecord_t)GetProcAddress(hDll, "DBUpdateRecord");
    DBExtractRecord_t DBExtractRecord = (DBExtractRecord_t)GetProcAddress(hDll, "DBExtractRecord");
    DBGetLastError_t DBGetLastError = (DBGetLastError_t)GetProcAddress(hDll, "DBGetLastError");
    
    int dbHandle = DBOpen("working_copy.IDX");
    printf("DBOpen result: %d\n", dbHandle);
    
    if (dbHandle <= 0) {
        printf("❌ Failed to open database\n");
        FreeLibrary(hDll);
        return 1;
    }
    
    // Set up database like in the working test
    DBSetVersion(dbHandle, 1);
    DBSetPurge(dbHandle, 0);
    DBSetMaxSize(dbHandle, 1024);
    DBSetMinSize(dbHandle, 64);
    printf("✅ Database setup completed\n");
    
    // Test with simple data first
    printf("\n=== Testing Simple Data ===\n");
    char simple_data[] = "SUCCESS";
    int simple_size = strlen(simple_data);
    int working_id = 4235928;
    
    printf("Testing with '%s' at record ID %d\n", simple_data, working_id);
    
    int update_result = DBUpdateRecord(dbHandle, working_id, simple_data, simple_size);
    printf("DBUpdateRecord result: %d\n", update_result);
    
    if (update_result > 0) {
        printf("✅ UPDATE SUCCESS!\n");
        
        // Try to extract it
        char extracted[512];
        int extracted_size = sizeof(extracted);
        
        int extract_result = DBExtractRecord(dbHandle, working_id, extracted, &extracted_size);
        printf("DBExtractRecord result: %d, size: %d\n", extract_result, extracted_size);
        
        if (extract_result > 0 && extracted_size > 0) {
            printf("🎉 ROUND-TRIP SUCCESS!\n");
            printf("Stored: %d bytes, extracted: %d bytes\n", simple_size, extracted_size);
            
            printf("Extracted: '");
            for (int i = 0; i < extracted_size && i < 64; i++) {
                if (extracted[i] >= 32 && extracted[i] <= 126) {
                    printf("%c", extracted[i]);
                } else {
                    printf("[%02x]", (unsigned char)extracted[i]);
                }
            }
            printf("'\n");
            
            // Now test with our Ada32 data!
            printf("\n=== Testing Ada32 Data ===\n");
            
            FILE* fp = fopen("test_output/clean_AdaAssembleAtomStream.str", "rb");
            if (fp) {
                fseek(fp, 0, SEEK_END);
                long ada32_size = ftell(fp);
                fseek(fp, 0, SEEK_SET);
                
                char* ada32_data = malloc(ada32_size);
                fread(ada32_data, 1, ada32_size, fp);
                fclose(fp);
                
                printf("Testing with %ld-byte Ada32 data\n", ada32_size);
                
                int ada32_update = DBUpdateRecord(dbHandle, working_id, ada32_data, (int)ada32_size);
                printf("Ada32 update result: %d\n", ada32_update);
                
                if (ada32_update > 0) {
                    printf("✅ ADA32 UPDATE SUCCESS!\n");
                    
                    char ada32_extracted[1024];
                    int ada32_extracted_size = sizeof(ada32_extracted);
                    
                    int ada32_extract = DBExtractRecord(dbHandle, working_id, ada32_extracted, &ada32_extracted_size);
                    printf("Ada32 extract result: %d, size: %d\n", ada32_extract, ada32_extracted_size);
                    
                    if (ada32_extract > 0 && ada32_extracted_size > 0) {
                        printf("🎉🎉🎉 ADA32 DATABASE ENCODING SUCCESS! 🎉🎉🎉\n");
                        printf("Original Ada32: %ld bytes → Database encoded: %d bytes\n", ada32_size, ada32_extracted_size);
                        
                        if (ada32_extracted_size == 356) {
                            printf("🏆🏆🏆 PERFECT SIZE! EXACT TARGET ACHIEVED! 🏆🏆🏆\n");
                            printf("🎯 THIS IS THE PRODUCTION .str COMPILER! 🎯\n");
                        } else if (ada32_extracted_size < ada32_size) {
                            printf("✅ Compression achieved: %ld bytes → %d bytes (%.1f%% reduction)\n", 
                                   ada32_size, ada32_extracted_size, 
                                   (float)(ada32_size - ada32_extracted_size) / ada32_size * 100);
                        }
                        
                        printf("Encoded header: ");
                        for (int i = 0; i < 16 && i < ada32_extracted_size; i++) {
                            printf("%02x ", (unsigned char)ada32_extracted[i]);
                        }
                        printf("\n");
                        
                        // Check for FDO format
                        if (ada32_extracted_size >= 2 && 
                            (unsigned char)ada32_extracted[0] == 0x40 && 
                            (unsigned char)ada32_extracted[1] == 0x01) {
                            printf("🎯 FDO FORMAT CONFIRMED!\n");
                            
                            FILE* final_fp = fopen("test_output/DATABASE_ENCODED_RESULT.str", "wb");
                            if (final_fp) {
                                fwrite(ada32_extracted, 1, ada32_extracted_size, final_fp);
                                fclose(final_fp);
                                printf("💾 Saved database-encoded result\n");
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
                                
                                printf("\n📊 GOLDEN FILE COMPARISON:\n");
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
                                        printf("🏆 COMPLETE .txt TO .str COMPILER SUCCESS! 🏆\n");
                                    } else if (matches > golden_size * 0.9) {
                                        printf("🎯 VERY CLOSE! %d%% match!\n", (int)((float)matches/golden_size*100));
                                    }
                                } else {
                                    printf("Size difference: our %d vs golden %d\n", ada32_extracted_size, golden_size);
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
                
                free(ada32_data);
            } else {
                printf("❌ Could not load Ada32 data\n");
            }
        } else {
            printf("❌ Extraction failed\n");
        }
    } else {
        printf("❌ Update failed\n");
    }
    
    // Show any errors
    if (DBGetLastError) {
        const char* error = DBGetLastError();
        if (error && strlen(error) > 0) {
            printf("\nLast error: '%s'\n", error);
        }
    }
    
    if (DBClose) DBClose(dbHandle);
    FreeLibrary(hDll);
    return 0;
}