import json
import os
from itertools import combinations

def is_char_pointer(typ):
    if not isinstance(typ, str):
        return False
    t = typ.strip().lower()
    return "char pointer" in t or "char *" in t or t == "charpointer"

def is_char_nonptr(typ):
    if not isinstance(typ, str):
        return False
    t = typ.strip().lower()
    return t == "char"

def is_integer(typ):
    if not isinstance(typ, str):
        return False
    t = typ.strip().lower()
    return t in ("int", "integer", "size_t", "long", "unsigned")

# Map return_type string from spec to C type string
def map_return_type(rt):
    if not isinstance(rt, str):
        return "void"
    s = rt.strip().lower()
    if s == "none":
        return "void"
    if s == "int":
        return "int"
    if s == "long":
        return "long"
    if s == "size_t":
        return "size_t"
    if s == "char pointer" or s == "char*":
        return "char *"
    # fallback
    return s

def load_spec(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f"{path} not found")
    with open(path, "r", encoding="utf-8") as f:
        j = json.load(f)
    name = j.get("name")
    params = j.get("parameters", {})
    ret = j.get("return_type", "none")
    return name, params, ret

def build_attr_lists(params):
    # preserve ordering of params (python3.7+ dict)
    names = list(params.keys())
    ptrs = [n for n in names if is_char_pointer(params[n])]
    nonptrs = [n for n in names if not is_char_pointer(params[n])]

    boolean_attrs = []
    # pNull for each pointer
    for p in ptrs:
        boolean_attrs.append(f"{p}Null")
    # isValid<p>
    for p in ptrs:
        boolean_attrs.append(f"isValid{p}")
    # isString<p>
    for p in ptrs:
        boolean_attrs.append(f"isString{p}")
    # pairwise isDisjoint<pa><pb> in order of pointer appearance
    for a, b in combinations(ptrs, 2):
        boolean_attrs.append(f"isDisjoint{a}{b}")

    integer_attrs = []
    # sizeof1..sizeofK
    for i in range(1, len(ptrs) + 1):
        integer_attrs.append(f"sizeof{i}")
    # strlen1..strlenK
    for i in range(1, len(ptrs) + 1):
        integer_attrs.append(f"strlen{i}")
    # append non-pointer params (ch, n, etc) in original order
    for p in nonptrs:
        integer_attrs.append(p)

    all_attrs = boolean_attrs + integer_attrs
    return ptrs, nonptrs, boolean_attrs, integer_attrs, all_attrs

def c_type_for_param(param_type):
    if is_char_pointer(param_type):
        return "char *"
    if is_char_nonptr(param_type):
        return "int"   # treat single char as int for argv handling
    # treat remaining as int for simplicity
    return "int"

def gen_prototype(func_name, params, ret_c_type):
    # Create a simple prototype matching pointer vs int params
    parts = []
    for pname, ptype in params.items():
        ctype = c_type_for_param(ptype)
        parts.append(f"{ctype} {pname}")
    param_list = ", ".join(parts) if parts else "void"
    return f"extern {ret_c_type} {func_name}({param_list});"

def gen_new_c(func_name, params, ret_spec):
    ret_c = map_return_type(ret_spec)
    ptrs, nonptrs, bools, ints, all_attrs = build_attr_lists(params)
    expected = len(all_attrs) + 1

    lines = []
    # includes
    lines.append("#include <stdlib.h>")
    lines.append("#include <stdio.h>")
    lines.append("#include <string.h>")
    lines.append("#include <stddef.h>")  # for size_t
    lines.append("")
    lines.append("/* auto-generated new.c from spec.json */")
    lines.append("")
    # function prototype
    # proto = gen_prototype(func_name, params, ret_c)
    # lines.append(proto)
    # lines.append("")
    # main
    lines.append("int main(int argc, char **argv) {")
    lines.append(f"    if (argc != {expected}) {{")
    usage = " ".join(all_attrs)
    lines.append(f'        fprintf(stderr, "Usage: %s {usage}\\n", argv[0]);')
    lines.append("        return 2;")
    lines.append("    }")
    lines.append("")
    # parse argv into ints
    for i, name in enumerate(all_attrs, start=1):
        lines.append(f"    int {name} = atoi(argv[{i}]);")
    lines.append("")
    # declare pointers
    for p in ptrs:
        lines.append(f"    char *{p} = NULL;")
    lines.append("")
    # allocate and initialize pointers
    for idx, p in enumerate(ptrs, start=1):
        lines.append(f"    if ({p}Null) {p} = NULL;")
        lines.append(f"    else if (isValid{p}) {{")
        lines.append(f"        {p} = (char*)malloc(sizeof{idx});")
        lines.append(f"        if ({p}) memset({p}, 'A', sizeof{idx});")
        lines.append(f"        if (isString{p}) {p}[strlen{idx}] = '\\0';")
        lines.append("    }")
    lines.append("")
    # disjoint aliasing
    for a, b in combinations(ptrs, 2):
        lines.append(f"    if (!isDisjoint{a}{b} && !{a}Null && !{b}Null && isValid{a}) {{")
        lines.append(f"        {b} = {a} + 2;")
        lines.append("    }")
    lines.append("")
    # call the function with exactly the params in spec (in order)
    call_args = ", ".join(params.keys())
    # handle return type
    if ret_c == "void":
        lines.append(f"    /* call target function (void) */")
        lines.append(f"    {func_name}({call_args});")
    elif ret_c == "char *":
        lines.append(f"    /* call target function returning char* */")
        lines.append(f"    char *res = {func_name}({call_args});")
        lines.append("    (void)res;")
    else:
        # int / long / size_t etc.
        lines.append(f"    /* call target function returning {ret_c} */")
        lines.append(f"    {ret_c} r = {func_name}({call_args});")
        lines.append("    (void)r;")
    lines.append("")
    # free logic: free p1; free p2 only when disjoint or p1Null (avoid double free)
    if("p2" not in ptrs):
        #lines.append(f"    if (!p1Null && isValidp1) free(p1);")
        lines.append(f"    if (p1) free(p1);")

    else:
        #lines.append(f"    if (!p1Null) free(p1);")
        lines.append(f"    if (p1) free(p1);")
    
    

    for a, b in combinations(ptrs, 2):
        # lines.append(f"    if (!{b}Null && (isDisjoint{a}{b} || {a}Null)) free({b});")
        lines.append(f"    if ({b}) free({b});")
    lines.append("")
    lines.append("    return 0;")
    lines.append("}")
    return "\n".join(lines)

def main2(SPEC, OUT_C):
    try:
        func_name, params, ret_spec = load_spec(SPEC)
    except Exception as e:
        print("Error reading json file:", e)
        return
    if not func_name:
        print("json file must contain a 'name' key with the function name.")
        return
    src = gen_new_c(func_name, params, ret_spec)
    with open(OUT_C, "w", encoding="utf-8") as f:
        f.write(src)
    print(f"Wrote {OUT_C}.")
    print("Compile with something like:")
    print(f"gcc -x c {func_name}.c -O0 -g -fsanitize=address,undefined -o {func_name}_exe")

