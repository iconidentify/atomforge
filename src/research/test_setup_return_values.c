/*
 * Focus on setup function return values and what they mean
 */
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>

typedef int (__stdcall *DBOpen_t)(const char* filename);
typedef int (__stdcall *DBClose_t)(int handle);
typedef int (__stdcall *DBCreate_t)(const char* filename);

int main() {
    printf("=== Analyzing Setup Function Return Values ===\n");
    
    HMODULE hDll = LoadLibrary("Dbaol32.dll");
    if (!hDll) {
        printf("❌ Failed to load Dbaol32.dll\n");
        return 1;
    }
    
    DBOpen_t DBOpen = (DBOpen_t)GetProcAddress(hDll, "DBOpen");
    DBClose_t DBClose = (DBClose_t)GetProcAddress(hDll, "DBClose");
    DBCreate_t DBCreate = (DBCreate_t)GetProcAddress(hDll, "DBCreate");
    
    void* DBSetVersion = GetProcAddress(hDll, "DBSetVersion");
    void* DBSetPurge = GetProcAddress(hDll, "DBSetPurge");
    void* DBSetMaxSize = GetProcAddress(hDll, "DBSetMaxSize");
    void* DBSetMinSize = GetProcAddress(hDll, "DBSetMinSize");
    
    void* DBExtractRecord = GetProcAddress(hDll, "DBExtractRecord");
    void* DBUpdateRecord = GetProcAddress(hDll, "DBUpdateRecord");
    void* DBAddRecord = GetProcAddress(hDll, "DBAddRecord");
    
    printf("✅ All functions loaded\n");
    
    // Test 1: Existing database
    printf("\n🔍 TESTING WITH EXISTING DATABASE\n");
    int mainHandle = DBOpen("golden_tests/main.IDX");
    printf("DBOpen(main.IDX): %d\n", mainHandle);
    
    if (mainHandle > 0) {
        printf("\nTesting different setup parameter values:\n");
        
        // Test DBSetVersion with different values
        if (DBSetVersion) {
            for (int ver = 0; ver <= 3; ver++) {
                int ver_result = ((int (__stdcall *)(int, int))DBSetVersion)(mainHandle, ver);
                printf("DBSetVersion(%d): %d", ver, ver_result);
                if (ver_result == 0) printf(" ❌ FAILED");
                else if (ver_result == mainHandle) printf(" ✅ SAME HANDLE");
                else printf(" 🔄 NEW HANDLE");
                printf("\n");
            }
        }
        
        // Test DBSetPurge with different values
        if (DBSetPurge) {
            for (int purge = 0; purge <= 2; purge++) {
                int purge_result = ((int (__stdcall *)(int, int))DBSetPurge)(mainHandle, purge);
                printf("DBSetPurge(%d): %d", purge, purge_result);
                if (purge_result == 0) printf(" ❌ FAILED");
                else if (purge_result == mainHandle) printf(" ✅ SAME HANDLE");
                else printf(" 🔄 NEW HANDLE");
                printf("\n");
            }
        }
        
        DBClose(mainHandle);
    }
    
    // Test 2: Fresh database with systematic setup
    printf("\n🔍 TESTING WITH FRESH DATABASE\n");
    const char* fresh_db = "setup_test.idx";
    remove(fresh_db);
    
    int create_result = DBCreate(fresh_db);
    printf("DBCreate: %d\n", create_result);
    
    if (create_result > 0) {
        int freshHandle = DBOpen(fresh_db);
        printf("DBOpen(fresh): %d\n", freshHandle);
        
        if (freshHandle > 0) {
            printf("\nSystematic setup sequence:\n");
            
            // Try to find the CORRECT setup sequence
            int workingHandle = freshHandle;
            
            // Sequence 1: Version first
            if (DBSetVersion) {
                int v1 = ((int (__stdcall *)(int, int))DBSetVersion)(workingHandle, 1);
                printf("Step 1 - DBSetVersion(1): %d\n", v1);
                if (v1 > 0) workingHandle = v1;
            }
            
            // Try add record after version setup
            if (DBAddRecord) {
                char test1[] = "AFTER_VERSION";
                int test1_size = strlen(test1);
                int new_id1 = 0;
                
                int add1 = ((int (__stdcall *)(int, void*, int, int*))DBAddRecord)(workingHandle, test1, test1_size, &new_id1);
                printf("Add after version: result=%d, newId=%d\n", add1, new_id1);
                
                if (add1 > 0) {
                    printf("✅ SUCCESS after DBSetVersion!\n");
                } else {
                    // Continue with more setup
                    if (DBSetPurge) {
                        int p1 = ((int (__stdcall *)(int, int))DBSetPurge)(workingHandle, 0);
                        printf("Step 2 - DBSetPurge(0): %d\n", p1);
                        if (p1 > 0) workingHandle = p1;
                        
                        // Try add again
                        int add2 = ((int (__stdcall *)(int, void*, int, int*))DBAddRecord)(workingHandle, test1, test1_size, &new_id1);
                        printf("Add after purge: result=%d, newId=%d\n", add2, new_id1);
                        
                        if (add2 > 0) {
                            printf("✅ SUCCESS after DBSetPurge!\n");
                        } else {
                            // Continue with size setup
                            if (DBSetMaxSize && DBSetMinSize) {
                                int max1 = ((int (__stdcall *)(int, int))DBSetMaxSize)(workingHandle, 1024);
                                printf("Step 3 - DBSetMaxSize(1024): %d\n", max1);
                                if (max1 > 0) workingHandle = max1;
                                
                                int min1 = ((int (__stdcall *)(int, int))DBSetMinSize)(workingHandle, 64);
                                printf("Step 4 - DBSetMinSize(64): %d\n", min1);
                                if (min1 > 0) workingHandle = min1;
                                
                                // Try add after full setup
                                int add3 = ((int (__stdcall *)(int, void*, int, int*))DBAddRecord)(workingHandle, test1, test1_size, &new_id1);
                                printf("Add after full setup: result=%d, newId=%d\n", add3, new_id1);
                                
                                if (add3 > 0) {
                                    printf("✅ SUCCESS after full setup!\n");
                                    
                                    // Try to read it back
                                    char read_buffer[512];
                                    int read_size = sizeof(read_buffer);
                                    
                                    int read_result = ((int (__stdcall *)(int, int, void*, int*))DBExtractRecord)(workingHandle, new_id1, read_buffer, &read_size);
                                    printf("Read back: result=%d, size=%d\n", read_result, read_size);
                                    
                                    if (read_result > 0) {
                                        printf("🎉🎉🎉 COMPLETE SUCCESS! 🎉🎉🎉\n");
                                        printf("Required setup sequence found!\n");
                                        printf("Final working handle: %d\n", workingHandle);
                                        
                                        printf("Data: ");
                                        for (int i = 0; i < read_size && i < 32; i++) {
                                            if (read_buffer[i] >= 32 && read_buffer[i] <= 126) {
                                                printf("%c", read_buffer[i]);
                                            } else {
                                                printf("[%02x]", (unsigned char)read_buffer[i]);
                                            }
                                        }
                                        printf("\n");
                                    }
                                }
                            }
                        }
                    }
                }
            }
            
            DBClose(workingHandle);
        }
        
        remove(fresh_db);
    }
    
    printf("\n=== ANALYSIS COMPLETE ===\n");
    printf("Key findings:\n");
    printf("- Setup functions returning 0 = FAILED\n");
    printf("- Setup functions returning handle = SUCCESS\n");
    printf("- May need specific setup sequence before add/read operations work\n");
    
    FreeLibrary(hDll);
    return 0;
}