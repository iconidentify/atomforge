/*
 * Test different parameter passing approaches for database functions
 */
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>

typedef int (__stdcall *DBOpen_t)(const char* filename);
typedef int (__stdcall *DBClose_t)(int handle);

int main() {
    printf("=== Testing Parameter Variations ===\n");
    
    HMODULE hDll = LoadLibrary("Dbaol32.dll");
    if (!hDll) {
        printf("❌ Failed to load Dbaol32.dll\n");
        return 1;
    }
    
    DBOpen_t DBOpen = (DBOpen_t)GetProcAddress(hDll, "DBOpen");
    DBClose_t DBClose = (DBClose_t)GetProcAddress(hDll, "DBClose");
    void* DBUpdateRecord = GetProcAddress(hDll, "DBUpdateRecord");
    
    if (!DBOpen || !DBUpdateRecord) {
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
    
    char test_data[] = "TEST";
    int test_size = 4;
    
    printf("\n=== Testing Different Signatures for DBUpdateRecord ===\n");
    
    // Signature 1: Standard assumed (handle, recordId, data, size)
    printf("Sig 1 (__stdcall): (handle, recordId, data, size)\n");
    for (int id = 1; id <= 5; id++) {
        int result = ((int (__stdcall *)(int, int, void*, int))DBUpdateRecord)(dbHandle, id, test_data, test_size);
        printf("  ID %d: %d\n", id, result);
    }
    
    // Signature 2: __cdecl (handle, recordId, data, size)
    printf("Sig 2 (__cdecl): (handle, recordId, data, size)\n");
    for (int id = 1; id <= 5; id++) {
        int result = ((int (__cdecl *)(int, int, void*, int))DBUpdateRecord)(dbHandle, id, test_data, test_size);
        printf("  ID %d: %d\n", id, result);
    }
    
    // Signature 3: Different parameter order (handle, data, size, recordId)
    printf("Sig 3 (__stdcall): (handle, data, size, recordId)\n");
    for (int id = 1; id <= 5; id++) {
        int result = ((int (__stdcall *)(int, void*, int, int))DBUpdateRecord)(dbHandle, test_data, test_size, id);
        printf("  ID %d: %d\n", id, result);
    }
    
    // Signature 4: __cdecl (handle, data, size, recordId)
    printf("Sig 4 (__cdecl): (handle, data, size, recordId)\n");
    for (int id = 1; id <= 5; id++) {
        int result = ((int (__cdecl *)(int, void*, int, int))DBUpdateRecord)(dbHandle, test_data, test_size, id);
        printf("  ID %d: %d\n", id, result);
    }
    
    // Signature 5: With pointer to size (handle, recordId, data, size*)
    printf("Sig 5 (__stdcall): (handle, recordId, data, size*)\n");
    for (int id = 1; id <= 5; id++) {
        int size_param = test_size;
        int result = ((int (__stdcall *)(int, int, void*, int*))DBUpdateRecord)(dbHandle, id, test_data, &size_param);
        printf("  ID %d: %d (size after: %d)\n", id, result, size_param);
    }
    
    // Signature 6: __cdecl with pointer to size
    printf("Sig 6 (__cdecl): (handle, recordId, data, size*)\n");
    for (int id = 1; id <= 5; id++) {
        int size_param = test_size;
        int result = ((int (__cdecl *)(int, int, void*, int*))DBUpdateRecord)(dbHandle, id, test_data, &size_param);
        printf("  ID %d: %d (size after: %d)\n", id, result, size_param);
    }
    
    // Signature 7: No record ID, just data (handle, data, size)
    printf("Sig 7 (__stdcall): (handle, data, size)\n");
    int result7 = ((int (__stdcall *)(int, void*, int))DBUpdateRecord)(dbHandle, test_data, test_size);
    printf("  Result: %d\n", result7);
    
    // Signature 8: __cdecl (handle, data, size)
    printf("Sig 8 (__cdecl): (handle, data, size)\n");
    int result8 = ((int (__cdecl *)(int, void*, int))DBUpdateRecord)(dbHandle, test_data, test_size);
    printf("  Result: %d\n", result8);
    
    // Signature 9: With additional flags parameter (handle, recordId, data, size, flags)
    printf("Sig 9 (__stdcall): (handle, recordId, data, size, flags)\n");
    for (int id = 1; id <= 3; id++) {
        for (int flags = 0; flags <= 2; flags++) {
            int result = ((int (__stdcall *)(int, int, void*, int, int))DBUpdateRecord)(dbHandle, id, test_data, test_size, flags);
            printf("  ID %d, flags %d: %d\n", id, flags, result);
        }
    }
    
    // Signature 10: __cdecl with flags
    printf("Sig 10 (__cdecl): (handle, recordId, data, size, flags)\n");
    for (int id = 1; id <= 3; id++) {
        for (int flags = 0; flags <= 2; flags++) {
            int result = ((int (__cdecl *)(int, int, void*, int, int))DBUpdateRecord)(dbHandle, id, test_data, test_size, flags);
            printf("  ID %d, flags %d: %d\n", id, flags, result);
        }
    }
    
    printf("\n=== Summary ===\n");
    printf("Tested 10 different function signatures with various parameters.\n");
    printf("Look for any non-zero results above.\n");
    
    if (DBClose) DBClose(dbHandle);
    FreeLibrary(hDll);
    return 0;
}