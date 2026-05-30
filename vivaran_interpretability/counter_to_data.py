import pandas as pd
import numpy as np
import random
import os
import json
import string
from datetime import timedelta
from smt_utilities import read_interval

PATH = os.path.realpath("")


################################## GENERATORS #####################################################
def gen_text(_min=1, _max=200):
    n = random.randint(_min, _max)
    return "".join(random.choices(string.ascii_letters + string.digits, k=n))


###################################################################################################


def merge_ne_feat(cex, ope_types_dict):
    all_ne_feat = [
        ope_types_dict[key]
        for key in ope_types_dict.keys()
        if key in ["Date", "NumFloat", "NumInt"]
    ]
    all_ne_feat = [f"ne_{item}" for sublist in all_ne_feat for item in sublist]
    req_ne_feat = [key for key in cex.keys() if key in all_ne_feat]
    req_ne_feat = {ele: cex[ele] for ele in req_ne_feat}
    for key in req_ne_feat.keys():
        key_cex = key[key.find("_") + 1 :]
        if req_ne_feat[key] == True:
            cex[key_cex] = eval(str(cex[key_cex]))
            del cex[key]
        else:
            del cex[key_cex]
            del cex[key]
    return cex


def handle_text_ne(cex, ope_types_dict):
    req_feat = [ele for ele in ope_types_dict["String"] if f"ne_{ele}" in cex.keys()]
    for ele in req_feat:
        if cex[f"ne_{ele}"]:
            cex[ele] = gen_text()
            del cex[f"ne_{ele}"]
        else:
            del cex[f"ne_{ele}"]
    return cex


def handle_select(cex, ope_types_dict, sel_dict):
    sel_feat = [ele for ele in ope_types_dict["Select"] if ele in cex.keys()]
    for ele in sel_feat:
        cex[ele] = sel_dict[ele][int(str(cex[ele]))]
    return cex


def handle_link_ne(cex, ope_types_dict):
    link_feat = [ele for ele in ope_types_dict["Link"] if f"ne_{ele}" in cex.keys()]
    for ele in link_feat:
        if cex[f"ne_{ele}"]:
            cex[ele] = True
            del cex[f"ne_{ele}"]
        else:
            del cex[f"ne_{ele}"]
    return cex


def handle_check_ne(cex, ope_types_dict):
    ## For choice we do not have ne_ operation
    check_feat = [ele for ele in ope_types_dict["Choice"] if ele in cex.keys()]
    for ele in check_feat:
        if not cex[ele]:
            del cex[ele]
    return cex


def add_delta(n_days):
    def_interval = read_interval()
    n_days = int(str(n_days))
    end_date = pd.Timestamp(def_interval["Date"][0]) + timedelta(days=n_days)
    return end_date


def convert_to_date(cex, ope_types_dict):
    date_feat = [ele for ele in ope_types_dict["Date"] if ele in cex.keys()]
    for ele in date_feat:
        cex[ele] = add_delta(cex[ele])
        cex[ele] = pd.to_datetime(cex[ele]).strftime("%d-%m-%Y")
    return cex


def handle_select_ne(cex, ope_types_dict, sel_dict):
    """If ne_select is false then ideally we should delete ne_select and set
    dict[ele] = False so even if select options have empty then None will be returned
    by the fuzzer.
    Although for custom validation"""
    sel_feat = [ele for ele in ope_types_dict["Select"] if f"ne_{ele}" in cex.keys()]
    for ele in sel_feat:
        if not cex[f"ne_{ele}"]:
            del cex[f"ne_{ele}"]
            if None in sel_dict[ele]:
                cex[ele] = 0
            else:
                del cex[ele]
        else:
            del cex[f"ne_{ele}"]
            if None in sel_dict[ele] and cex[ele] == 0:
                cex[ele] = random.randint(1, len(sel_dict[ele]) - 1)
    return cex


# counter_to_data(cex, types_dict, sel_dict, iter)
def counter_to_data(cex, ope_types_dict, sel_dict):
    cex = merge_ne_feat(cex, ope_types_dict)
    cex = handle_text_ne(cex, ope_types_dict)
    cex = handle_select_ne(cex, ope_types_dict, sel_dict)
    cex = handle_select(cex, ope_types_dict, sel_dict)
    cex = handle_link_ne(cex, ope_types_dict)
    cex = handle_check_ne(cex, ope_types_dict)
    cex = convert_to_date(cex, ope_types_dict)
    return cex



##################################################################################
