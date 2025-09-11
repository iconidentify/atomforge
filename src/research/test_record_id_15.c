/*
 * Focused test for record ID 15 that appeared to work
 */
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>

typedef int (__stdcall *DBOpen_t)(const char* filename);
typedef int (__stdcall *DBClose_t)(int handle);
typedef int (__cdecl *DBUpdateRecord_t)(int handle, int recordId, void* data, int dataSize);
typedef int (__cdecl *DBExtractRecord_t)(int handle, int recordId, void* buffer, int* bufferSize);

int main() {
    printf("=== Testing Record ID 15 ===\n");
    
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
    
    int dbHandle = DBOpen("working_copy.IDX");
    printf("DBOpen result: %d\n", dbHandle);
    
    if (dbHandle <= 0) {
        printf("❌ Failed to open database\n");
        FreeLibrary(hDll);
        return 1;
    }
    
    // Test record ID 15 specifically
    printf("\n=== Testing Record ID 15 ===\n");
    char test_data[] = "TEST15";
    int test_size = strlen(test_data);
    
    int update_result = DBUpdateRecord(dbHandle, 15, test_data, test_size);
    printf("DBUpdateRecord(15) result: %d\n", update_result);
    
    if (update_result > 0) {
        printf("✅ UPDATE SUCCESS with ID 15!\n");
        
        char extracted[256];
        int extracted_size = sizeof(extracted);
        
        int extract_result = DBExtractRecord(dbHandle, 15, extracted, &extracted_size);
        printf("DBExtractRecord(15) result: %d, size: %d\n", extract_result, extracted_size);
        
        if (extract_result > 0 && extracted_size > 0) {
            printf("🎉 ROUND-TRIP SUCCESS!\n");
            printf("Stored: %d bytes, extracted: %d bytes\n", test_size, extracted_size);
            printf("Extracted: '");
            for (int i = 0; i < extracted_size && i < 32; i++) {
                if (extracted[i] >= 32 && extracted[i] <= 126) {
                    printf("%c", extracted[i]);
                } else {
                    printf("[%02x]", (unsigned char)extracted[i]);
                }
            }
            printf("'\n");
            
            // Now test with our Ada32 data
            printf("\n=== Testing Ada32 Data at ID 15 ===\n");
            
            FILE* fp = fopen("test_output/clean_AdaAssembleAtomStream.str", "rb");
            if (fp) {
                fseek(fp, 0, SEEK_END);
                long ada32_size = ftell(fp);
                fseek(fp, 0, SEEK_SET);
                
                char* ada32_data = malloc(ada32_size);
                fread(ada32_data, 1, ada32_size, fp);
                fclose(fp);
                
                printf("Testing %ld-byte Ada32 data at ID 15\n", ada32_size);
                
                int ada32_update = DBUpdateRecord(dbHandle, 15, ada32_data, (int)ada32_size);
                printf("Ada32 update result: %d\n", ada32_update);
                
                if (ada32_update > 0) {
                    printf("✅ ADA32 UPDATE SUCCESS!\n");
                    
                    char ada32_extracted[1024];
                    int ada32_extracted_size = sizeof(ada32_extracted);
                    
                    int ada32_extract = DBExtractRecord(dbHandle, 15, ada32_extracted, &ada32_extracted_size);
                    printf("Ada32 extract result: %d, size: %d\n", ada32_extract, ada32_extracted_size);
                    
                    if (ada32_extract > 0 && ada32_extracted_size > 0) {
                        printf("🎉🎉🎉 ADA32 ROUND-TRIP SUCCESS! 🎉🎉🎉\n");
                        printf("Original: %ld bytes → Database: %d bytes\n", ada32_size, ada32_extracted_size);
                        
                        if (ada32_extracted_size == 356) {
                            printf("🏆 PERFECT SIZE! EXACT TARGET ACHIEVED!\n");
                        } else {
                            printf("Size analysis: %d vs target 356\n", ada32_extracted_size);
                        }
                        
                        printf("Header: ");
                        for (int i = 0; i < 16 && i < ada32_extracted_size; i++) {
                            printf("%02x ", (unsigned char)ada32_extracted[i]);
                        }
                        printf("\n");
                        
                        // Check for FDO format
                        if (ada32_extracted_size >= 2 && 
                            (unsigned char)ada32_extracted[0] == 0x40 && 
                            (unsigned char)ada32_extracted[1] == 0x01) {
                            printf("🎯 FDO FORMAT CONFIRMED!\n");
                            
                            FILE* final_fp = fopen("test_output/ENCODED_BY_DATABASE.str", "wb");
                            if (final_fp) {
                                fwrite(ada32_extracted, 1, ada32_extracted_size, final_fp);
                                fclose(final_fp);
                                printf("💾 Saved database-encoded result\n");
                            }
                        }
                    }
                }
                
                free(ada32_data);
            }
        }
    } else {
        printf("❌ Still no success with ID 15\n");
        
        // Try a few more IDs around 15
        int test_ids[] = {14, 15, 16, 10, 20, 5, 1, 0};
        for (int i = 0; i < 8; i++) {
            int id = test_ids[i];
            int result = DBUpdateRecord(dbHandle, id, test_data, test_size);
            printf("ID %d: result=%d\n", id, result);
            if (result > 0) {
                printf("✅ Found working ID: %d\n", id);
                break;
            }
        }
    }
    
    if (DBClose) DBClose(dbHandle);
    FreeLibrary(hDll);
    return 0;
}