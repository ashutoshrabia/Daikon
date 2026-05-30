import os
import pandas as pd
from utilities import *
from extract_rules import ExtractRules
from prune_hypothesis import smt_main
import warnings
import json

# from acc_rate import get_acceptance_rate
import argparse

warnings.simplefilter(action="ignore", category=FutureWarning)


parser = argparse.ArgumentParser()


def get_list():
    f = open(f"{PATH}/list_of_urls.txt", "r")
    list_of_urls = f.readlines()
    f.close()
    return [ele.strip() for ele in list_of_urls]


parser.add_argument(
    "--logging",
    help="put 'yes' (or 'y') if \
    you want to log detailed output in files",
)

parser.add_argument(
    "--max-iter",
    help="number of pruning iterations\
    for each benchmark",
    type=int,
)

parser.add_argument(
    "--url",
    help="You can execute individual benchmarks\
        by providing the url from the list_of_urls.txt",
)


args = parser.parse_args()

if str(args.logging).lower() in ["yes", "y"]:
    logging = True
else:
    logging = False

if args.max_iter is None:
    max_iter = 8
else:
    max_iter = args.max_iter


def initiate_logging(url, iterations):
    log_path = f"{PATH}/log.txt"
    status_log_path = f"{PATH}/statuslog.txt"
    if not os.path.exists(log_path):
        fl = open(log_path, "w")
    else:
        fl = open(log_path, "a")
    if not os.path.exists(status_log_path):
        fls = open(status_log_path, "w")
    else:
        fls = open(status_log_path, "a")
    fl.write(f"{url}---Iteration--{iterations}\n")
    fls.write(f"{url}---Iteration--{iterations}\n")
    fl.close()


# with open("spec.json", "r", encoding="utf-8") as f:
#     spec = json.load(f)
# func_name = spec.get("name", "target")
# list_of_programs = func_name.split(",")


def mainfun(progname):
    print(f"Processing {progname}...")
    data_df = pd.read_csv(f"{PATH}/data/{progname}.csv")
    data_df, ope_types_dict = preprocess_data(data_df, progname)
    # sel_dict = read_sel_dicts(url)
    sel_dict = {}
    iterations = 0
    acc_rate = 0
    oracle_queries = 0
    while acc_rate < 1 and iterations < 1:
        if logging:
            initiate_logging(progname, iterations)
        data_df_acc = data_df[data_df["label"] == 1]
        er_obj = ExtractRules(data_df_acc, ope_types_dict, progname)
        all_rules_acc, all_cols = er_obj.extract_all_rules(
            sel_dict, ope_types_dict, iterations
        )
        # print(f"all rules acc = {all_rules_acc}")
        # f = open(f"{PATH}/daik_deps/inv_{progname}.txt", "r")
        # all_rules_acc = f.readlines()
        # f.close()
        all_rules_acc = [ele.strip() for ele in all_rules_acc]
        all_cols = list(data_df.columns)
        all_rules_acc, oracle_queries = smt_main(
            max_iter,
            all_rules_acc,
            sel_dict,
            all_cols,
            ope_types_dict,
            progname,
            oracle_queries,
            logging,
        )
        #print(f"{all_rules_acc=}")
        # acc_rate, oracle_queries, dxd = get_acceptance_rate(
        #     url, all_rules_acc, ope_types_dict, sel_dict, oracle_queries
        # )
        # print(f"{acc_rate}")
        # data_df = pd.concat([data_df, dxd], axis=0, ignore_index=True)
        iterations += 1
    if logging:
        f = open(f"{PATH}/log.txt", "a")
        f.write(f"Total no of oracle queries :{oracle_queries}\n")
        f.close()


PATH = os.path.realpath("")
