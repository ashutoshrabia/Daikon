import pandas as pd
import numpy as np
from Operations import Operations
from parse import *
from itertools import combinations
from itertools import chain
import os
import json

PATH = os.path.realpath("")
"""defining transformation functions to prepare a dataset
Braod Categorization of types:
String : Data, Color, Text Editor
Date : Date
Numeric: Float, Int (Only general operations)
Selection: Select (Only general operations)
Choice: Check (handle them first by just mapping true:1 and false:0)"""


class ExtractRules:
    def __init__(self, data_df: pd.DataFrame, types_dict, progname) -> None:
        self.data_df = data_df
        self.types_dict = types_dict
        self.ope = Operations(self.data_df, self.types_dict)
        self.url = progname

    def daikon_data(self, sel_dict):
        """transforms the data_df to daikon format"""
        tf_choice = self.ope.choice_operations()
        tf_bool = self.ope.bool_operations()
        #tf_non_empty = self.ope.general_operations()
        tf_select = self.ope.selection_operations(sel_dict)
        tf_date = self.ope.date_operations(requires_diff=False)
        tf_numI = self.ope.numInt_operations(requires_diff=False)
        tf_numF = self.ope.numFloat_operations(requires_diff=False)
        tf = pd.concat(
            [
                tf_choice.reset_index(drop=True),
                tf_bool.reset_index(drop=True),
                #tf_non_empty.reset_index(drop=True),
                tf_select.reset_index(drop=True),
                tf_date.reset_index(drop=True),
                tf_numI.reset_index(drop=True),
                tf_numF.reset_index(drop=True),
            ],
            axis=1,
        )
        tf = tf.replace(np.nan, 0)
        all_cols = list(tf.columns)
        tf.to_csv(f"{PATH}/daik_deps/{self.url}.csv", index=False)
        return tf, all_cols

    def daikon_rules(self, sel_dict, ope_types_dict, iterations):
        """generates daikon rules for the given url"""
        format_decls_file(self.url, ope_types_dict)
        """convert csv to dtrace"""
        # st = f"$DAIKONDIR/scripts/convertcsv.pl -m nonsensical -decl ./daik_deps/{self.url}.decls ./daik_deps/{self.url}.csv"
        # added 2>/dev/null to suppress Perl "Use of uninitialized value" warnings from convertcsv.pl
        st = f"$DAIKONDIR/scripts/convertcsv.pl -m nonsensical -decl ./daik_deps/{self.url}.decls ./daik_deps/{self.url}.csv 2>/dev/null"
        os.system(st)
        """create split info"""
        create_split_info(sel_dict, ope_types_dict, self.url, iterations)
        """run daikon and generates invariants"""
        st = f"java -cp $DAIKONDIR/daikon.jar daikon.Daikon --nohierarchy --config $DAIKONDIR/myconfig.txt ./daik_deps/{self.url}.decls ./daik_deps/{self.url}.dtrace ./splitInfo/{self.url}.spinfo > ./daik_deps/inv_{self.url}.txt"
        os.system(st)
        os.system("rm -rf *.inv.gz")

    def extract_all_rules(self, sel_dict, ope_types_dict, iterations):
        """returns a list with 2 nested lists (implications and others)"""
        all_rules = {}
        tf, all_cols = self.daikon_data(sel_dict)
        self.daikon_rules(sel_dict, ope_types_dict, iterations)
        all_rules = parse_invs(self.url, ope_types_dict, tf)
        return all_rules, all_cols


###############UTILITIES FOR extract_rules.py###################################
def create_decls_lst(url, ope_types_dict):
    decls_lst = []
    decls_lst.extend(["DECLARE", "aprogram.point:::POINT"])
    daik_data = pd.read_csv(f"{PATH}/daik_deps/{url}.csv")
    for col in daik_data.columns:
        # id = str(col).split("_")[0]
        if col in ope_types_dict["Bool"]:
            decls_lst.extend([f"{col}", "boolean", "boolean", 1])
        elif col in ope_types_dict["Choice"]:
            decls_lst.extend([f"{col}", "boolean", "boolean", 1])
        elif "ne_" in col:
            decls_lst.extend([f"{col}", "boolean", "boolean", 2])
        elif col in ope_types_dict["Select"]:
            decls_lst.extend([f"{col}", "java.lang.String", "java.lang.String", 3])
        elif col in ope_types_dict["NumInt"]:
            decls_lst.extend([f"{col}", "int", "int", 4])
        elif col in ope_types_dict["NumFloat"]:
            decls_lst.extend([f"{col}", "double", "double", 5])
        elif col in ope_types_dict["Date"]:
            decls_lst.extend([f"{col}", "int", "int", 6])

    return decls_lst


def format_decls_file(url, ope_types_dict):
    decls_lst = create_decls_lst(url, ope_types_dict)
    f = open(f"{PATH}/daik_deps/{url}.decls", "w")
    for ele in decls_lst:
        f.write(f"{ele}\n")


def write_to_split_info(combined, chs, ss, ne_date, url):
    f = open(f"{PATH}/splitInfo/{url}.spinfo", "w")
    f.write(f"PPT_NAME aprogram.point:::POINT\n")
    for ele in combined:
        f.write(f"{ele[0]} && {ele[1]}\n")
    for ele in chs:
        f.write(f"{ele}\n")
    for lst in ss:
        for ele in lst:
            f.write(f"{ele}\n")
    for ele in ne_date:
        f.write(f"{ele[0]} && {ele[1]}\n")


def get_sel_splits(key, value):
    all_splits = []
    for idx, _ in enumerate(value):
        all_splits.append(f'{key} == "{str(idx)}"')
    return all_splits


def merge_split_points(check_splits, sel_splits, iterations):
    combined = []
    for ele1 in list(chain.from_iterable(sel_splits[:iterations])):
        for ele2 in check_splits:
            combined.append((ele2, ele1))
    return combined


def create_split_info(sel_dict, ope_types_dict, url, iterations):
    df = pd.read_csv(f"{PATH}/daik_deps/{url}.csv")
    sel_splits, check_splits = [], []
    check_sel_cols = [
        ele
        for ele in df.columns
        if ele in ope_types_dict.get("Choice", []) or ele in ope_types_dict.get("Select", [])
    ]
    ne_date_cols = [
        ele for ele in df.columns if ele[ele.find("_") + 1 :] in ope_types_dict.get("Date", [])
    ]
    ne_date_cols = list(combinations(ne_date_cols, 2))
    for ele in check_sel_cols:
        if ele in sel_dict.keys():
            sel_splits.append(get_sel_splits(ele, sel_dict[ele]))
        else:
            check_splits.append(ele)
    combined = merge_split_points(check_splits, sel_splits, iterations)
    #write_to_split_info(combined, check_splits, sel_splits, ne_date_cols, url)
