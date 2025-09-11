/*
 * Test database functions with existing main.IDX file
 */
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>

typedef int (__stdcall *DBOpen_t)(const char* filename);
typedef int (__stdcall *DBClose_t)(int handle);
typedef int (__stdcall *DBAddRecord_t)(int handle, void* data, int dataSize, int* recordId);
typedef int (__stdcall *DBExtractRecord_t)(int handle, int recordId, void* buffer, int* bufferSize);
typedef int (__stdcall *DBGetInfo_t)(int handle, void* info);
typedef const char* (__stdcall *DBGetLastError_t)(void);

int main() {
    printf("=== Testing Database Functions with Existing main.IDX ===\n");
    
    HMODULE hDbaol = LoadLibrary("Dbaol32.dll");
    if (!hDbaol) {
        printf("❌ Failed to load Dbaol32.dll\n");
        return 1;
    }
    
    DBOpen_t DBOpen = (DBOpen_t)GetProcAddress(hDbaol, "DBOpen");
    DBClose_t DBClose = (DBClose_t)GetProcAddress(hDbaol, "DBClose");
    DBAddRecord_t DBAddRecord = (DBAddRecord_t)GetProcAddress(hDbaol, "DBAddRecord");
    DBExtractRecord_t DBExtractRecord = (DBExtractRecord_t)GetProcAddress(hDbaol, "DBExtractRecord");
    DBGetInfo_t DBGetInfo = (DBGetInfo_t)GetProcAddress(hDbaol, "DBGetInfo");
    DBGetLastError_t DBGetLastError = (DBGetLastError_t)GetProcAddress(hDbaol, "DBGetLastError");
    
    printf("Functions loaded:\n");
    printf("DBOpen: %s\n", DBOpen ? "✅" : "❌");
    printf("DBAddRecord: %s\n", DBAddRecord ? "✅" : "❌");
    printf("DBExtractRecord: %s\n", DBExtractRecord ? "✅" : "❌");
    
    if (!DBOpen) {
        printf("❌ Cannot test without DBOpen\n");
        FreeLibrary(hDbaol);
        return 1;
    }
    
    // Try opening the existing database
    const char* db_path = "golden_tests/main.IDX";
    printf("\nAttempting to open existing database: %s\n", db_path);
    
    int dbHandle = DBOpen(db_path);
    printf("DBOpen result: %d\n", dbHandle);
    
    if (dbHandle > 0) {
        printf("✅ Successfully opened existing database!\n");
        
        // Try to get database info
        if (DBGetInfo) {
            char info[1024] = {0};
            int info_result = DBGetInfo(dbHandle, info);
            printf("DBGetInfo result: %d\n", info_result);
            if (info_result > 0 && strlen(info) > 0) {
                printf("Database info: %s\n", info);
            }
        }
        
        // Try to extract the known record (32-105) - record ID 335544363
        if (DBExtractRecord) {
            printf("\nTesting extraction of known record (32-105)...\n");
            char extracted_data[1024];
            int extracted_size = sizeof(extracted_data);
            
            // We know from previous analysis that record 335544363 is 32-105
            int record_id = 335544363;
            int extract_result = DBExtractRecord(dbHandle, record_id, extracted_data, &extracted_size);
            printf("DBExtractRecord(ID=%d) result: %d, size: %d\n", record_id, extract_result, extracted_size);
            
            if (extract_result > 0 && extracted_size > 0) {
                printf("🎯 EXTRACTION SUCCESS!\n");
                printf("Extracted %d bytes\n", extracted_size);
                printf("First 16 bytes: ");
                for (int i = 0; i < 16 && i < extracted_size; i++) {
                    printf("%02x ", (unsigned char)extracted_data[i]);
                }
                printf("\n");
                
                // Check if it's FDO format
                if (extracted_size >= 2 && (unsigned char)extracted_data[0] == 0x40 && (unsigned char)extracted_data[1] == 0x01) {
                    printf("✅ FDO format confirmed!\n");
                    printf("Size: %d bytes\n", extracted_size);
                    
                    if (extracted_size == 356) {
                        printf("🎉 PERFECT! This matches our target size!\n");
                        
                        // Save this as reference
                        FILE* out_fp = fopen("test_output/db_extracted_reference.str", "wb");
                        if (out_fp) {
                            fwrite(extracted_data, 1, extracted_size, out_fp);
                            fclose(out_fp);
                            printf("💾 Saved reference extraction\n");
                        }
                        
                        // Now the key test: Can we add our raw data and get the same encoding?
                        if (DBAddRecord) {
                            printf("\n🔧 Testing save encoding with our raw data...\n");
                            
                            // Load our raw Ada32 output
                            FILE* fp = fopen("test_output/clean_AdaAssembleAtomStream.str", "rb");
                            if (fp) {
                                fseek(fp, 0, SEEK_END);
                                long raw_size = ftell(fp);
                                fseek(fp, 0, SEEK_SET);
                                
                                char* raw_data = malloc(raw_size);
                                fread(raw_data, 1, raw_size, fp);
                                fclose(fp);
                                
                                printf("Loaded %ld-byte raw data\n", raw_size);
                                
                                // Try to add it
                                int new_record_id = 0;
                                int add_result = DBAddRecord(dbHandle, raw_data, (int)raw_size, &new_record_id);
                                printf("DBAddRecord result: %d, new ID: %d\n", add_result, new_record_id);
                                
                                if (add_result > 0) {
                                    // Extract it back
                                    char new_extracted[1024];
                                    int new_size = sizeof(new_extracted);
                                    
                                    int new_extract = DBExtractRecord(dbHandle, new_record_id, new_extracted, &new_size);
                                    printf("Extract new record: %d, size: %d\n", new_extract, new_size);
                                    
                                    if (new_extract > 0 && new_size > 0) {
                                        printf("🎯 NEW RECORD ENCODED TO %d BYTES!\n", new_size);
                                        
                                        if (new_size == 356) {
                                            printf("🏆 PERFECT ENCODING ACHIEVED!\n");
                                        }
                                        
                                        // Save the encoded result
                                        FILE* encoded_fp = fopen("test_output/db_encoded_our_data.str", "wb");
                                        if (encoded_fp) {
                                            fwrite(new_extracted, 1, new_size, encoded_fp);
                                            fclose(encoded_fp);
                                            printf("💾 Saved our encoded data\n");
                                        }
                                    }
                                }
                                
                                free(raw_data);
                            } else {
                                printf("❌ Could not load raw data\n");
                            }
                        }
                    }
                }
            } else {
                printf("❌ Extraction failed\n");
                if (DBGetLastError) {
                    const char* error = DBGetLastError();
                    if (error) printf("Error: %s\n", error);
                }
            }
        }
        
        if (DBClose) DBClose(dbHandle);
    } else {
        printf("❌ Failed to open database\n");
        if (DBGetLastError) {
            const char* error = DBGetLastError();
            if (error) printf("Error: %s\n", error);
        }
    }
    
    FreeLibrary(hDbaol);
    return 0;
}