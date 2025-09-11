/*
 * Test if we can iterate through database records using different approaches
 */
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>

typedef int (__stdcall *DBOpen_t)(const char* filename);
typedef int (__stdcall *DBClose_t)(int handle);
typedef int (__stdcall *DBGetInfo_t)(int handle, void* info);

int main() {
    printf("=== Database Iteration and Discovery Test ===\n");
    
    HMODULE hDll = LoadLibrary("Dbaol32.dll");
    if (!hDll) {
        printf("❌ Failed to load Dbaol32.dll\n");
        return 1;
    }
    
    DBOpen_t DBOpen = (DBOpen_t)GetProcAddress(hDll, "DBOpen");
    DBClose_t DBClose = (DBClose_t)GetProcAddress(hDll, "DBClose");
    DBGetInfo_t DBGetInfo = (DBGetInfo_t)GetProcAddress(hDll, "DBGetInfo");
    
    void* DBExtractRecord = GetProcAddress(hDll, "DBExtractRecord");
    void* DBUpdateRecord = GetProcAddress(hDll, "DBUpdateRecord");
    void* DBInterpretGID = GetProcAddress(hDll, "DBInterpretGID");
    
    printf("Functions available:\n");
    printf("  DBExtractRecord: %s\n", DBExtractRecord ? "✅" : "❌");
    printf("  DBUpdateRecord: %s\n", DBUpdateRecord ? "✅" : "❌");
    printf("  DBInterpretGID: %s\n", DBInterpretGID ? "✅" : "❌");
    
    int dbHandle = DBOpen("golden_tests/main.IDX");
    printf("\nDBOpen result: %d\n", dbHandle);
    
    if (dbHandle <= 0) {
        printf("❌ Failed to open database\n");
        FreeLibrary(hDll);
        return 1;
    }
    
    // Get detailed database info
    if (DBGetInfo) {
        printf("\n=== Database Information Analysis ===\n");
        
        // Try different info buffer sizes to see what we get
        for (int size = 4; size <= 512; size *= 2) {
            char* info = malloc(size);
            memset(info, 0, size);
            
            int info_result = DBGetInfo(dbHandle, info);
            printf("DBGetInfo with %d-byte buffer: result=%d\n", size, info_result);
            
            if (info_result > 0) {
                printf("  Data: ");
                for (int i = 0; i < 32 && i < size; i++) {
                    printf("%02x ", (unsigned char)info[i]);
                }
                printf("\n");
                
                // Check if this looks like record count or metadata
                int* int_data = (int*)info;
                printf("  As integers: ");
                for (int i = 0; i < 8 && i < size/4; i++) {
                    printf("%d ", int_data[i]);
                }
                printf("\n");
            }
            
            free(info);
        }
    }
    
    printf("\n=== Testing Sequential Record Access ===\n");
    
    // Maybe records are numbered sequentially from 1 or 0
    char buffer[1024];
    int buffer_size;
    int found_records = 0;
    
    printf("Testing records 0-100 sequentially:\n");
    for (int id = 0; id <= 100 && found_records < 5; id++) {
        buffer_size = sizeof(buffer);
        
        // Try __stdcall DBExtractRecord
        int result = ((int (__stdcall *)(int, int, void*, int*))DBExtractRecord)(dbHandle, id, buffer, &buffer_size);
        
        if (result > 0 && buffer_size > 0 && buffer_size < 1000) {
            printf("✅ Record %d: %d bytes\n", id, buffer_size);
            found_records++;
            
            if (buffer_size >= 2 && (unsigned char)buffer[0] == 0x40 && (unsigned char)buffer[1] == 0x01) {
                printf("   🎯 FDO FORMAT!\n");
            }
            
            printf("   Header: ");
            for (int i = 0; i < 16 && i < buffer_size; i++) {
                printf("%02x ", (unsigned char)buffer[i]);
            }
            printf("\n");
        }
    }
    
    if (found_records == 0) {
        printf("No records found in sequential scan 0-100\n");
        
        printf("\n=== Testing GID Interpretation ===\n");
        
        if (DBInterpretGID) {
            // Try GID values that might make sense
            // 32-105.str might mean GID 32, subrecord 105
            int test_gids[] = {32, 105, 1, 2, 3, 100, 1000};
            
            for (int i = 0; i < 7; i++) {
                int gid = test_gids[i];
                buffer_size = sizeof(buffer);
                
                int gid_result = ((int (__stdcall *)(int, int, void*, int*))DBInterpretGID)(dbHandle, gid, buffer, &buffer_size);
                
                if (gid_result > 0 && buffer_size > 0 && buffer_size < 1000) {
                    printf("✅ GID %d: %d bytes\n", gid, buffer_size);
                    
                    if (buffer_size == 356) {
                        printf("   🏆 PERFECT SIZE!\n");
                        
                        char filename[256];
                        sprintf(filename, "test_output/gid_%d_result.str", gid);
                        FILE* fp = fopen(filename, "wb");
                        if (fp) {
                            fwrite(buffer, 1, buffer_size, fp);
                            fclose(fp);
                            printf("   💾 Saved to %s\n", filename);
                        }
                    }
                }
            }
        }
    }
    
    printf("\n=== Testing Update on Any Working Record ===\n");
    
    // If we found any readable record, try to update it
    if (found_records > 0) {
        printf("Found %d readable records. Now testing updates...\n", found_records);
        
        // Test update on record ID 0 (if it was readable)
        char test_data[] = "TEST123";
        int test_size = strlen(test_data);
        
        for (int test_id = 0; test_id <= 5; test_id++) {
            int update_result = ((int (__stdcall *)(int, int, void*, int))DBUpdateRecord)(dbHandle, test_id, test_data, test_size);
            printf("Update record %d: result=%d\n", test_id, update_result);
            
            if (update_result > 0) {
                printf("✅ UPDATE SUCCESS on record %d!\n", test_id);
                
                // Verify the update
                buffer_size = sizeof(buffer);
                int verify_result = ((int (__stdcall *)(int, int, void*, int*))DBExtractRecord)(dbHandle, test_id, buffer, &buffer_size);
                
                if (verify_result > 0) {
                    printf("✅ Verification read success: %d bytes\n", buffer_size);
                    printf("Data: ");
                    for (int i = 0; i < buffer_size && i < 32; i++) {
                        if (buffer[i] >= 32 && buffer[i] <= 126) {
                            printf("%c", buffer[i]);
                        } else {
                            printf("[%02x]", (unsigned char)buffer[i]);
                        }
                    }
                    printf("\n");
                    
                    printf("\n🎉🎉🎉 COMPLETE SUCCESS! READ AND WRITE WORKING! 🎉🎉🎉\n");
                    break;
                }
            }
        }
    } else {
        printf("No readable records found to test updates on.\n");
        printf("💡 This suggests either:\n");
        printf("   1. Different function signatures needed\n");
        printf("   2. Database requires specific initialization\n");
        printf("   3. Records are indexed differently than expected\n");
    }
    
    if (DBClose) DBClose(dbHandle);
    FreeLibrary(hDll);
    return 0;
}