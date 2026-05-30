import os
from collections import OrderedDict
from utilities import *

PATH = os.path.realpath("")


def ante_implying_itself(implications):
    imply_to_remove = []
    for ele in implications:
        ante, cons = ele.split("==>")[0].strip(), ele.split("==>")[1].strip()
        if ante == cons:
            imply_to_remove.append(ele)
        else:
            continue
    return [ele for ele in implications if ele not in imply_to_remove]


def add_inequality_constraints(lines, ope_types_dict, tf):
    req_cols = (
        ope_types_dict["Date"] + ope_types_dict["NumInt"] + ope_types_dict["NumFloat"]
    )
    req_cols = [col for col in tf.columns if col in req_cols]
    for col in req_cols:
        mini, maxi = min(tf[col]), max(tf[col])
        if f"{col} >= {mini}" not in lines:
            lines.append(f"{col} >= {mini}")
        if f"{col} <= {maxi}" not in lines:
            lines.append(f"{col} <= {maxi}")
    return lines


def remove_redundant(var, value, imp):
    # print(f"var: {var}--value: {value}")
    new_imp = []
    for ele in imp:
        ante, cons = ele.split("==>")[0].strip(), ele.split("==>")[1].strip()
        cons = cons.strip("(").strip(")")
        if f"{var} ==" in cons:
            lhs, rhs = cons.split("==")[0].strip(), cons.split("==")[1].strip()
            new_ele = f"{ante}  ==>  ({rhs} == {value})"
            # print(f"{new_ele=}")
            new_imp.append(new_ele)
        else:
            new_imp.append(ele)
    return list(set(new_imp))


def remove_redundant_implies(implications, others):
    """We will not use it here but we will use it once our algorithm terminates:
    Removes implications that are always true as consequent is always true"""
    redundant_imply = []
    for ele in others:
        for imply in implications:
            if "==>" in imply:
                val = imply.split("==>")[1]
            else:
                val = imply.split("<==>")[1]
            val = val.strip()
            ele = ele.strip()
            if f"({ele})" == val:
                redundant_imply.append(imply)
    return [ele for ele in implications if ele not in redundant_imply]


def remove_trivial_implications(implications):
    """EARLIER CASE: These are implications of type (a ==> a != 0) or (a && b) ==> (b != 0) or
    a ==> ne_a != 0 or (a && b) ==> ne_a != 0 or (a && b) ==> ne_b != 0
    CURRENT CASE: These are implications of type (a ==> a == 1) or (a && b) ==> (b == 1) or
    a ==> ne_a == 1 or (a && b) ==> ne_a == 1 or (a && b) ==> ne_b == 1"""
    imply_to_remove = []
    for imply in implications:
        ante, cons = imply.split("==>")[0], imply.split("==>")[1]
        if "== 1" in cons:
            cons_var = cons.split("==")[0].strip().strip("(")
            if cons_var in ante or cons_var[cons_var.find("_") + 1 :] in ante:
                imply_to_remove.append(imply)
    return [imply for imply in implications if imply not in imply_to_remove]


def remove_redundant_equality_implications(implications):
    """Implications of type: (a == 1)  ==>  (b == 1), (a == 1)  ==>  (b == a),
    (c == 0)  ==>  (d == 0), (c == 0)  ==>  (c == d),
    (status == '3')  ==>  (ne_a == 0), (status == '3')  ==>  (ne_a == ne_b),
    (status == '3')  ==>  (ne_b == 0)"""
    new_imp = []
    for imply in implications:
        ante, cons = imply.split("==>")[0].strip(), imply.split("==>")[1].strip()
        if "==" in cons:
            var1, var2 = cons.split("==")[0].strip().strip("("), cons.split("==")[
                1
            ].strip().strip(")")
            try:
                if type(eval(var2)) == int:
                    # print(f"var1:::{var1}==>var2:::{var2}")
                    new_imp.append(imply)
            except NameError:
                continue
        else:
            new_imp.append(imply)
    return new_imp


###########################################################################################


def get_imply_with_same_cons(cons, implications):
    imply_with_cons = []
    for imply in implications:
        cons1 = imply.split("==>")[1].strip()
        if cons1 == cons:
            imply_with_cons.append(imply)
    return imply_with_cons


def remove_redundant_cons_implications(implications):
    """Implications of type a ==> c and (a && b) ==> c, in this case (a && b) ==> c is removed"""
    imply_to_remove = []
    for imply in implications:
        # print(f"{imply=}")
        ante, cons = (
            imply.split("==>")[0].strip().strip("(").strip(")"),
            imply.split("==>")[1].strip(),
        )
        imply_with_cons = get_imply_with_same_cons(cons, implications)
        # print(f"{imply_with_cons}")
        imply_with_cons = sorted(imply_with_cons, key=len)
        imply_with_cons.remove(imply)
        for ele in imply_with_cons:
            if ante in ele.split("==>")[0]:
                imply_to_remove.append(ele)
        # imply_to_remove += imply_with_cons[1:]
    return [imply for imply in implications if imply not in imply_to_remove]


##################################################################################


############################## BI-IMPLICATION  ##################################


def get_split_points(url):
    neg_split_points = []
    split_points = []
    with open(f"{PATH}/splitInfo/{url}.spinfo", "r") as f:
        s_p = f.readlines()
        f.close()
    s_p = [ele.strip() for ele in s_p[1:]]
    for ele in s_p:
        if "==" in ele or "&&" in ele:
            split_points.append(f"({ele})")
            neg_split_points.append(f"(not({ele}))")
        else:
            split_points.append(f"({ele} == true)")
            neg_split_points.append(f"({ele} == false)")
    return split_points, neg_split_points


"""
To_do_in_future: I'm thinking of using ope_types_dict to check if any of the variables (found in ele of value)
belong to Select, Choice or ne class then use that rule to concretize map
Preserve the order:
1) if antecedent matches first matches with any original splits
then value = antecedent
2) if any consequent in values matches first matches with any original splits
then value = antecedent
3) if antecedent matches with any negated splits then value = antecedent
4) if any consequent in values matches with any negated splits then value = consequent
"""


def concretize_mapping(mapping, s_p, n_sp):
    modified_map = {}
    for key in mapping.keys():
        if key in s_p or key in n_sp:
            modified_map[key] = key
            continue
        for split in s_p:
            if split in mapping[key]:
                modified_map[key] = split
                break
        for split in n_sp:
            if split in mapping[key] and key not in modified_map.keys():
                modified_map[key] = split
                break
             
    return modified_map


def is_subset_bimply(s_p, bi_implications, updated_implications):
    s_p = [ele for ele in s_p if "&&" in ele]
    new_bimply = []
    sub_sp = []
    for ele in s_p:
        a, b = ele.split("&&")[0].strip().strip("("), ele.split("&&")[1].strip().strip(
            ")"
        )
        sub_sp.append(f"({a} == true)")
        sub_sp.append(f"({b} == true)")
    sub_sp = list(set(sub_sp))
    for ele in bi_implications:
        ante, cons = ele.split("<==>")[0].strip(), ele.split("<==>")[1].strip()
        # print(f"{ante=}")
        if ante in sub_sp:
            updated_implications.append(f"{ante} ==> {cons}")
        else:
            new_bimply.append(ele)
    return new_bimply, updated_implications


def process_bi_implications(bi_implications, implications, url):
    """First : Replace implications ante with smallest cons (matches the ante of considered implication)
    of the bi-implication
    Second: Remove the bi-implication
    This in turn removes all bi-implications"""
    mapping = {}
    updated_implications = []
    s_p, n_sp = get_split_points(url)
    """Why was this added? Because of which URL and because of which rule? It contradicts with
    task url rule (ne_completed_on == true) <==> (status == '5')"""
    # bi_implications, updated_implications = is_subset_bimply(
    #     s_p, bi_implications, updated_implications
    # )
    for idx, ele in enumerate(bi_implications):
        ante, cons = ele.split("<==>")
        ante, cons = ante.strip(), cons.strip()
        if ante not in mapping.keys():
            mapping[ante] = [cons]
        else:
            mapping[ante] += [cons]
    # print(f"PREVIOUS::{mapping}")
    mapping = concretize_mapping(mapping, s_p, n_sp)
    # print(f"AFTER::{mapping}")
    for key, value in mapping.items():
        if key != value:
            updated_implications.append(f"{value}  ==>  {key}")
    for ele in bi_implications:
        ante, cons = ele.split("<==>")
        ante, cons = ante.strip(), cons.strip()
        updated_implications.append(f"{ante}  ==>  {cons}")

    for ele in implications:
        ante, cons = ele.split("==>")
        ante, cons = ante.strip(), cons.strip()
        if ante in mapping.keys():
            updated_implications.append(ele.replace(ante, mapping[ante]))
        else:
            updated_implications.append(ele)
    return updated_implications



###############################CONTRAPOSITIVE#################################
def get_negation_exp(exp):
    neg_map = {"0": "1", "1": "0"}
    for key in neg_map.keys():
        if f"== {key}" in exp:
            return exp.replace(key, neg_map[key])


def find_contrapositive(imply, implications, req_implys):
    ante, cons = imply.split("==>")[0].strip(), imply.split("==>")[1].strip()
    ante_neq, cons_neg = get_negation_exp(ante), get_negation_exp(cons)
    if f"{cons_neg}  ==>  {ante_neq}" in implications:
        req_implys.append(f"{cons_neg}  ==>  {ante_neq}")
    return req_implys


def remove_contrapositive_implications(implications):
    req_implys = []
    for imply in implications:
        if "== 0" in imply or "== 1" in imply:
            if imply in req_implys:
                continue
            else:
                req_implys = find_contrapositive(imply, implications, req_implys)
    implications = [imply for imply in implications if imply not in req_implys]
    return implications


#############################################################################
####REMOVING ALL NOT's accept the one specided in splitinfo file
def remove_not_imply(implications, url):
    imply_to_remove = []
    with open(f"{PATH}/splitInfo/{url}.spinfo", "r") as f:
        s_p = f.readlines()
    s_p = [f"({ele.strip()})" for ele in s_p[1:] if "not(" in ele]
    not_implications = [imply for imply in implications if "(not(" in imply]
    for imply in not_implications:
        ante = imply.split("==>")[0].strip()
        if ante in s_p:
            continue
        else:
            imply_to_remove.append(imply)
    implications = [imply for imply in implications if imply not in imply_to_remove]
    return implications


def filter_range_constraints(others):
    new_others = []
    for ele in others:
        boundary = check_range(ele)
        if boundary and "val" in boundary.keys():
            continue
        else:
            new_others.append(ele)
    return new_others

            

####################################  MAIN    #####################################


def parse_invs(url, ope_types_dict, tf):
    f = open(f"{PATH}/daik_deps/inv_{url}.txt", "r")
    lines = f.readlines()
    lines = lines[
        lines.index("aprogram.point:::POINT\n") + 1 : lines.index("Exiting Daikon.\n")
    ]
    lines = [ele.strip() for ele in lines]
    

    ########################## PHASE 1 ######################################
    bi_implications = [ele for ele in lines if "<==>" in ele]
    implications = [ele for ele in lines if "==>" in ele and ele not in bi_implications]
    others = [ele for ele in lines if ele not in implications + bi_implications]
    implications = process_bi_implications(bi_implications, implications, url)
    lines = implications + others
    ####################################### PHASE 2 #############################################
    """We have:
    daikon.inv.unary.scalar.OneOfScalar.enabled = true and size = 1. But daikon
    considers int and booleans as scalar, hence it is important to remove
    a == 0 where a is of type NumInt or Date. """
    date_int_cols = ope_types_dict["NumInt"] + ope_types_dict["Date"]
    to_remove = [
        line
        for line in lines
        for ele in date_int_cols
        # not f"ne_{ele} == {0}" prevents from matching to ne_a == 0
        if (f"{ele} == {0}" in line and not f"ne_{ele} == {0}" in line)
    ]
    lines = [line for line in lines if line not in to_remove]

    """Convert true to 1 and false to 0"""
    lines = [
        ele.replace("== true", "== 1").replace("== false", "== 0") for ele in lines
    ]

    implications = [line for line in lines if "==>" in line]
    others = [line for line in lines if line not in implications]

    """Here we want to remove dependencies like s == 1 and n == 1 and s == n. To do so:
    given s == 1 and if s == n is also present then we remove s == n and append n == 1(Before appending 
    we also check if n == 1 is already present), if it is not already present in implications otherwise we just remove s == n.
    In this case it is important to have this before removing trivial implications (for reason see
    comments in remove_trivial_implications)"""

    for ele in others:
        if "==" in ele:
            var, value = ele.split("==")[0].strip(), ele.split("==")[1].strip()
            try:
                value = int(value)
            except ValueError:
                continue
            implications = remove_redundant(var, value, implications)

    implications = list(OrderedDict.fromkeys(implications))

    """its important to remove_circular_implications after above code beacuse
    above code resolves s == n part if present in others"""
    implications = remove_redundant_equality_implications(implications)
    implications = remove_trivial_implications(implications)
    implications = remove_redundant_cons_implications(implications)
    implications = remove_contrapositive_implications(implications)
    implications = ante_implying_itself(implications)

    # ########################## PHASE 3 ######################################
    """remove implications that contain %"""
    implications = [ele for ele in implications if "%" not in ele]
    others = [ele for ele in others if "%" not in ele]
    new_others = filter_range_constraints(others)
    implications = remove_redundant_implies(implications, new_others)

    """Remove writing to file after debugging phase"""
    f = open(f"{PATH}/daik_deps/inv_{url}.txt", "w")
    for ele in implications:
        f.write(f"{ele}\n")
    for ele in others:
        f.write(f"{ele}\n")
    return implications + others
