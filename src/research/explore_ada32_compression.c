/*
 * Explore Ada32.dll for compression-related functions
 */
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>

int main() {
    printf("=== Exploring Ada32.dll for Compression Functions ===\n");
    
    // Load both versions
    HMODULE hAda32 = LoadLibrary("Ada32.dll");
    HMODULE hDbviewAda32 = LoadLibrary("Dbview/Ada32.dll");
    
    if (!hAda32) {
        printf("❌ Failed to load main Ada32.dll\n");
    } else {
        printf("✅ Loaded main Ada32.dll\n");
    }
    
    if (!hDbviewAda32) {
        printf("❌ Failed to load Dbview/Ada32.dll\n");
    } else {
        printf("✅ Loaded Dbview/Ada32.dll\n");
    }
    
    // Test compression-related function names
    const char* compression_functions[] = {
        "AdaCompressAtomStream",
        "AdaDecompressAtomStream", 
        "AdaCompressFragment",
        "AdaDecompressFragment",
        "AdaPackAtomStream",
        "AdaUnpackAtomStream",
        "AdaConvertToProd",
        "AdaConvertToDebug",
        "AdaConvertFormat",
        "AdaOptimizeAtomStream",
        "AdaReduceAtomStream",
        "AdaMinifyAtomStream"
    };
    
    int num_functions = sizeof(compression_functions) / sizeof(compression_functions[0]);
    
    printf("\n=== Main Ada32.dll Compression Functions ===\n");
    if (hAda32) {
        for (int i = 0; i < num_functions; i++) {
            void* func = GetProcAddress(hAda32, compression_functions[i]);
            printf("%-25s: %s\n", compression_functions[i], func ? "✅ Found" : "❌ Not found");
        }
    }
    
    printf("\n=== DbViewer Ada32.dll Compression Functions ===\n");
    if (hDbviewAda32) {
        for (int i = 0; i < num_functions; i++) {
            void* func = GetProcAddress(hDbviewAda32, compression_functions[i]);
            printf("%-25s: %s\n", compression_functions[i], func ? "✅ Found" : "❌ Not found");
        }
    }
    
    // Also check other DLLs in DbViewer
    printf("\n=== Other DbViewer DLLs ===\n");
    
    HMODULE hSupersub = LoadLibrary("Dbview/Supersub.dll");
    if (hSupersub) {
        printf("✅ Loaded Supersub.dll\n");
        // Test if this has compression
        void* compress = GetProcAddress(hSupersub, "Compress");
        void* decompress = GetProcAddress(hSupersub, "Decompress");
        printf("  Compress function: %s\n", compress ? "✅ Found" : "❌ Not found");
        printf("  Decompress function: %s\n", decompress ? "✅ Found" : "❌ Not found");
        FreeLibrary(hSupersub);
    } else {
        printf("❌ Failed to load Supersub.dll\n");
    }
    
    HMODULE hJgdw32 = LoadLibrary("Dbview/Jgdw32.dll");
    if (hJgdw32) {
        printf("✅ Loaded Jgdw32.dll\n");
        // Test compression functions
        void* compress = GetProcAddress(hJgdw32, "Compress");
        void* pack = GetProcAddress(hJgdw32, "Pack");
        printf("  Compress function: %s\n", compress ? "✅ Found" : "❌ Not found");
        printf("  Pack function: %s\n", pack ? "✅ Found" : "❌ Not found");
        FreeLibrary(hJgdw32);
    } else {
        printf("❌ Failed to load Jgdw32.dll\n");
    }
    
    if (hAda32) FreeLibrary(hAda32);
    if (hDbviewAda32) FreeLibrary(hDbviewAda32);
    
    return 0;
}