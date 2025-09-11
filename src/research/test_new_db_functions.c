/*
 * Test the newly discovered database functions
 */
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>

typedef int (__stdcall *DBOpen_t)(const char* filename);
typedef int (__stdcall *DBClose_t)(int handle);
typedef int (__stdcall *DBGetInfo_t)(int handle, void* info);

// Newly discovered functions
typedef int (__stdcall *DBCopyRecord_t)(int handle, int recordId, void* buffer, int* bufferSize);
typedef int (__stdcall *DBCopyThisRecord_t)(int handle, void* buffer, int* bufferSize);
typedef int (__stdcall *DBExtractUndeletedRecord_t)(int handle, int recordId, void* buffer, int* bufferSize);
typedef int (__stdcall *DBInterpretGID_t)(int handle, int gid, void* buffer, int* bufferSize);
typedef int (__stdcall *DBSetVersion_t)(int handle, int version);
typedef int (__stdcall *DBSetPurge_t)(int handle, int purge);
typedef const char* (__stdcall *DBGetLastError_t)(void);

int main() {
    printf("=== Testing Newly Discovered Database Functions ===\n");
    
    HMODULE hDll = LoadLibrary("Dbaol32.dll");
    if (!hDll) {
        printf("❌ Failed to load Dbaol32.dll\n");
        return 1;
    }
    
    // Load all the new functions
    DBOpen_t DBOpen = (DBOpen_t)GetProcAddress(hDll, "DBOpen");
    DBClose_t DBClose = (DBClose_t)GetProcAddress(hDll, "DBClose");
    DBGetInfo_t DBGetInfo = (DBGetInfo_t)GetProcAddress(hDll, "DBGetInfo");
    
    DBCopyRecord_t DBCopyRecord = (DBCopyRecord_t)GetProcAddress(hDll, "DBCopyRecord");
    DBCopyThisRecord_t DBCopyThisRecord = (DBCopyThisRecord_t)GetProcAddress(hDll, "DBCopyThisRecord");
    DBExtractUndeletedRecord_t DBExtractUndeletedRecord = (DBExtractUndeletedRecord_t)GetProcAddress(hDll, "DBExtractUndeletedRecord");
    DBInterpretGID_t DBInterpretGID = (DBInterpretGID_t)GetProcAddress(hDll, "DBInterpretGID");
    DBSetVersion_t DBSetVersion = (DBSetVersion_t)GetProcAddress(hDll, "DBSetVersion");
    DBSetPurge_t DBSetPurge = (DBSetPurge_t)GetProcAddress(hDll, "DBSetPurge");
    DBGetLastError_t DBGetLastError = (DBGetLastError_t)GetProcAddress(hDll, "DBGetLastError");
    
    printf("New functions found:\n");
    printf("  DBCopyRecord: %s\n", DBCopyRecord ? "✅" : "❌");
    printf("  DBCopyThisRecord: %s\n", DBCopyThisRecord ? "✅" : "❌");
    printf("  DBExtractUndeletedRecord: %s\n", DBExtractUndeletedRecord ? "✅" : "❌");
    printf("  DBInterpretGID: %s\n", DBInterpretGID ? "✅" : "❌");
    printf("  DBSetVersion: %s\n", DBSetVersion ? "✅" : "❌");
    printf("  DBSetPurge: %s\n", DBSetPurge ? "✅" : "❌");
    
    // Open database
    int dbHandle = DBOpen("working_copy.IDX");
    printf("\\nDBOpen result: %d\n", dbHandle);
    
    if (dbHandle <= 0) {
        printf("❌ Failed to open database\n");
        FreeLibrary(hDll);
        return 1;
    }
    
    printf("✅ Database opened\n");
    
    // Test 1: Try DBExtractUndeletedRecord - this might be the key!
    if (DBExtractUndeletedRecord) {
        printf("\\n=== Testing DBExtractUndeletedRecord ===\n");
        
        // Try extracting records with this function instead
        int test_ids[] = {0, 1, 2, 3, 105, 106, 117, 1000};
        int num_tests = sizeof(test_ids) / sizeof(test_ids[0]);
        
        for (int i = 0; i < num_tests; i++) {
            int record_id = test_ids[i];
            char buffer[1024];
            int buffer_size = sizeof(buffer);
            
            int result = DBExtractUndeletedRecord(dbHandle, record_id, buffer, &buffer_size);
            
            if (result > 0 && buffer_size > 0) {
                printf("✅ ID %d: SUCCESS! Size: %d bytes\n", record_id, buffer_size);
                printf("   First 16 bytes: ");
                for (int j = 0; j < 16 && j < buffer_size; j++) {
                    printf("%02x ", (unsigned char)buffer[j]);
                }
                printf("\n");
                
                // Check for FDO format
                if (buffer_size >= 2 && (unsigned char)buffer[0] == 0x40 && (unsigned char)buffer[1] == 0x01) {
                    printf("   🎯 FDO FORMAT!\n");
                    if (buffer_size == 356) {
                        printf("   🎉 PERFECT SIZE!\n");
                        
                        // Save this record
                        FILE* fp = fopen("test_output/extracted_undeleted_record.str", "wb");
                        if (fp) {
                            fwrite(buffer, 1, buffer_size, fp);
                            fclose(fp);
                            printf("   💾 Saved successful extraction\n");
                        }
                        
                        // This proves extraction works! Now we need to figure out how to add/update
                        printf("\\n🎯 BREAKTHROUGH! Extraction works with DBExtractUndeletedRecord!\n");
                        break;
                    }
                }
            } else {
                printf("❌ ID %d: Failed (result=%d, size=%d)\n", record_id, result, buffer_size);
            }
        }
    }
    
    // Test 2: Try GID interpretation - maybe records are accessed by GID not ID
    if (DBInterpretGID) {
        printf("\\n=== Testing DBInterpretGID ===\n");
        
        // Try GID values that might correspond to our known records
        // 32-105 might mean GID 32, subrecord 105
        int test_gids[] = {32, 105, 117, 16, 9736, 32105, 32106, 32117};
        int num_gids = sizeof(test_gids) / sizeof(test_gids[0]);
        
        for (int i = 0; i < num_gids; i++) {
            int gid = test_gids[i];
            char buffer[1024];
            int buffer_size = sizeof(buffer);
            
            int result = DBInterpretGID(dbHandle, gid, buffer, &buffer_size);
            
            if (result > 0 && buffer_size > 0) {
                printf("✅ GID %d: SUCCESS! Size: %d bytes\n", gid, buffer_size);
                
                if (buffer_size == 356) {
                    printf("   🎉 PERFECT SIZE! This might be our 32-105 record!\n");
                    
                    FILE* fp = fopen("test_output/gid_interpreted_record.str", "wb");
                    if (fp) {
                        fwrite(buffer, 1, buffer_size, fp);
                        fclose(fp);
                        printf("   💾 Saved GID interpretation\n");
                    }
                }
            } else {
                printf("❌ GID %d: Failed (result=%d, size=%d)\n", gid, result, buffer_size);
            }
        }
    }
    
    // Test 3: Try setup functions - maybe these are needed before add/update works
    if (DBSetVersion && DBSetPurge) {
        printf("\\n=== Testing Database Setup Functions ===\n");
        
        // Try different version and purge settings
        int version_result = DBSetVersion(dbHandle, 1);
        printf("DBSetVersion(1) result: %d\n", version_result);
        
        int purge_result = DBSetPurge(dbHandle, 0);  // Disable purging
        printf("DBSetPurge(0) result: %d\n", purge_result);
        
        if (version_result > 0 || purge_result > 0) {
            printf("✅ Setup functions worked! Maybe now add/update will work?\n");
            
            // Try a simple update now that setup is done
            void* DBUpdateRecord = GetProcAddress(hDll, "DBUpdateRecord");
            if (DBUpdateRecord) {
                char simple_data[] = "SETUP_TEST";
                int simple_size = strlen(simple_data);
                int test_id = 888888;
                
                int update_result = ((int (__stdcall *)(int, int, void*, int))DBUpdateRecord)(dbHandle, test_id, simple_data, simple_size);
                printf("DBUpdateRecord after setup: %d\n", update_result);
                
                if (update_result > 0) {
                    printf("🎉 UPDATE WORKED AFTER SETUP!\n");
                }
            }
        }
    }
    
    // Show any error messages
    if (DBGetLastError) {
        const char* error = DBGetLastError();
        if (error && strlen(error) > 0) {
            printf("\\nLast error: %s\n", error);
        }
    }
    
    if (DBClose) DBClose(dbHandle);
    FreeLibrary(hDll);
    return 0;
}