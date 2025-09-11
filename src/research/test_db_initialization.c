/*
 * Test if database functions need specific initialization or cursor positioning
 */
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>

typedef int (__stdcall *DBOpen_t)(const char* filename);
typedef int (__stdcall *DBClose_t)(int handle);

int main() {
    printf("=== Testing Database Initialization Requirements ===\n");
    
    HMODULE hDll = LoadLibrary("Dbaol32.dll");
    if (!hDll) {
        printf("❌ Failed to load Dbaol32.dll\n");
        return 1;
    }
    
    DBOpen_t DBOpen = (DBOpen_t)GetProcAddress(hDll, "DBOpen");
    DBClose_t DBClose = (DBClose_t)GetProcAddress(hDll, "DBClose");
    
    // Get ALL available functions
    void* DBExtractRecord = GetProcAddress(hDll, "DBExtractRecord");
    void* DBUpdateRecord = GetProcAddress(hDll, "DBUpdateRecord");
    void* DBGetInfo = GetProcAddress(hDll, "DBGetInfo");
    void* DBSetVersion = GetProcAddress(hDll, "DBSetVersion");
    void* DBSetPurge = GetProcAddress(hDll, "DBSetPurge");
    void* DBSetMaxSize = GetProcAddress(hDll, "DBSetMaxSize");
    void* DBSetMinSize = GetProcAddress(hDll, "DBSetMinSize");
    void* DBCopyResultSize = GetProcAddress(hDll, "DBCopyResultSize");
    void* DBInterpretGID = GetProcAddress(hDll, "DBInterpretGID");
    void* DBCopyThisRecord = GetProcAddress(hDll, "DBCopyThisRecord");
    
    int dbHandle = DBOpen("golden_tests/main.IDX");
    printf("DBOpen result: %d\n", dbHandle);
    
    if (dbHandle <= 0) {
        printf("❌ Failed to open database\n");
        FreeLibrary(hDll);
        return 1;
    }
    
    printf("\n=== Step 1: Try Every Setup Function in Sequence ===\n");
    
    if (DBSetVersion) {
        int ver_result = ((int (__stdcall *)(int, int))DBSetVersion)(dbHandle, 1);
        printf("DBSetVersion(1): %d\n", ver_result);
    }
    
    if (DBSetPurge) {
        int purge_result = ((int (__stdcall *)(int, int))DBSetPurge)(dbHandle, 0);
        printf("DBSetPurge(0): %d\n", purge_result);
    }
    
    if (DBSetMaxSize) {
        int max_result = ((int (__stdcall *)(int, int))DBSetMaxSize)(dbHandle, 2048);
        printf("DBSetMaxSize(2048): %d\n", max_result);
    }
    
    if (DBSetMinSize) {
        int min_result = ((int (__stdcall *)(int, int))DBSetMinSize)(dbHandle, 32);
        printf("DBSetMinSize(32): %d\n", min_result);
    }
    
    printf("\n=== Step 2: Try DBCopyResultSize to Get Record Count/Info ===\n");
    
    if (DBCopyResultSize) {
        int result_size = 0;
        int size_result = ((int (__stdcall *)(int, int*))DBCopyResultSize)(dbHandle, &result_size);
        printf("DBCopyResultSize: result=%d, size=%d\n", size_result, result_size);
        
        if (result_size > 0) {
            printf("✅ Got result size: %d - this might be record count or database size!\n", result_size);
        }
    }
    
    printf("\n=== Step 3: Try DBCopyThisRecord (No ID Required) ===\n");
    
    if (DBCopyThisRecord) {
        char buffer[1024];
        int buffer_size = sizeof(buffer);
        
        // Try __stdcall
        int copy_result = ((int (__stdcall *)(int, void*, int*))DBCopyThisRecord)(dbHandle, buffer, &buffer_size);
        printf("DBCopyThisRecord (__stdcall): result=%d, size=%d\n", copy_result, buffer_size);
        
        if (copy_result > 0 && buffer_size > 0 && buffer_size < 1000) {
            printf("✅ SUCCESS! Current record: %d bytes\n", buffer_size);
            printf("Data: ");
            for (int i = 0; i < 16 && i < buffer_size; i++) {
                printf("%02x ", (unsigned char)buffer[i]);
            }
            printf("\n");
            
            if (buffer_size >= 2 && (unsigned char)buffer[0] == 0x40 && (unsigned char)buffer[1] == 0x01) {
                printf("🎯 FDO FORMAT!\n");
                
                FILE* fp = fopen("test_output/copy_this_record_success.str", "wb");
                if (fp) {
                    fwrite(buffer, 1, buffer_size, fp);
                    fclose(fp);
                    printf("💾 Saved current record\n");
                }
            }
        } else {
            // Try __cdecl
            buffer_size = sizeof(buffer);
            int copy_result2 = ((int (__cdecl *)(int, void*, int*))DBCopyThisRecord)(dbHandle, buffer, &buffer_size);
            printf("DBCopyThisRecord (__cdecl): result=%d, size=%d\n", copy_result2, buffer_size);
        }
    }
    
    printf("\n=== Step 4: Try GID Interpretation with Known Values ===\n");
    
    if (DBInterpretGID) {
        // Try GIDs based on our file names: 32-105.str, 32-106.str, etc.
        int gids[] = {32, 105, 106, 117, 1, 2, 3};
        
        for (int i = 0; i < 7; i++) {
            int gid = gids[i];
            char gid_buffer[1024];
            int gid_size = sizeof(gid_buffer);
            
            int gid_result = ((int (__stdcall *)(int, int, void*, int*))DBInterpretGID)(dbHandle, gid, gid_buffer, &gid_size);
            
            if (gid_result > 0 && gid_size > 0 && gid_size < 1000) {
                printf("✅ GID %d: SUCCESS! %d bytes\n", gid, gid_size);
                
                if (gid_size == 356) {
                    printf("🏆 PERFECT SIZE!\n");
                    
                    char filename[256];
                    sprintf(filename, "test_output/gid_%d_success.str", gid);
                    FILE* fp = fopen(filename, "wb");
                    if (fp) {
                        fwrite(gid_buffer, 1, gid_size, fp);
                        fclose(fp);
                        printf("💾 Saved GID %d result\n", gid);
                    }
                }
            } else if (gid_result != 0) {
                printf("GID %d: result=%d, size=%d\n", gid, gid_result, gid_size);
            }
        }
    }
    
    printf("\n=== Step 5: After Setup, Try ExtractRecord Again ===\n");
    
    if (DBExtractRecord) {
        // Now that we've done setup, try extract again
        for (int id = 0; id <= 10; id++) {
            char extract_buffer[1024];
            int extract_size = sizeof(extract_buffer);
            
            int extract_result = ((int (__stdcall *)(int, int, void*, int*))DBExtractRecord)(dbHandle, id, extract_buffer, &extract_size);
            
            if (extract_result > 0 && extract_size > 0 && extract_size < 1000) {
                printf("✅ Extract ID %d: SUCCESS! %d bytes\n", id, extract_size);
                
                if (extract_size == 356) {
                    printf("🏆 PERFECT SIZE!\n");
                }
                
                // Now try update on this working ID
                char test_update[] = "AFTER_SETUP";
                int update_result = ((int (__stdcall *)(int, int, void*, int))DBUpdateRecord)(dbHandle, id, test_update, strlen(test_update));
                printf("Update ID %d after setup: %d\n", id, update_result);
                
                if (update_result > 0) {
                    printf("🎉 UPDATE SUCCESS AFTER SETUP!\n");
                    break;
                }
            }
        }
    }
    
    printf("\n=== INITIALIZATION TEST COMPLETE ===\n");
    
    if (DBClose) DBClose(dbHandle);
    FreeLibrary(hDll);
    return 0;
}