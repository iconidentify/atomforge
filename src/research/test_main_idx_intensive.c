/*
 * Intensive testing of main.IDX where setup functions work
 */
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>

typedef int (__stdcall *DBOpen_t)(const char* filename);
typedef int (__stdcall *DBClose_t)(int handle);

int main() {
    printf("=== Intensive main.IDX Testing - Setup Works Here ===\n");
    
    HMODULE hDll = LoadLibrary("Dbaol32.dll");
    if (!hDll) {
        printf("❌ Failed to load Dbaol32.dll\n");
        return 1;
    }
    
    DBOpen_t DBOpen = (DBOpen_t)GetProcAddress(hDll, "DBOpen");
    DBClose_t DBClose = (DBClose_t)GetProcAddress(hDll, "DBClose");
    
    void* DBSetVersion = GetProcAddress(hDll, "DBSetVersion");
    void* DBSetPurge = GetProcAddress(hDll, "DBSetPurge");
    void* DBSetMaxSize = GetProcAddress(hDll, "DBSetMaxSize");
    void* DBSetMinSize = GetProcAddress(hDll, "DBSetMinSize");
    
    void* DBExtractRecord = GetProcAddress(hDll, "DBExtractRecord");
    void* DBUpdateRecord = GetProcAddress(hDll, "DBUpdateRecord");
    void* DBAddRecord = GetProcAddress(hDll, "DBAddRecord");
    void* DBCopyRecord = GetProcAddress(hDll, "DBCopyRecord");
    void* DBCopyThisRecord = GetProcAddress(hDll, "DBCopyThisRecord");
    void* DBInterpretGID = GetProcAddress(hDll, "DBInterpretGID");
    
    int mainHandle = DBOpen("golden_tests/main.IDX");
    printf("DBOpen(main.IDX): %d\n", mainHandle);
    
    if (mainHandle <= 0) {
        printf("❌ Failed to open main.IDX\n");
        FreeLibrary(hDll);
        return 1;
    }
    
    printf("\n=== Setup sequence on main.IDX (we know this works) ===\n");
    
    int workingHandle = mainHandle;
    
    // Apply all setup in sequence
    if (DBSetVersion) {
        workingHandle = ((int (__stdcall *)(int, int))DBSetVersion)(workingHandle, 1);
        printf("After DBSetVersion: %d\n", workingHandle);
    }
    
    if (DBSetPurge) {
        workingHandle = ((int (__stdcall *)(int, int))DBSetPurge)(workingHandle, 0);
        printf("After DBSetPurge: %d\n", workingHandle);
    }
    
    if (DBSetMaxSize) {
        workingHandle = ((int (__stdcall *)(int, int))DBSetMaxSize)(workingHandle, 2048);
        printf("After DBSetMaxSize: %d\n", workingHandle);
    }
    
    if (DBSetMinSize) {
        workingHandle = ((int (__stdcall *)(int, int))DBSetMinSize)(workingHandle, 32);
        printf("After DBSetMinSize: %d\n", workingHandle);
    }
    
    printf("Final working handle: %d\n", workingHandle);
    
    // Now test EVERY read function extensively with this properly set up handle
    printf("\n=== Testing ALL Read Functions with Setup Handle ===\n");
    
    int successful_reads = 0;
    
    // Test range of IDs that might exist
    int test_range[] = {0, 1, 2, 3, 4, 5, 10, 15, 20, 25, 30, 32, 35, 40, 50, 64, 65, 100, 105, 106, 117, 200, 500, 1000};
    int range_size = sizeof(test_range) / sizeof(test_range[0]);
    
    for (int i = 0; i < range_size; i++) {
        int test_id = test_range[i];
        
        // Test DBExtractRecord
        if (DBExtractRecord) {
            char buffer[1024];
            int buffer_size = sizeof(buffer);
            
            int extract_result = ((int (__stdcall *)(int, int, void*, int*))DBExtractRecord)(workingHandle, test_id, buffer, &buffer_size);
            
            if (extract_result > 0 && buffer_size > 0 && buffer_size < 1000) {
                printf("✅ DBExtractRecord ID %d: %d bytes\n", test_id, buffer_size);
                successful_reads++;
                
                printf("   Data: ");
                for (int j = 0; j < 16 && j < buffer_size; j++) {
                    printf("%02x ", (unsigned char)buffer[j]);
                }
                printf("\n");
                
                if (buffer_size >= 2 && (unsigned char)buffer[0] == 0x40 && (unsigned char)buffer[1] == 0x01) {
                    printf("   🎯 FDO FORMAT!\n");
                    if (buffer_size == 356) {
                        printf("   🏆 PERFECT SIZE - TARGET FOUND!\n");
                        
                        // Save this perfect result
                        char filename[256];
                        sprintf(filename, "test_output/perfect_extract_id_%d.str", test_id);
                        FILE* fp = fopen(filename, "wb");
                        if (fp) {
                            fwrite(buffer, 1, buffer_size, fp);
                            fclose(fp);
                            printf("   💾 Saved perfect extraction\n");
                        }
                        
                        // NOW TEST UPDATE/ADD on this working record!
                        printf("   🔄 TESTING UPDATE ON WORKING RECORD %d\n", test_id);
                        
                        char update_data[] = "MAIN_IDX_UPDATE";
                        int update_size = strlen(update_data);
                        
                        int update_result = ((int (__stdcall *)(int, int, void*, int))DBUpdateRecord)(workingHandle, test_id, update_data, update_size);
                        printf("   Update result: %d\n", update_result);
                        
                        if (update_result > 0) {
                            printf("   🎉🎉🎉 UPDATE SUCCESS ON MAIN.IDX! 🎉🎉🎉\n");
                            
                            // Verify the update
                            char verify_buffer[1024];
                            int verify_size = sizeof(verify_buffer);
                            int verify_result = ((int (__stdcall *)(int, int, void*, int*))DBExtractRecord)(workingHandle, test_id, verify_buffer, &verify_size);
                            
                            if (verify_result > 0) {
                                printf("   ✅ Verification: %d bytes\n", verify_size);
                                printf("   Updated data: ");
                                for (int k = 0; k < verify_size && k < 64; k++) {
                                    if (verify_buffer[k] >= 32 && verify_buffer[k] <= 126) {
                                        printf("%c", verify_buffer[k]);
                                    } else {
                                        printf("[%02x]", (unsigned char)verify_buffer[k]);
                                    }
                                }
                                printf("\n");
                                
                                printf("\n🏆🏆🏆 COMPLETE DATABASE R/W SUCCESS! 🏆🏆🏆\n");
                                printf("Working database: main.IDX\n");
                                printf("Working record ID: %d\n", test_id);
                                printf("Working handle: %d\n", workingHandle);
                                
                                goto success_found; // Break out of all loops
                            }
                        }
                    }
                }
            }
        }
        
        // Also test DBCopyRecord on the same ID
        if (DBCopyRecord) {
            char copy_buffer[1024];
            int copy_size = sizeof(copy_buffer);
            
            int copy_result = ((int (__stdcall *)(int, int, void*, int*))DBCopyRecord)(workingHandle, test_id, copy_buffer, &copy_size);
            
            if (copy_result > 0 && copy_size > 0 && copy_size < 1000) {
                printf("✅ DBCopyRecord ID %d: %d bytes\n", test_id, copy_size);
                successful_reads++;
            }
        }
    }
    
    success_found:
    
    // Test functions that don't need record IDs
    printf("\n=== Testing Functions Without Record IDs ===\n");
    
    if (DBCopyThisRecord) {
        char this_buffer[1024];
        int this_size = sizeof(this_buffer);
        
        int this_result = ((int (__stdcall *)(int, void*, int*))DBCopyThisRecord)(workingHandle, this_buffer, &this_size);
        printf("DBCopyThisRecord: result=%d, size=%d\n", this_result, this_size);
        
        if (this_result > 0 && this_size > 0 && this_size < 1000) {
            printf("✅ DBCopyThisRecord SUCCESS: %d bytes\n", this_size);
            
            if (this_size == 356) {
                printf("🏆 PERFECT SIZE!\n");
                
                FILE* fp = fopen("test_output/copy_this_record_success.str", "wb");
                if (fp) {
                    fwrite(this_buffer, 1, this_size, fp);
                    fclose(fp);
                    printf("💾 Saved DBCopyThisRecord result\n");
                }
            }
        }
    }
    
    // Test GID interpretation
    if (DBInterpretGID) {
        printf("\nTesting GID interpretation:\n");
        int gids[] = {32, 105, 106, 117};
        
        for (int g = 0; g < 4; g++) {
            int gid = gids[g];
            char gid_buffer[1024];
            int gid_size = sizeof(gid_buffer);
            
            int gid_result = ((int (__stdcall *)(int, int, void*, int*))DBInterpretGID)(workingHandle, gid, gid_buffer, &gid_size);
            
            if (gid_result > 0 && gid_size > 0 && gid_size < 1000) {
                printf("✅ GID %d: %d bytes\n", gid, gid_size);
                
                if (gid_size == 356) {
                    printf("🏆 PERFECT SIZE!\n");
                    
                    char gid_filename[256];
                    sprintf(gid_filename, "test_output/gid_%d_perfect.str", gid);
                    FILE* gid_fp = fopen(gid_filename, "wb");
                    if (gid_fp) {
                        fwrite(gid_buffer, 1, gid_size, gid_fp);
                        fclose(gid_fp);
                        printf("💾 Saved GID %d result\n", gid);
                    }
                }
            }
        }
    }
    
    printf("\n=== SUMMARY ===\n");
    printf("Total successful reads: %d\n", successful_reads);
    printf("Database: main.IDX (where setup functions work)\n");
    printf("Working handle: %d\n", workingHandle);
    
    if (successful_reads == 0) {
        printf("❌ Still no successful reads even with working setup\n");
        printf("This suggests either:\n");
        printf("1. Function signatures are still wrong\n");
        printf("2. Records are indexed completely differently\n");
        printf("3. Additional steps required beyond setup\n");
    } else {
        printf("✅ Found working read operations!\n");
    }
    
    if (DBClose) DBClose(workingHandle);
    FreeLibrary(hDll);
    return 0;
}