/*
 * Atom Stream Compiler - Parse .txt files and compile using Ada32.dll
 * Compile with: i686-w64-mingw32-gcc -o atom_compiler.exe atom_compiler.c
 */
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>

typedef int (__cdecl *AdaInitialize_t)(void);
typedef int (__cdecl *AdaAssembleAtomStream_t)(void* input, int inputSize, void* output, int* outputSize);

// Structure to hold parsed atoms
typedef struct {
    char* atom_name;
    char* parameters;
    int indent_level;
} ParsedAtom;

typedef struct {
    ParsedAtom* atoms;
    int count;
    int capacity;
} AtomList;

// Global DLL handles
HMODULE hDll = NULL;
AdaInitialize_t AdaInitialize = NULL;
AdaAssembleAtomStream_t AdaAssembleAtomStream = NULL;

int load_ada32_dll() {
    hDll = LoadLibrary("Ada32.dll");
    if (!hDll) {
        printf("ERROR: Failed to load Ada32.dll\n");
        return 0;
    }
    
    AdaInitialize = (AdaInitialize_t)GetProcAddress(hDll, "AdaInitialize");
    AdaAssembleAtomStream = (AdaAssembleAtomStream_t)GetProcAddress(hDll, "AdaAssembleAtomStream");
    
    if (!AdaInitialize || !AdaAssembleAtomStream) {
        printf("ERROR: Failed to load Ada32.dll functions\n");
        FreeLibrary(hDll);
        return 0;
    }
    
    int result = AdaInitialize();
    if (result != 1) {
        printf("ERROR: AdaInitialize failed: %d\n", result);
        FreeLibrary(hDll);
        return 0;
    }
    
    printf("Ada32.dll loaded and initialized successfully\n");
    return 1;
}

void cleanup_ada32() {
    if (hDll) {
        FreeLibrary(hDll);
        hDll = NULL;
    }
}

AtomList* create_atom_list() {
    AtomList* list = malloc(sizeof(AtomList));
    list->atoms = malloc(sizeof(ParsedAtom) * 100);
    list->count = 0;
    list->capacity = 100;
    return list;
}

void add_atom(AtomList* list, const char* atom_name, const char* parameters, int indent_level) {
    if (list->count >= list->capacity) {
        list->capacity *= 2;
        list->atoms = realloc(list->atoms, sizeof(ParsedAtom) * list->capacity);
    }
    
    ParsedAtom* atom = &list->atoms[list->count];
    atom->atom_name = strdup(atom_name);
    atom->parameters = parameters ? strdup(parameters) : NULL;
    atom->indent_level = indent_level;
    list->count++;
}

void free_atom_list(AtomList* list) {
    for (int i = 0; i < list->count; i++) {
        free(list->atoms[i].atom_name);
        if (list->atoms[i].parameters) {
            free(list->atoms[i].parameters);
        }
    }
    free(list->atoms);
    free(list);
}

int count_indent(const char* line) {
    int count = 0;
    while (line[count] == ' ') {
        count++;
    }
    return count;
}

char* trim_whitespace(char* str) {
    // Trim leading whitespace
    while (isspace(*str)) str++;
    
    // Trim trailing whitespace
    char* end = str + strlen(str) - 1;
    while (end > str && isspace(*end)) end--;
    *(end + 1) = '\0';
    
    return str;
}

AtomList* parse_atom_stream(const char* filename) {
    FILE* fp = fopen(filename, "r");
    if (!fp) {
        printf("ERROR: Cannot open file: %s\n", filename);
        return NULL;
    }
    
    AtomList* list = create_atom_list();
    char line[1024];
    int line_num = 0;
    
    printf("Parsing atom stream from %s...\n", filename);
    
    while (fgets(line, sizeof(line), fp)) {
        line_num++;
        
        // Remove newline
        line[strcspn(line, "\r\n")] = '\0';
        
        // Skip empty lines and comment lines
        char* trimmed = trim_whitespace(line);
        if (strlen(trimmed) == 0 || trimmed[0] == '<') {
            continue;
        }
        
        // Count indentation
        int indent = count_indent(line);
        
        // Parse atom and parameters
        char* atom_name = NULL;
        char* parameters = NULL;
        
        // Find the atom name (first word after indentation)
        char* start = line + indent;
        char* space_pos = strchr(start, ' ');
        char* bracket_pos = strchr(start, '<');
        
        if (space_pos && (!bracket_pos || space_pos < bracket_pos)) {
            // Atom with parameters
            int atom_len = space_pos - start;
            atom_name = malloc(atom_len + 1);
            strncpy(atom_name, start, atom_len);
            atom_name[atom_len] = '\0';
            
            // Extract parameters (everything after the atom name)
            parameters = trim_whitespace(space_pos + 1);
            if (strlen(parameters) > 0) {
                parameters = strdup(parameters);
            } else {
                parameters = NULL;
            }
        } else {
            // Atom without parameters
            atom_name = strdup(trim_whitespace(start));
            parameters = NULL;
        }
        
        if (atom_name && strlen(atom_name) > 0) {
            add_atom(list, atom_name, parameters, indent);
            printf("  Parsed: '%s' params='%s' indent=%d\n", 
                   atom_name, parameters ? parameters : "(none)", indent);
        }
        
        if (atom_name) free(atom_name);
        if (parameters) free(parameters);
    }
    
    fclose(fp);
    printf("Parsed %d atoms\n", list->count);
    return list;
}

int compile_atom(const char* atom_name, char* output_buffer, int max_output_size) {
    if (!AdaAssembleAtomStream) {
        return -1;
    }
    
    int input_size = strlen(atom_name);
    int output_size = max_output_size;
    
    int result = AdaAssembleAtomStream((void*)atom_name, input_size, output_buffer, &output_size);
    
    if (result > 0) {
        // Use the minimum of result and output_size as actual size
        int actual_size = (result < output_size) ? result : output_size;
        return actual_size;
    }
    
    return 0;  // Compilation failed
}

void print_hex(const char* label, const unsigned char* data, int size) {
    printf("%s (%d bytes): ", label, size);
    for (int i = 0; i < size && i < 32; i++) {
        printf("%02x ", data[i]);
    }
    if (size > 32) printf("...");
    printf("\n");
}

int compile_atom_stream(const char* input_file, const char* output_file) {
    if (!load_ada32_dll()) {
        return 1;
    }
    
    AtomList* atoms = parse_atom_stream(input_file);
    if (!atoms) {
        cleanup_ada32();
        return 1;
    }
    
    FILE* output_fp = fopen(output_file, "wb");
    if (!output_fp) {
        printf("ERROR: Cannot create output file: %s\n", output_file);
        free_atom_list(atoms);
        cleanup_ada32();
        return 1;
    }
    
    printf("\nCompiling atoms...\n");
    
    int total_output_size = 0;
    char atom_output[1024];  // Buffer for individual atom compilation
    
    for (int i = 0; i < atoms->count; i++) {
        ParsedAtom* atom = &atoms->atoms[i];
        
        printf("Compiling atom %d/%d: '%s'\n", i+1, atoms->count, atom->atom_name);
        
        int compiled_size = compile_atom(atom->atom_name, atom_output, sizeof(atom_output));
        
        if (compiled_size > 0) {
            printf("  Success: %d bytes\n", compiled_size);
            print_hex("  Output", (unsigned char*)atom_output, compiled_size);
            
            // Write compiled atom to output file
            fwrite(atom_output, 1, compiled_size, output_fp);
            total_output_size += compiled_size;
        } else {
            printf("  Failed to compile atom: %s\n", atom->atom_name);
        }
        
        // Also try to compile parameters if they exist
        if (atom->parameters && strlen(atom->parameters) > 0) {
            printf("  Compiling parameters: '%s'\n", atom->parameters);
            compiled_size = compile_atom(atom->parameters, atom_output, sizeof(atom_output));
            if (compiled_size > 0) {
                printf("    Parameters: %d bytes\n", compiled_size);
                fwrite(atom_output, 1, compiled_size, output_fp);
                total_output_size += compiled_size;
            }
        }
    }
    
    fclose(output_fp);
    
    printf("\nCompilation complete!\n");
    printf("Total output size: %d bytes\n", total_output_size);
    printf("Output file: %s\n", output_file);
    
    free_atom_list(atoms);
    cleanup_ada32();
    return 0;
}

int main(int argc, char* argv[]) {
    printf("Ada32 Atom Stream Compiler\n");
    printf("==========================\n");
    
    if (argc != 3) {
        printf("Usage: %s <input.txt> <output.str>\n", argv[0]);
        return 1;
    }
    
    const char* input_file = argv[1];
    const char* output_file = argv[2];
    
    printf("Input:  %s\n", input_file);
    printf("Output: %s\n", output_file);
    
    return compile_atom_stream(input_file, output_file);
}