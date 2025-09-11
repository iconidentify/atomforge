/*
 * Try to understand the database structure and record system
 */
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>

typedef int (__stdcall *DBOpen_t)(const char* filename);
typedef int (__stdcall *DBClose_t)(int handle);
typedef int (__stdcall *DBExtractRecord_t)(int handle, int recordId, void* buffer, int* bufferSize);
typedef int (__stdcall *DBAddRecord_t)(int handle, void* data, int dataSize, int* recordId);
typedef int (__stdcall *DBGetInfo_t)(int handle, void* info);
typedef int (__stdcall *DBCreate_t)(const char* filename);
typedef const char* (__stdcall *DBGetLastError_t)(void);

int main() {
    printf("=== Understanding Database Structure ===\n");
    
    HMODULE hDll = LoadLibrary("Dbaol32.dll");
    if (!hDll) {
        printf("❌ Failed to load Dbaol32.dll\n");
        return 1;
    }
    
    DBOpen_t DBOpen = (DBOpen_t)GetProcAddress(hDll, "DBOpen");
    DBClose_t DBClose = (DBClose_t)GetProcAddress(hDll, "DBClose");
    DBExtractRecord_t DBExtractRecord = (DBExtractRecord_t)GetProcAddress(hDll, "DBExtractRecord");
    DBAddRecord_t DBAddRecord = (DBAddRecord_t)GetProcAddress(hDll, "DBAddRecord");
    DBGetInfo_t DBGetInfo = (DBGetInfo_t)GetProcAddress(hDll, "DBGetInfo");
    DBCreate_t DBCreate = (DBCreate_t)GetProcAddress(hDll, "DBCreate");
    DBGetLastError_t DBGetLastError = (DBGetLastError_t)GetProcAddress(hDll, "DBGetLastError");
    
    printf("Available functions:\n");
    printf("  DBOpen: %s\n", DBOpen ? "✅" : "❌");
    printf("  DBGetInfo: %s\n", DBGetInfo ? "✅" : "❌");
    printf("  DBAddRecord: %s\n", DBAddRecord ? "✅" : "❌");
    printf("  DBCreate: %s\n", DBCreate ? "✅" : "❌");
    printf("  DBGetLastError: %s\n", DBGetLastError ? "✅" : "❌");
    
    // Open the database
    int dbHandle = DBOpen("golden_tests/main.IDX");
    printf("\\nDBOpen result: %d\n", dbHandle);
    
    if (dbHandle <= 0) {
        printf("❌ Failed to open database\n");
        FreeLibrary(hDll);
        return 1;
    }
    
    // Try to get database info
    if (DBGetInfo) {
        printf("\\n=== Database Info ===\n");
        
        // Try different buffer sizes and types for info
        char info_buffer[1024];
        memset(info_buffer, 0, sizeof(info_buffer));
        
        int info_result = DBGetInfo(dbHandle, info_buffer);
        printf("DBGetInfo result: %d\n", info_result);
        
        if (info_result > 0) {
            printf("Info string: '%s'\n", info_buffer);
            printf("Info hex: ");
            for (int i = 0; i < 32; i++) {
                printf("%02x ", (unsigned char)info_buffer[i]);
            }
            printf("\n");
        } else {
            printf("DBGetInfo failed\n");
            if (DBGetLastError) {
                const char* error = DBGetLastError();
                if (error && strlen(error) > 0) {
                    printf("Error: %s\n", error);
                }
            }
        }
    }
    
    // Test if we can create a new database and add records to it
    if (DBCreate && DBAddRecord) {
        printf("\\n=== Testing Record Creation ===\n");
        
        const char* test_db = "test_creation.idx";
        remove(test_db);  // Remove if exists
        
        printf("Creating new database: %s\n", test_db);
        int create_result = DBCreate(test_db);
        printf("DBCreate result: %d\n", create_result);
        
        if (create_result > 0) {
            // Open the new database
            int newDbHandle = DBOpen(test_db);
            printf("DBOpen new database result: %d\n", newDbHandle);
            
            if (newDbHandle > 0) {
                // Try to add a simple record
                printf("Adding test record...\n");
                
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
                    
                    int new_record_id = 0;
                    int add_result = DBAddRecord(newDbHandle, raw_data, (int)raw_size, &new_record_id);
                    printf("DBAddRecord result: %d, new record ID: %d\n", add_result, new_record_id);
                    
                    if (add_result > 0) {
                        printf("✅ Successfully added record!\n");
                        
                        // Now try to extract it
                        char extracted_data[1024];
                        int extracted_size = sizeof(extracted_data);
                        
                        int extract_result = DBExtractRecord(newDbHandle, new_record_id, extracted_data, &extracted_size);
                        printf("DBExtractRecord result: %d, size: %d\n", extract_result, extracted_size);
                        
                        if (extract_result > 0 && extracted_size > 0) {
                            printf("🎉 SUCCESSFUL ROUND-TRIP!\n");
                            printf("Original size: %ld bytes\n", raw_size);
                            printf("Extracted size: %d bytes\n", extracted_size);
                            printf("Size difference: %ld bytes\n", raw_size - extracted_size);
                            
                            printf("First 16 bytes of extracted: ");
                            for (int i = 0; i < 16 && i < extracted_size; i++) {
                                printf("%02x ", (unsigned char)extracted_data[i]);
                            }
                            printf("\n");
                            
                            // Check if it got encoded to FDO format
                            if (extracted_size >= 2 && (unsigned char)extracted_data[0] == 0x40 && (unsigned char)extracted_data[1] == 0x01) {
                                printf("🎯 CONVERTED TO FDO FORMAT!\n");
                                
                                if (extracted_size == 356) {
                                    printf("🏆 PERFECT SIZE - ENCODING COMPLETE!\n");
                                } else {
                                    printf("⚠️  Size %d (target 356)\n", extracted_size);
                                }
                                
                                // Save the encoded result
                                FILE* out_fp = fopen("test_output/db_round_trip_result.str", "wb");
                                if (out_fp) {
                                    fwrite(extracted_data, 1, extracted_size, out_fp);
                                    fclose(out_fp);
                                    printf("💾 Saved encoded result\n");
                                }
                            } else {
                                printf("❌ Not FDO format (starts with %02x %02x)\n", 
                                       (unsigned char)extracted_data[0], (unsigned char)extracted_data[1]);
                            }
                        } else {
                            printf("❌ Extraction failed\n");
                        }
                    } else {
                        printf("❌ Failed to add record\n");
                        if (DBGetLastError) {
                            const char* error = DBGetLastError();
                            if (error && strlen(error) > 0) {
                                printf("Add error: %s\n", error);
                            }
                        }
                    }
                    
                    free(raw_data);
                } else {
                    printf("❌ Could not load raw data for testing\n");
                }
                
                if (DBClose) DBClose(newDbHandle);
            } else {
                printf("❌ Failed to open newly created database\n");
            }
        } else {
            printf("❌ Failed to create database\n");
            if (DBGetLastError) {
                const char* error = DBGetLastError();
                if (error && strlen(error) > 0) {
                    printf("Create error: %s\n", error);
                }
            }
        }
    }
    
    if (DBClose) DBClose(dbHandle);
    FreeLibrary(hDll);
    return 0;
}