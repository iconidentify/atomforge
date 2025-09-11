/*
 * Ada32 Explorer - Comprehensive DLL function exploration tool
 * Compile with: i686-w64-mingw32-gcc -o ada32_explorer.exe ada32_explorer.c
 */
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// Function type definitions based on exports.json
typedef int (__cdecl *AdaInitialize_t)(void);
typedef int (__cdecl *AdaGetErrorText_t)(int errorCode, char* buffer, int bufferSize);
typedef int (__cdecl *AdaLookupAtomEnum_t)(const char* atomName);
typedef int (__cdecl *AdaAssembleAtomStream_t)(void* input, int inputSize, void* output, int* outputSize);
typedef int (__cdecl *AdaAssembleFragment_t)(void* input, int inputSize, void* output, int* outputSize);
typedef int (__cdecl *AdaAssembleArgument_t)(void* input, int inputSize, void* output, int* outputSize);
typedef int (__cdecl *AdaNormalizeAtomStream_t)(void* input, int inputSize, void* output, int* outputSize);
typedef int (__cdecl *AdaDisassembleAtomStream_t)(void* input, int inputSize);
typedef int (__cdecl *AdaDisassembleArgument_t)(void* input, int inputSize);
typedef int (__cdecl *AdaDisassembleAtom_t)(void* input, int inputSize);
typedef int (__cdecl *AdaAddToAtomStream_t)(void* data, int size);
typedef int (__cdecl *AdaAddLongToAtomStream_t)(long value);
typedef int (__cdecl *AdaDoAtomCallbacks_t)(void);

// Global function pointers
HMODULE hDll = NULL;
AdaInitialize_t AdaInitialize = NULL;
AdaGetErrorText_t AdaGetErrorText = NULL;
AdaLookupAtomEnum_t AdaLookupAtomEnum = NULL;
AdaAssembleAtomStream_t AdaAssembleAtomStream = NULL;
AdaAssembleFragment_t AdaAssembleFragment = NULL;
AdaAssembleArgument_t AdaAssembleArgument = NULL;
AdaNormalizeAtomStream_t AdaNormalizeAtomStream = NULL;
AdaDisassembleAtomStream_t AdaDisassembleAtomStream = NULL;
AdaDisassembleArgument_t AdaDisassembleArgument = NULL;
AdaDisassembleAtom_t AdaDisassembleAtom = NULL;
AdaAddToAtomStream_t AdaAddToAtomStream = NULL;
AdaAddLongToAtomStream_t AdaAddLongToAtomStream = NULL;
AdaDoAtomCallbacks_t AdaDoAtomCallbacks = NULL;

void log_result(const char* function_name, const char* test_type, int result, const char* details) {
    printf("RESULT: %s | %s | result=%d | %s\n", function_name, test_type, result, details);
}

int load_dll_functions() {
    hDll = LoadLibrary("Ada32.dll");
    if (!hDll) {
        printf("ERROR: Failed to load Ada32.dll\n");
        return 0;
    }
    
    // Load all function pointers
    AdaInitialize = (AdaInitialize_t)GetProcAddress(hDll, "AdaInitialize");
    AdaGetErrorText = (AdaGetErrorText_t)GetProcAddress(hDll, "AdaGetErrorText");
    AdaLookupAtomEnum = (AdaLookupAtomEnum_t)GetProcAddress(hDll, "AdaLookupAtomEnum");
    AdaAssembleAtomStream = (AdaAssembleAtomStream_t)GetProcAddress(hDll, "AdaAssembleAtomStream");
    AdaAssembleFragment = (AdaAssembleFragment_t)GetProcAddress(hDll, "AdaAssembleFragment");
    AdaAssembleArgument = (AdaAssembleArgument_t)GetProcAddress(hDll, "AdaAssembleArgument");
    AdaNormalizeAtomStream = (AdaNormalizeAtomStream_t)GetProcAddress(hDll, "AdaNormalizeAtomStream");
    AdaDisassembleAtomStream = (AdaDisassembleAtomStream_t)GetProcAddress(hDll, "AdaDisassembleAtomStream");
    AdaDisassembleArgument = (AdaDisassembleArgument_t)GetProcAddress(hDll, "AdaDisassembleArgument");
    AdaDisassembleAtom = (AdaDisassembleAtom_t)GetProcAddress(hDll, "AdaDisassembleAtom");
    AdaAddToAtomStream = (AdaAddToAtomStream_t)GetProcAddress(hDll, "AdaAddToAtomStream");
    AdaAddLongToAtomStream = (AdaAddLongToAtomStream_t)GetProcAddress(hDll, "AdaAddLongToAtomStream");
    AdaDoAtomCallbacks = (AdaDoAtomCallbacks_t)GetProcAddress(hDll, "AdaDoAtomCallbacks");
    
    printf("FUNCTION_LOAD: AdaInitialize=%p\n", AdaInitialize);
    printf("FUNCTION_LOAD: AdaGetErrorText=%p\n", AdaGetErrorText);
    printf("FUNCTION_LOAD: AdaLookupAtomEnum=%p\n", AdaLookupAtomEnum);
    printf("FUNCTION_LOAD: AdaAssembleAtomStream=%p\n", AdaAssembleAtomStream);
    printf("FUNCTION_LOAD: AdaAssembleFragment=%p\n", AdaAssembleFragment);
    printf("FUNCTION_LOAD: AdaAssembleArgument=%p\n", AdaAssembleArgument);
    printf("FUNCTION_LOAD: AdaNormalizeAtomStream=%p\n", AdaNormalizeAtomStream);
    printf("FUNCTION_LOAD: AdaDisassembleAtomStream=%p\n", AdaDisassembleAtomStream);
    printf("FUNCTION_LOAD: AdaDisassembleArgument=%p\n", AdaDisassembleArgument);
    printf("FUNCTION_LOAD: AdaDisassembleAtom=%p\n", AdaDisassembleAtom);
    printf("FUNCTION_LOAD: AdaAddToAtomStream=%p\n", AdaAddToAtomStream);
    printf("FUNCTION_LOAD: AdaAddLongToAtomStream=%p\n", AdaAddLongToAtomStream);
    printf("FUNCTION_LOAD: AdaDoAtomCallbacks=%p\n", AdaDoAtomCallbacks);
    
    return (AdaInitialize != NULL);
}

void explore_initialize() {
    printf("\n=== EXPLORING: AdaInitialize ===\n");
    if (!AdaInitialize) {
        printf("ERROR: AdaInitialize not loaded\n");
        return;
    }
    
    int result = AdaInitialize();
    log_result("AdaInitialize", "basic_call", result, "no parameters");
    
    // Test multiple calls
    int result2 = AdaInitialize();
    log_result("AdaInitialize", "second_call", result2, "testing idempotency");
}

void explore_get_error_text() {
    printf("\n=== EXPLORING: AdaGetErrorText ===\n");
    if (!AdaGetErrorText) {
        printf("ERROR: AdaGetErrorText not loaded\n");
        return;
    }
    
    char buffer[256];
    
    // Test with error code 0
    memset(buffer, 0, sizeof(buffer));
    int result = AdaGetErrorText(0, buffer, sizeof(buffer));
    log_result("AdaGetErrorText", "error_code_0", result, buffer);
    
    // Test with various error codes
    for (int i = 1; i <= 5; i++) {
        memset(buffer, 0, sizeof(buffer));
        result = AdaGetErrorText(i, buffer, sizeof(buffer));
        char detail[300];
        snprintf(detail, sizeof(detail), "error_code_%d: %s", i, buffer);
        log_result("AdaGetErrorText", "error_codes", result, detail);
    }
}

void explore_lookup_atom_enum() {
    printf("\n=== EXPLORING: AdaLookupAtomEnum ===\n");
    if (!AdaLookupAtomEnum) {
        printf("ERROR: AdaLookupAtomEnum not loaded\n");
        return;
    }
    
    // Test common atom names found in the golden files
    const char* test_atoms[] = {
        "uni_start_stream",
        "uni_end_stream", 
        "man_start_object",
        "man_end_object",
        "mat_object_id",
        "mat_orientation",
        "act_set_criterion",
        "de_ez_send_form",
        "invalid_atom_name",
        "",
        NULL
    };
    
    for (int i = 0; test_atoms[i] != NULL; i++) {
        int result = AdaLookupAtomEnum(test_atoms[i]);
        char detail[256];
        snprintf(detail, sizeof(detail), "atom='%s'", test_atoms[i]);
        log_result("AdaLookupAtomEnum", "atom_lookup", result, detail);
    }
}

void explore_assembly_functions(const char* test_input, int input_size) {
    printf("\n=== EXPLORING: Assembly Functions ===\n");
    
    char* output_buffer = malloc(input_size * 8);  // Large buffer
    int output_size;
    
    // Test AdaAssembleAtomStream
    if (AdaAssembleAtomStream) {
        output_size = input_size * 8;
        int result = AdaAssembleAtomStream((void*)test_input, input_size, output_buffer, &output_size);
        char detail[256];
        snprintf(detail, sizeof(detail), "input_size=%d, result_size=%d", input_size, output_size);
        log_result("AdaAssembleAtomStream", "simple_input", result, detail);
    }
    
    // Test AdaAssembleFragment
    if (AdaAssembleFragment) {
        output_size = input_size * 8;
        int result = AdaAssembleFragment((void*)test_input, input_size, output_buffer, &output_size);
        char detail[256];
        snprintf(detail, sizeof(detail), "input_size=%d, result_size=%d", input_size, output_size);
        log_result("AdaAssembleFragment", "simple_input", result, detail);
    }
    
    // Test AdaAssembleArgument  
    if (AdaAssembleArgument) {
        output_size = input_size * 8;
        int result = AdaAssembleArgument((void*)test_input, input_size, output_buffer, &output_size);
        char detail[256];
        snprintf(detail, sizeof(detail), "input_size=%d, result_size=%d", input_size, output_size);
        log_result("AdaAssembleArgument", "simple_input", result, detail);
    }
    
    // Test AdaNormalizeAtomStream
    if (AdaNormalizeAtomStream) {
        output_size = input_size * 8;
        int result = AdaNormalizeAtomStream((void*)test_input, input_size, output_buffer, &output_size);
        char detail[256];
        snprintf(detail, sizeof(detail), "input_size=%d, result_size=%d", input_size, output_size);
        log_result("AdaNormalizeAtomStream", "simple_input", result, detail);
    }
    
    free(output_buffer);
}

void explore_disassembly_functions() {
    printf("\n=== EXPLORING: Disassembly Functions ===\n");
    
    // Read a golden .str file for testing
    FILE* fp = fopen("golden_tests/32-105.str", "rb");
    if (!fp) {
        printf("ERROR: Cannot open golden test file\n");
        return;
    }
    
    fseek(fp, 0, SEEK_END);
    long file_size = ftell(fp);
    fseek(fp, 0, SEEK_SET);
    
    char* binary_data = malloc(file_size);
    fread(binary_data, 1, file_size, fp);
    fclose(fp);
    
    // Test AdaDisassembleAtomStream
    if (AdaDisassembleAtomStream) {
        int result = AdaDisassembleAtomStream(binary_data, file_size);
        char detail[256];
        snprintf(detail, sizeof(detail), "input_size=%ld", file_size);
        log_result("AdaDisassembleAtomStream", "golden_file", result, detail);
    }
    
    // Test AdaDisassembleArgument
    if (AdaDisassembleArgument) {
        int result = AdaDisassembleArgument(binary_data, file_size);
        char detail[256];
        snprintf(detail, sizeof(detail), "input_size=%ld", file_size);
        log_result("AdaDisassembleArgument", "golden_file", result, detail);
    }
    
    // Test AdaDisassembleAtom
    if (AdaDisassembleAtom) {
        int result = AdaDisassembleAtom(binary_data, file_size);
        char detail[256];
        snprintf(detail, sizeof(detail), "input_size=%ld", file_size);
        log_result("AdaDisassembleAtom", "golden_file", result, detail);
    }
    
    free(binary_data);
}

void explore_stream_manipulation() {
    printf("\n=== EXPLORING: Stream Manipulation Functions ===\n");
    
    // Test AdaAddToAtomStream
    if (AdaAddToAtomStream) {
        char test_data[] = "test data";
        int result = AdaAddToAtomStream(test_data, strlen(test_data));
        log_result("AdaAddToAtomStream", "string_data", result, "test string");
    }
    
    // Test AdaAddLongToAtomStream
    if (AdaAddLongToAtomStream) {
        int result = AdaAddLongToAtomStream(12345);
        log_result("AdaAddLongToAtomStream", "numeric_data", result, "value=12345");
        
        result = AdaAddLongToAtomStream(0);
        log_result("AdaAddLongToAtomStream", "zero_value", result, "value=0");
        
        result = AdaAddLongToAtomStream(-1);
        log_result("AdaAddLongToAtomStream", "negative_value", result, "value=-1");
    }
    
    // Test AdaDoAtomCallbacks
    if (AdaDoAtomCallbacks) {
        int result = AdaDoAtomCallbacks();
        log_result("AdaDoAtomCallbacks", "basic_call", result, "no parameters");
    }
}

int main(int argc, char* argv[]) {
    printf("Ada32 DLL Function Explorer\n");
    printf("===========================\n");
    
    if (!load_dll_functions()) {
        printf("ERROR: Failed to load DLL functions\n");
        return 1;
    }
    
    // Explore functions systematically
    explore_initialize();
    explore_get_error_text();
    explore_lookup_atom_enum();
    
    // Test with simple input
    const char* simple_input = "uni_start_stream <00x>\nuni_end_stream <00x>";
    explore_assembly_functions(simple_input, strlen(simple_input));
    
    explore_disassembly_functions();
    explore_stream_manipulation();
    
    printf("\n=== EXPLORATION COMPLETE ===\n");
    
    if (hDll) {
        FreeLibrary(hDll);
    }
    
    return 0;
}