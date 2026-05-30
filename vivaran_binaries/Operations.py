import pandas as pd
import numpy as np
import itertools
import datetime
import json


class Operations:
    def __init__(self, data_df, types_dict) -> None:
        self.data_df = data_df
        self.types_dict = types_dict

    def choice_operations(self):
        """Transform Choice to 0 and 1"""
        transformed_df = pd.DataFrame()
        for ele in self.types_dict["Choice"]:
            transformed_df[ele] = (
                self.data_df[ele]
                .map({"True": 1, "False": 0, False: 0, True: 1})
                .to_list()
            )
        transformed_df = transformed_df.astype(pd.Int64Dtype())
        return transformed_df

    def bool_operations(self):
        """Transform Choice to 0 and 1"""
        transformed_df = pd.DataFrame()
        for ele in self.types_dict["Bool"]:
            transformed_df[ele] = (
                self.data_df[ele].to_list()
            )
        transformed_df = transformed_df.astype(pd.Int64Dtype())
        return transformed_df

    def general_operations(self):
        """Define a non-empty transformation for all the columns except Choice columns"""
        transformed_df = pd.DataFrame()
        general_op_cols = [
            self.types_dict[ele]
            for ele in self.types_dict.keys()
            if ele not in ["Choice"]
        ]
        general_op_cols = [item for sublist in general_op_cols for item in sublist]
        for col in general_op_cols:
            values = self.data_df[col].to_list()
            transformed_df[f"ne_{col}"] = [int(not pd.isnull(s)) for s in values]

        return transformed_df

    def selection_operations(self, sel_dict):
        """Map selection columns to integers"""
        transformed_df = pd.DataFrame()
        for col in self.types_dict["Select"]:
            mapping = {val: str(idx) for idx, val in enumerate(sel_dict[col])}
            transformed_df[col] = self.data_df[col].map(mapping).to_list()
        return transformed_df

    def date_operations(self, requires_diff):
        """Convert date to int and find difference with current date if requires_diff is True, currently requires_diff is False"""
        transformed_df = pd.DataFrame()
        # Columns required for date operations
        date_cols = self.types_dict["Date"]
        for col in date_cols:
            transformed_df[col] = pd.to_datetime(self.data_df[col], dayfirst=True)
            transformed_df[col] = convert_to_int(transformed_df[col])
        # Difference with current date
        if requires_diff:
            """If difference is required know with cdiff and ddiff"""
            # for col in date_cols:
            #     transformed_df[f"cdiff_{col}"] = transformed_df[col].apply(date_curr_diff).to_list()
            # Pair wise date difference
            transformed_df = date_diff_all_cols(date_cols, transformed_df)
            transformed_df.drop(columns=date_cols, inplace=True)
        transformed_df = transformed_df.astype(pd.Int64Dtype())
        # transformed_df.to_csv("check_date.csv")
        return transformed_df

    def numInt_operations(self, requires_diff):
        """Convert numInt to int and find difference with current date if requires_diff is True, currently requires_diff is False"""
        transformed_df = pd.DataFrame()
        # Columns required for date operations
        num_cols = self.types_dict["NumInt"]
        for col in num_cols:
            transformed_df[col] = pd.to_numeric(
                self.data_df[col], errors="coerce"
            ).convert_dtypes()
            # transformed_df[f"int_{col}"] = self.data_df[col].astype(pd.Int64Dtype())
        if requires_diff:
            transformed_df = num_diff_all_cols(transformed_df, num_cols, "int")
        return transformed_df

    def numFloat_operations(self, requires_diff):
        """Convert numFloat to float and find difference with current date if requires_diff is True, currently requires_diff is False"""
        transformed_df = pd.DataFrame()
        # Columns required for date operations
        num_cols = self.types_dict["NumFloat"]
        for col in num_cols:
            transformed_df[col] = self.data_df[col].astype(float)
        if requires_diff:
            transformed_df = num_diff_all_cols(transformed_df, num_cols, "float")
        return transformed_df


#######################Utilities for operation functions##############################


###########################Date Operation Utilities######################################
def date_curr_diff(date_):
    if pd.isnull(date_):
        return np.nan
    curr_date = np.datetime64("today")
    # date_str = datetime.strptime(date_str, '%d-%m-%Y').date()
    return (curr_date - date_).days


def date_diff(d1: pd.Series, d2: pd.Series):
    diff_lst = (d1 - d2).dt.days.to_list()
    diff_lst = [ele if not pd.isnull(ele) else 0 for ele in diff_lst]
    return diff_lst
    # return (d1 - d2).dt.days.to_list()


def date_diff_all_cols(date_cols: list, tf: pd.DataFrame):
    subset_dates = list(itertools.combinations(date_cols, 2))
    for ele in subset_dates:
        tf[f"{ele[0]}_ddiff_{ele[1]}"] = date_diff(tf[ele[0]], tf[ele[1]])
    return tf


def convert_to_int(d1: pd.Series):
    """This is just for DAIKON"""
    return (d1 - pd.Timestamp("1980-01-01")).dt.days.to_list()


#######################################################################################
#####################################Numerical Utilities###############################
def num_diff(n1: pd.Series, n2: pd.Series, typ):
    res = (n1 - n2).to_list()
    if typ == "int":
        return res
    else:
        return [round(ele, 2) for ele in res]


def num_diff_all_cols(tf: pd.DataFrame, num_cols, typ):
    subset_dates = list(itertools.combinations(num_cols, 2))
    for ele in subset_dates:
        tf[f"{typ}_{ele[0]}ndiff{ele[1]}"] = num_diff(tf[ele[0]], tf[ele[1]], typ)
    return tf


#######################################################################################
