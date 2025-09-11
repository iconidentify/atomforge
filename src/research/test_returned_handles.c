/*
 * Test using the handles returned by setup functions instead of ignoring them
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

int main() {
    printf("=== Testing Setup Function Returned Handles ===\n");
    
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
    
    void* DBExtractRecord = GetProcAddress(hDll, "DBExtractRecord");
    void* DBUpdateRecord = GetProcAddress(hDll, "DBUpdateRecord");
    
    // Step 1: Open database
    int originalHandle = DBOpen("golden_tests/main.IDX");
    printf("Original DBOpen handle: %d\n", originalHandle);
    
    if (originalHandle <= 0) {
        printf("❌ Failed to open database\n");
        FreeLibrary(hDll);
        return 1;
    }
    
    // Step 2: Call setup functions and USE their returned handles
    printf("\n=== Using Returned Handles from Setup Functions ===\n");
    
    int currentHandle = originalHandle;
    
    if (DBSetVersion) {
        int newHandle1 = DBSetVersion(currentHandle, 1);
        printf("DBSetVersion(%d, 1) returned: %d\n", currentHandle, newHandle1);
        if (newHandle1 > 0 && newHandle1 != currentHandle) {
            printf("✅ Got NEW handle from DBSetVersion: %d\n", newHandle1);
            currentHandle = newHandle1; // USE the new handle!
        }
    }
    
    if (DBSetPurge) {
        int newHandle2 = DBSetPurge(currentHandle, 0);
        printf("DBSetPurge(%d, 0) returned: %d\n", currentHandle, newHandle2);
        if (newHandle2 > 0 && newHandle2 != currentHandle) {
            printf("✅ Got NEW handle from DBSetPurge: %d\n", newHandle2);
            currentHandle = newHandle2; // USE the new handle!
        }
    }
    
    if (DBSetMaxSize) {
        int newHandle3 = DBSetMaxSize(currentHandle, 1024);
        printf("DBSetMaxSize(%d, 1024) returned: %d\n", currentHandle, newHandle3);
        if (newHandle3 > 0 && newHandle3 != currentHandle) {
            printf("✅ Got NEW handle from DBSetMaxSize: %d\n", newHandle3);
            currentHandle = newHandle3; // USE the new handle!
        }
    }
    
    if (DBSetMinSize) {
        int newHandle4 = DBSetMinSize(currentHandle, 64);
        printf("DBSetMinSize(%d, 64) returned: %d\n", currentHandle, newHandle4);
        if (newHandle4 > 0 && newHandle4 != currentHandle) {
            printf("✅ Got NEW handle from DBSetMinSize: %d\n", newHandle4);
            currentHandle = newHandle4; // USE the new handle!
        }
    }
    
    printf("\nFinal working handle after setup: %d\n", currentHandle);
    
    // Step 3: Now try database operations with the FINAL handle
    printf("\n=== Testing Operations with Final Handle ===\n");
    
    if (DBExtractRecord) {
        printf("Testing DBExtractRecord with final handle %d:\n", currentHandle);
        
        for (int id = 0; id <= 10; id++) {
            char buffer[512];
            int buffer_size = sizeof(buffer);
            
            int result = ((int (__stdcall *)(int, int, void*, int*))DBExtractRecord)(currentHandle, id, buffer, &buffer_size);
            
            if (result > 0 && buffer_size > 0 && buffer_size < 500) {
                printf("✅ ID %d: SUCCESS! %d bytes\n", id, buffer_size);
                printf("   Data: ");
                for (int i = 0; i < 16 && i < buffer_size; i++) {
                    printf("%02x ", (unsigned char)buffer[i]);
                }
                printf("\n");
                
                if (buffer_size >= 2 && (unsigned char)buffer[0] == 0x40 && (unsigned char)buffer[1] == 0x01) {
                    printf("   🎯 FDO FORMAT!\n");
                    if (buffer_size == 356) {
                        printf("   🏆 PERFECT SIZE!\n");
                        
                        // Save successful extraction
                        char filename[256];
                        sprintf(filename, "test_output/extracted_with_final_handle_id_%d.str", id);
                        FILE* fp = fopen(filename, "wb");
                        if (fp) {
                            fwrite(buffer, 1, buffer_size, fp);
                            fclose(fp);
                            printf("   💾 Saved extraction\n");
                        }
                        
                        // Now try UPDATE on this working record!
                        printf("   🔄 Testing UPDATE on working record...\n");
                        
                        char test_data[] = "HANDLE_TEST";
                        int test_size = strlen(test_data);
                        
                        int update_result = ((int (__stdcall *)(int, int, void*, int))DBUpdateRecord)(currentHandle, id, test_data, test_size);
                        printf("   Update result: %d\n", update_result);
                        
                        if (update_result > 0) {
                            printf("   🎉🎉🎉 UPDATE SUCCESS WITH CORRECT HANDLE! 🎉🎉🎉\n");
                            
                            // Verify the update
                            char verify_buffer[512];
                            int verify_size = sizeof(verify_buffer);
                            int verify_result = ((int (__stdcall *)(int, int, void*, int*))DBExtractRecord)(currentHandle, id, verify_buffer, &verify_size);
                            
                            if (verify_result > 0) {
                                printf("   ✅ Verification: %d bytes\n", verify_size);
                                printf("   New data: ");
                                for (int j = 0; j < verify_size && j < 32; j++) {
                                    if (verify_buffer[j] >= 32 && verify_buffer[j] <= 126) {
                                        printf("%c", verify_buffer[j]);
                                    } else {
                                        printf("[%02x]", (unsigned char)verify_buffer[j]);
                                    }
                                }
                                printf("\n");
                                
                                printf("\n🏆🏆🏆 COMPLETE SUCCESS! READ AND WRITE WORKING! 🏆🏆🏆\n");
                                printf("Key insight: Must use handles returned by setup functions!\n");
                                break;
                            }
                        }
                    }
                }
            } else if (result != 0) {
                printf("   ID %d: result=%d, size=%d\n", id, result, buffer_size);
            }
        }
    }
    
    // Step 4: Test with fresh database too
    printf("\n=== Testing with Fresh Database ===\n");
    
    void* DBCreate = GetProcAddress(hDll, "DBCreate");
    if (DBCreate) {
        const char* fresh_db = "handle_test.idx";
        remove(fresh_db);
        
        int create_result = ((int (__stdcall *)(const char*))DBCreate)(fresh_db);
        printf("DBCreate result: %d\n", create_result);
        
        if (create_result > 0) {
            int fresh_handle = DBOpen(fresh_db);
            printf("Fresh DBOpen handle: %d\n", fresh_handle);
            
            if (fresh_handle > 0) {
                // Apply setup to fresh database
                int fresh_final_handle = fresh_handle;
                
                if (DBSetVersion) {
                    fresh_final_handle = DBSetVersion(fresh_final_handle, 1);
                    printf("Fresh DBSetVersion: %d\n", fresh_final_handle);
                }
                if (DBSetPurge) {
                    fresh_final_handle = DBSetPurge(fresh_final_handle, 0);
                    printf("Fresh DBSetPurge: %d\n", fresh_final_handle);
                }
                
                // Try to add a record to fresh database
                void* DBAddRecord = GetProcAddress(hDll, "DBAddRecord");
                if (DBAddRecord) {
                    char fresh_data[] = "FRESH_RECORD";
                    int fresh_size = strlen(fresh_data);
                    int new_record_id = 0;
                    
                    int add_result = ((int (__stdcall *)(int, void*, int, int*))DBAddRecord)(fresh_final_handle, fresh_data, fresh_size, &new_record_id);
                    printf("Fresh DBAddRecord: result=%d, newId=%d\n", add_result, new_record_id);
                    
                    if (add_result > 0) {
                        printf("🎉 ADD SUCCESS on fresh database!\n");
                        
                        // Try to read it back
                        char read_back[512];
                        int read_size = sizeof(read_back);
                        int read_result = ((int (__stdcall *)(int, int, void*, int*))DBExtractRecord)(fresh_final_handle, new_record_id, read_back, &read_size);
                        
                        if (read_result > 0) {
                            printf("✅ Read back success: %d bytes\n", read_size);
                            printf("Data: ");
                            for (int k = 0; k < read_size && k < 32; k++) {
                                if (read_back[k] >= 32 && read_back[k] <= 126) {
                                    printf("%c", read_back[k]);
                                } else {
                                    printf("[%02x]", (unsigned char)read_back[k]);
                                }
                            }
                            printf("\n");
                        }
                    }
                }
                
                DBClose(fresh_final_handle);
            }
        }
        
        remove(fresh_db);
    }
    
    // Clean up
    if (DBClose) DBClose(currentHandle);
    FreeLibrary(hDll);
    return 0;
}