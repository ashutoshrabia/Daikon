import sys
import os
import json
import subprocess
import shutil
import numpy as np
import pandas as pd

np.random.seed(0)
############################################ Helpers ####################################

# with open("new.c", "r", encoding="utf-8") as f:
#     c_full = f.read()

# gcc = shutil.which("gcc")
# compile_cmd = [gcc, "-x", "c", "-", "-O0", "-g", "-fsanitize=address,undefined", "-o", EXE]
# print("Compiling C source (piped to gcc)...")
# subprocess.run(compile_cmd, input=c_full, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def validate_counter_ex(cex, progname):
    with open(f"functions/{progname}.json", "r", encoding="utf-8") as f:
        spec = json.load(f)
    boolean = spec.get("types_dict", {}).get("Bool", [])
    integer = spec.get("types_dict", {}).get("NumInt", [])
    all_attr = boolean + integer
    types_dict = {"Bool": boolean, "NumInt": integer}

    for att in all_attr:
        if att not in cex:
            if att in types_dict["Bool"]:
                cex[att] = int(np.random.binomial(1, 0.5, size=1)[0])
            else:
                cex[att] = int(np.random.randint(1, 20, size=1)[0])

    EXE = f"EXE/{progname}_exe"
    args = [str(int(cex.get(attr, 0))) for attr in all_attr]
    cmd = [EXE] + args
    try:
        res = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=1.0
        )
        if res.returncode == 0:
            return "accepted"
        else:
            return "rejected"
    except subprocess.TimeoutExpired:
        return "rejected"
    except Exception:
        return "rejected"


# cex = {'isDisjointp1p2': True, 'isStringp1': False, 'p2Null': False, 'strlen1': 0, 'isValidp1': True, 'p1Null': False,  'sizeof2': 9, 'sizeof1': 10, 'isStringp2': True, 'isValidp2': True, 'strlen2': 9}
# progname = "strcpy"
# result = validate_counter_ex(cex, progname)
# print(f"Counter-example validation result for program '{progname}': {result}")
