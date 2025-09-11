/*
 * Explore Dbaol32.dll functions to find compression capability
 */
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>

int main() {
    // Load both versions of Dbaol32.dll
    printf("=== Exploring Dbaol32.dll Functions ===\n");
    
    HMODULE hDbaol = LoadLibrary("Dbaol32.dll");
    HMODULE hDbviewDbaol = LoadLibrary("Dbview/Dbaol32.dll");
    
    if (!hDbaol) {
        printf("❌ Failed to load main Dbaol32.dll\n");
    } else {
        printf("✅ Loaded main Dbaol32.dll\n");
    }
    
    if (!hDbviewDbaol) {
        printf("❌ Failed to load Dbview/Dbaol32.dll\n");
    } else {
        printf("✅ Loaded Dbview/Dbaol32.dll\n");
    }
    
    // Test common function names
    const char* test_functions[] = {
        "DBOpen",
        "DBClose", 
        "DBExtractRecord",
        "DBGetInfo",
        "DBGetLastError",
        "DBCompress",
        "DBDecompress",
        "CompressRecord",
        "DecompressRecord",
        "ConvertRecord",
        "SaveRecord",
        "ExportRecord",
        "PackRecord",
        "UnpackRecord"
    };
    
    int num_functions = sizeof(test_functions) / sizeof(test_functions[0]);
    
    printf("\n=== Main Dbaol32.dll Functions ===\n");
    if (hDbaol) {
        for (int i = 0; i < num_functions; i++) {
            void* func = GetProcAddress(hDbaol, test_functions[i]);
            printf("%-20s: %s\n", test_functions[i], func ? "✅ Found" : "❌ Not found");
        }
    }
    
    printf("\n=== DbViewer Dbaol32.dll Functions ===\n");
    if (hDbviewDbaol) {
        for (int i = 0; i < num_functions; i++) {
            void* func = GetProcAddress(hDbviewDbaol, test_functions[i]);
            printf("%-20s: %s\n", test_functions[i], func ? "✅ Found" : "❌ Not found");
        }
    }
    
    if (hDbaol) FreeLibrary(hDbaol);
    if (hDbviewDbaol) FreeLibrary(hDbviewDbaol);
    
    return 0;
}