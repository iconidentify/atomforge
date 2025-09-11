/*
 * Simple AOL Atom Stream Compiler
 * Converts .txt atom streams to .str binary files using Ada32.dll
 */
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>

typedef int (__cdecl *AdaInitialize_t)(void);
typedef int (__cdecl *AdaAssembleAtomStream_t)(void* input, int size, void* output, int* outSize);

int main(int argc, char* argv[]) {
    printf("AOL Atom Stream Compiler v1.0\n");
    printf("==============================\n");
    
    if (argc != 3) {
        printf("Usage: %s <input.txt> <output.str>\n", argv[0]);
        printf("Example: %s tests/fixtures/clean_32-105.txt output.str\n", argv[0]);
        return 1;
    }
    
    const char* input_file = argv[1];
    const char* output_file = argv[2];
    
    printf("Input:  %s\n", input_file);
    printf("Output: %s\n", output_file);
    
    // Load Ada32.dll
    HMODULE ada32 = LoadLibraryA("bin/dlls/Ada32.dll");
    if (!ada32) {
        printf("❌ Failed to load bin/dlls/Ada32.dll\n");
        return 1;
    }
    
    // Get function pointers
    AdaInitialize_t AdaInitialize = (AdaInitialize_t)GetProcAddress(ada32, "AdaInitialize");
    AdaAssembleAtomStream_t AdaAssembleAtomStream = (AdaAssembleAtomStream_t)GetProcAddress(ada32, "AdaAssembleAtomStream");
    
    if (!AdaInitialize || !AdaAssembleAtomStream) {
        printf("❌ Required functions not found in Ada32.dll\n");
        FreeLibrary(ada32);
        return 1;
    }
    
    // Initialize Ada32
    int init_result = AdaInitialize();
    if (init_result != 1) {
        printf("❌ Ada32 initialization failed: %d\n", init_result);
        FreeLibrary(ada32);
        return 1;
    }
    
    printf("✅ Ada32.dll loaded and initialized\n");
    
    // Read input file
    FILE* input_fp = fopen(input_file, "r");
    if (!input_fp) {
        printf("❌ Cannot open input file: %s\n", input_file);
        FreeLibrary(ada32);
        return 1;
    }
    
    fseek(input_fp, 0, SEEK_END);
    long input_size = ftell(input_fp);
    fseek(input_fp, 0, SEEK_SET);
    
    char* input_data = malloc(input_size + 1);
    fread(input_data, 1, input_size, input_fp);
    input_data[input_size] = 0;
    fclose(input_fp);
    
    printf("✅ Read %ld bytes from input file\n", input_size);
    
    // Compile atom stream
    printf("\n🔄 Compiling atom stream...\n");
    char output_buffer[1024];
    int output_size = sizeof(output_buffer);
    
    int compile_result = AdaAssembleAtomStream(input_data, (int)input_size, output_buffer, &output_size);
    
    if (compile_result != 0) {
        printf("❌ Compilation failed with error: %d\n", compile_result);
        free(input_data);
        FreeLibrary(ada32);
        return 1;
    }
    
    if (output_size <= 0) {
        printf("❌ No output generated\n");
        free(input_data);
        FreeLibrary(ada32);
        return 1;
    }
    
    printf("✅ Compilation successful: %d bytes generated\n", output_size);
    
    // Write output file
    FILE* output_fp = fopen(output_file, "wb");
    if (!output_fp) {
        printf("❌ Cannot create output file: %s\n", output_file);
        free(input_data);
        FreeLibrary(ada32);
        return 1;
    }
    
    fwrite(output_buffer, 1, output_size, output_fp);
    fclose(output_fp);
    
    printf("✅ Written %d bytes to %s\n", output_size, output_file);
    
    // Show format info
    printf("\n📊 Output Analysis:\n");
    printf("Format: %s\n", output_size == 356 ? "356-byte FDO (target)" : output_size == 413 ? "413-byte Raw (working)" : "Unknown");
    printf("Header: ");
    for (int i = 0; i < 8 && i < output_size; i++) {
        printf("%02x ", (unsigned char)output_buffer[i]);
    }
    printf("\n");
    
    if (output_size == 413) {
        printf("🎯 Successfully compiled to working 413-byte format!\n");
        printf("💡 Note: This contains all data but is not compressed to 356-byte FDO format\n");
    } else if (output_size == 356) {
        printf("🏆 Successfully compiled to target 356-byte FDO format!\n");
    } else {
        printf("⚠️  Unexpected output size: %d bytes\n", output_size);
    }
    
    // Cleanup
    free(input_data);
    FreeLibrary(ada32);
    
    printf("\n✅ Compilation complete!\n");
    return 0;
}