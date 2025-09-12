#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <windows.h>

// Ada32.dll function declarations
typedef int (__cdecl *AdaAssembleAtomStream_t)(void* input, int inputSize, void* output, int* outputSize);

int main(int argc, char* argv[]) {
    HMODULE ada32_dll;
    AdaAssembleAtomStream_t AdaAssembleAtomStream;
    FILE* input_file;
    FILE* output_file;
    char* input_buffer;
    char* output_buffer;
    int input_size;
    int output_size = 1024 * 1024; // 1MB output buffer
    int result;

    printf("ADA32 FDO Compiler\n");
    printf("=================\n\n");

    // Load Ada32.dll
    ada32_dll = LoadLibrary("bin\\dlls\\Ada32.dll");
    if (!ada32_dll) {
        printf("ERROR: Failed to load Ada32.dll\n");
        return 1;
    }

    // Get function pointer
    AdaAssembleAtomStream = (AdaAssembleAtomStream_t)GetProcAddress(ada32_dll, "AdaAssembleAtomStream");
    if (!AdaAssembleAtomStream) {
        printf("ERROR: Failed to find AdaAssembleAtomStream function\n");
        FreeLibrary(ada32_dll);
        return 1;
    }

    // Read input file
    input_file = fopen("input.txt", "rb");
    if (!input_file) {
        printf("ERROR: Failed to open input.txt\n");
        FreeLibrary(ada32_dll);
        return 1;
    }

    // Get file size
    fseek(input_file, 0, SEEK_END);
    input_size = ftell(input_file);
    fseek(input_file, 0, SEEK_SET);

    // Allocate input buffer
    input_buffer = (char*)malloc(input_size + 1);
    if (!input_buffer) {
        printf("ERROR: Failed to allocate input buffer\n");
        fclose(input_file);
        FreeLibrary(ada32_dll);
        return 1;
    }

    // Read input file
    fread(input_buffer, 1, input_size, input_file);
    input_buffer[input_size] = '\0';
    fclose(input_file);

    // Allocate output buffer
    output_buffer = (char*)malloc(output_size);
    if (!output_buffer) {
        printf("ERROR: Failed to allocate output buffer\n");
        free(input_buffer);
        FreeLibrary(ada32_dll);
        return 1;
    }

    printf("Compiling FDO...\n");
    printf("Input size: %d bytes\n", input_size);

    // Call Ada32.dll compilation function
    result = AdaAssembleAtomStream(input_buffer, input_size, output_buffer, &output_size);

    if (result == 0) {
        printf("Compilation successful!\n");
        printf("Output size: %d bytes\n", output_size);

        // Write output file
        output_file = fopen("output.str", "wb");
        if (output_file) {
            fwrite(output_buffer, 1, output_size, output_file);
            fclose(output_file);
            printf("Output written to output.str\n");
        } else {
            printf("ERROR: Failed to write output file\n");
        }
    } else {
        printf("ERROR: Compilation failed with code %d\n", result);
    }

    // Cleanup
    free(input_buffer);
    free(output_buffer);
    FreeLibrary(ada32_dll);

    printf("\nDone.\n");
    return (result == 0) ? 0 : 1;
}
