import pandas as pd
from copy import deepcopy
import os
import json

PATH = os.path.realpath("")


def update_rules(daik_rules, previous_rules, url):
    if previous_rules == []:
        return daik_rules
    daik_rules = [ele for ele in daik_rules if ele not in previous_rules]
    with open(
        f"{PATH}/results/accepted/{url.split('/')[-2].replace('-', '')}.txt", "r"
    ) as f:
        refined_rules = f.readlines()
    refined_rules = [ele.strip() for ele in refined_rules]
    daik_rules = daik_rules + refined_rules
    return daik_rules


def read_sel_dicts(url):
    with open(
        f"{PATH}/sel_dicts/{url.split('/')[-1].replace('-', '')}.json", "r"
    ) as json_file:
        sel_dict = json.load(json_file)
    return sel_dict

def drop_col_all_nans(data_df):
    """Like trt: use only accepted rows to decide all-NaN columns (for typed CSV with result column)."""
    all_columns = list(data_df.columns)
    # old code: data_df_acc = deepcopy(data_df)
    if "income" in data_df.columns:
        data_df_acc = deepcopy(data_df[data_df["income"] == "accepted"])
    else:
        data_df_acc = deepcopy(data_df)
    for col in all_columns:
        all_values = data_df_acc[col].to_list()
        if pd.isnull(all_values).all():
            data_df.drop(columns=[col], inplace=True)
    return data_df


def preprocess_data(data_df):
    
    types_dict = {
        "String": [],
        "Date": [],
        "NumInt": [],
        "NumFloat": [],
        "Select": [],
        "Choice": [],
        "Link": [],
        "Bool": [],
    }
    data_df = drop_col_all_nans(data_df)
    data_df_types = data_df.drop(columns=["income"]).loc[0, :].values.tolist()
    data_df = data_df.drop(labels=0, axis=0)
    data_df_cols = data_df.columns[:-1]
    for idx, col in enumerate(data_df_cols):
        if data_df_types[idx] in ["Data", "Text Editor", "Text", "Small Text"]:
            types_dict["String"].append(col)
        elif data_df_types[idx] in ["Date"]:
            types_dict["Date"].append(col)
        elif data_df_types[idx] in ["Check"]:
            types_dict["Choice"].append(col)
        elif data_df_types[idx] in ["Link", "Dynamic Link"]:
            types_dict["Link"].append(col)
        elif data_df_types[idx] in ["Select"]:
            types_dict["Select"].append(col)
        elif data_df_types[idx] in ["Float", "Percent"]:
            types_dict["NumFloat"].append(col)
        elif data_df_types[idx] in ["Int", "Currency"]:
            types_dict["NumInt"].append(col)
    return data_df, types_dict


def convert_to_int(interval):
    (
        d1,
        d2,
    ) = (
        interval[0],
        interval[1],
    )
    d1 = pd.Timestamp(d1)
    d2 = pd.Timestamp(d2)
    d1 = (pd.Series(d1) - pd.Timestamp(interval[0])).dt.days
    d2 = (pd.Series(d2) - pd.Timestamp(interval[0])).dt.days
    return [int(d1[0]), int(d2[0])]


def get_parts(s: str, id):
    s = s.strip("(").strip(")")
    var, val = s.split(f" {id} ")[0], s.split(f" {id} ")[1]
    try:
        val = int(eval(val))
        return {"var": var, "val": val, "id": id}
    except NameError:
        if id in ["<", ">"]:
            return {"var1": var, "var2": val, "id": id}
        else:
            return False


def check_range(ele):
    """We have catagorized rules into three types:
    1) Numerical Range Constraints: Range Constraints
    2) Constraints with strict inquality between two variables: StrictInq Constraints
    3) Any other constraint: Complex Constraints"""
    ide = ["<=", ">=", "<", ">"]
    for id in ide:
        if id in ele.replace("==>", ""):
            if "==>" in ele:
                ante, cons = ele.split("==>")[0].strip(), ele.split("==>")[1].strip()
                # print(f"ante:{ante}, cons:{cons}, id:{id}")
                boundary = get_parts(cons, id)
                # print(f"boundary_check_range: {boundary}")
                if boundary:
                    boundary["ante"] = ante[1:-1]
            else:
                boundary = get_parts(ele, id)
            return boundary
    return False


def get_feature_status(result):
    result = [ele for ele in result if ele != None]
    if len(set(result)) == 1 and result[0] == "accepted":
        """If only one label for all cex then remove"""
        return "remove"
    else:
        return "add_back"


def update_boundaries(a, b, mid, res, id):
    if id == ">=":
        if res == "accepted":
            b = mid - 1
        else:
            a = mid + 1
    else:
        if res == "accepted":
            a = mid + 1
        else:
            b = mid - 1
    return a, b
