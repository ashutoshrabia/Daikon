import os
import json
import subprocess
import shutil
import numpy as np
import pandas as pd
from prune_main import mainfun
from make import main2

np.random.seed(0)


list_of_programs = ["strcat", "strncat"]


def is_char_pointer(typ: str) -> bool:
    if not isinstance(typ, str):
        return False
    t = typ.strip().lower()
    return "char pointer" in t or "char *" in t or t == "charpointer"


for progname in list_of_programs:
    with open(f"functions/{progname}.json", "r", encoding="utf-8") as f:
        spec = json.load(f)
    params = spec.get("parameters", {})
    func_name = spec.get("name", "target")

    names = list(params.keys())
    ptr_names = [n for n in names if is_char_pointer(params[n])]
    nonptr_names = [n for n in names if not is_char_pointer(params[n])]

    boolean_attrs = []
    for p in ptr_names:
        boolean_attrs.append(f"{p}Null")
    for p in ptr_names:
        boolean_attrs.append(f"isValid{p}")
    for p in ptr_names:
        boolean_attrs.append(f"isString{p}")
    for a, b in __import__("itertools").combinations(ptr_names, 2):
        boolean_attrs.append(f"isDisjoint{a}{b}")

    integer_attrs = []
    for idx in range(1, len(ptr_names) + 1):
        integer_attrs.append(f"sizeof{idx}")
    for idx in range(1, len(ptr_names) + 1):
        integer_attrs.append(f"strlen{idx}")
    for p in nonptr_names:
        integer_attrs.append(p)

    attributes = boolean_attrs + integer_attrs
    types_dict = {"Bool": boolean_attrs, "NumInt": integer_attrs}

    with open(f"functions/{progname}.json", "w", encoding="utf-8") as f:
        spec["types_dict"] = types_dict
        json.dump(spec, f, indent=4)

    EXE = f"EXE/{progname}_exe"

    main2(f"functions/{progname}.json", f"cfunctions/{progname}.c")
    
    with open(f"cfunctions/{progname}.c", "r", encoding="utf-8") as f:
        c_full = f.read()
    gcc = shutil.which("gcc")
    compile_cmd = [
        gcc,
        "-x",
        "c",
        "-",
        "-O0",
        "-g",
        "-fsanitize=address,undefined",
        "-o",
        EXE,
    ]
    print("Compiling C source...")
    subprocess.run(
        compile_cmd,
        input=c_full,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    print("Compiled executable at:", EXE)

    if not os.path.exists(f"data/{progname}.csv"):

        n_rows = 2000
        bool_count = len(boolean_attrs)
        int_count = len(integer_attrs)

        with open("interval.json", "r") as f:
            data = json.load(f)
        low = data["NumInt"][0]
        high = data["NumInt"][1]

        bool_data = np.random.binomial(1, 0.5, size=(n_rows, bool_count)).astype(int)
        int_data = np.random.randint(low, high + 1, size=(n_rows, int_count)).astype(
            int
        )

        data_matrix = np.hstack([bool_data, int_data])
        df = pd.DataFrame(data_matrix, columns=attributes).astype(int)
        os.makedirs("data", exist_ok=True)

        

        label = []
        for idx, row in df.iterrows():
            args = [str(int(row[col])) for col in attributes]
            cmd = [EXE] + args
            try:
                res = subprocess.run(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=1.0
                )
                label.append(1 if res.returncode == 0 else 0)
            except subprocess.TimeoutExpired:
                label.append(0)
            except Exception:
                label.append(0)

        df["label"] = label
        # os.makedirs("labels_data", exist_ok=True)
        df.to_csv(f"data/{func_name}.csv", index=False)
        print("Number of good runs (label==1):", int((df["label"] == 1).sum()))

    else:
        df = pd.read_csv(f"data/{func_name}.csv")
        print("Number of good runs (label==1):", int((df["label"] == 1).sum()))
    if df["label"].sum() == 0:
        df.to_csv(f"{func_name}.csv", index=False)
        continue
    mainfun(progname)
