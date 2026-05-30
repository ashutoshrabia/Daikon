import z3
import math
import os
import copy
import json
import time
from concurrent.futures import ThreadPoolExecutor
from itertools import repeat
from utilities import *
from smt_utilities import *
from counter_to_data import counter_to_data
from validation import validate_counter_ex


PATH = os.path.realpath("")
z3.set_param("smt.random_seed", 42)

################################### RANGE CONSTRAINTS HANDLER #######################################




def get_sat_model(mid, boundary, s_plus, other_constr, sel_constr, ope_types_dict, unsat_check=True):
    ante_constr = antecedent_constr(boundary, ope_types_dict)
    var = get_typed_exp(boundary["var"], ope_types_dict)
    hard_constraints = sel_constr + other_constr + [var == mid] + ante_constr
    if unsat_check:
        final_constraints = s_plus + hard_constraints
        tracked = []
        solver = z3.Solver()
        for i, c in enumerate(final_constraints):
            label = z3.Bool(f"c{i}")
            solver.assert_and_track(c, label)
            tracked.append((label, c))
        # solver.add(final_constraints)
        if solver.check() == z3.sat:
            print("BS Satisfiable")
        else:
            core = solver.unsat_core()
            print("BS Unsat core labels:", core)
            print("BS Unsat core constraints:")
            for lbl, c in tracked:
                if lbl in core:
                    print(c)
    s = z3.Optimize()
    for cons in hard_constraints:
        s.add(cons)
    for cons in s_plus:
        s.add_soft(cons)
    cex = get_solutions(s, 1)
    # return [
    #     {d.name(): convert_to_python_types(ele[d]) for d in ele.decls()} for ele in cex
    # ][0]
    # [Commented: original raised IndexError when cex is empty (solver returns no model)]
    if not cex:
        return None
    return {d.name(): convert_to_python_types(cex[0][d]) for d in cex[0].decls()}


def range_binary(
    boundary,
    s_plus,
    other_constr,
    sel_constr,
    ope_types_dict,
    sel_dict,
    url,
    oracle_queries,
):
    a, b = min(boundary["req_val"], boundary["val"]), max(
        boundary["req_val"], boundary["val"]
    )
    if not a == b:
        while a <= b:
            mid = math.floor((a + b) / 2)
            cex = get_sat_model(
                mid, boundary, s_plus, other_constr, sel_constr, ope_types_dict
            )
            print(f"Current boundaries::{a}, {b}, {mid}")
            print(f"Binary Search CEX::{cex=}")
            # if cex:
            # [Commented: skip iteration when get_sat_model returns None (no model found)]
            if cex is None:
                break
            oracle_queries += 1
            cex = counter_to_data(cex, ope_types_dict, sel_dict)
            # print(f"Range:{cex}")
            res = validate_counter_ex(cex, url)
            print(f"Binary Search Result::{res=}")
            a, b = update_boundaries(a, b, mid, res, boundary["id"])

    """Complete progress so a and b are swapped"""
    if boundary["id"] == ">=":
        if "ante" in boundary.keys():
            acc = f"({boundary['ante']})  ==>  ({boundary['var']} >= {a})"
            # rej = f"({boundary['ante']})  ==>  ({boundary['var']} < {a})"
        else:
            acc = f"{boundary['var']} >= {a}"
            # rej = f"{boundary['var']} < {a}"
    else:
        if "ante" in boundary.keys():
            acc = f"({boundary['ante']})  ==>  ({boundary['var']} <= {b})"
            # rej = f"({boundary['ante']})  ==>  ({boundary['var']} > {b})"
        else:
            acc = f"{boundary['var']} <= {b}"
            # rej = f"{boundary['var']} > {b}"

    # print(f"{acc=}")
    # print(f"{rej=}")
    return acc, oracle_queries

def range_constraints_handler(
    all_rules_acc,
    sel_constr,
    other_constr,
    ope_types_dict,
    sel_dict,
    url,
    oracle_queries,
):
    for idx in range(len(all_rules_acc)):
        print(f"BSrule--->{all_rules_acc[idx]}")
        # print(other_constr)
        s_plus = encode_in_smt(all_rules_acc, ope_types_dict)
        boundary = check_range(all_rules_acc[idx])
        if boundary and "val" in boundary.keys():
            rule = all_rules_acc.pop(idx)
            s_plus.pop(idx)
            """given a --> x>20 & x > 4 remove x > 4 from s_plus so that binary search
            continues without any obstruction otherwise binary search on x>20 would
            have stopped at x = 4 because of x > 4"""
            s_plus = remove_rules_matching_cons(boundary, s_plus, all_rules_acc)

            for ele in other_constr:
                if ele.decl().name() == boundary['id']:   # <=
                    lhs = ele.arg(0)
                    rhs = ele.arg(1)
                    if str(lhs) == boundary['var']:
                        boundary["req_val"] = rhs.as_long()
            # print(f"{ele=}")
            # print(f"{boundary=}")
            acc, oracle_queries = range_binary(
                boundary,
                s_plus,
                other_constr,
                sel_constr,
                ope_types_dict,
                sel_dict,
                url,
                oracle_queries,
            )
            #print(f"Binary Search Result::{acc=}")
            all_rules_acc.insert(idx, acc)
            s_plus.insert(idx, encode_in_smt([acc], ope_types_dict)[0])
            # s_plus.insert(idx, encode_in_smt([acc_rej[0]], ope_types_dict)[0])
            # if len(acc_rej) > 1:
            #     all_rules_rej.append(acc_rej[1])

    # for acc, rej in zip(all_rules_acc, all_rules_rej):
    #     print(f'{acc=}')
    #     print(f'{rej=}')
    # for acc in all_rules_acc:
    #     print(f'{acc=}')
    return all_rules_acc, oracle_queries


################################# COMPLEX CONSTRAINTS HANDLER #########################################


def get_cex_data(neg_constr, s_plus, sel_constr, other_constr, all_vars):
    # all_constraints = prune_unsat(s_plus, sel_constr, other_constr, neg_constr)
    # print(f'Length of all constraints::{len(all_constraints)}')
    all_constraints = maxSat(s_plus, sel_constr, other_constr, neg_constr)
    s = z3.Solver()
    s.add(all_constraints)
    cex = get_solutions_complex(s, len(all_vars), all_vars)
    data = [
        {str(var): convert_to_python_types(d[var]) for var in d.keys()} for d in cex
    ]
    s.reset()
    data = hyper_sample(s, data, all_constraints, all_vars)
    return data


def validate_cex_data(data, ope_types_dict, sel_dict, url):
    results = []
    data_copy = copy.deepcopy(data)
    for idx, cex in enumerate(data_copy):
        cex = counter_to_data(cex, ope_types_dict, sel_dict)
        # if idx == 0:
        # print(f"{cex=}")
    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(validate_counter_ex, data_copy, repeat(url)))
    return data_copy, results


def complex_contraints_handler(
    all_rules_acc,
    sel_constr,
    other_constr,
    ope_types_dict,
    sel_dict,
    url,
    oracle_queries,
    logging,
):
    s_plus = encode_in_smt(all_rules_acc, ope_types_dict)
    all_vars = get_all_vars(all_rules_acc, ope_types_dict)
    idx_to_remove = []
    for idx in range(len(all_rules_acc)):
        print(f"rule--->{all_rules_acc[idx]}")
        boundary = check_range(all_rules_acc[idx])
        if not boundary or "var2" in boundary.keys():
            idx_to_remove.append(idx)
            neg_constr = s_plus[idx]
            s_plus_updated = [
                s_plus[i] for i in range(len(s_plus)) if i not in idx_to_remove
            ]
            data = get_cex_data(
                neg_constr, s_plus_updated, sel_constr, other_constr, all_vars
            )
            print(f"{data=}")
            oracle_queries += len(data)
            _, result = validate_cex_data(data, ope_types_dict, sel_dict, url)
            print(f"{result=}")
            feat_status = get_feature_status(result)
            if feat_status == "add_back":
                idx_to_remove.pop()
            else:
                continue
    if logging:
        f = open(f"{PATH}/statuslog.txt", "a")
        for idx in idx_to_remove:
            f.write(f"rule::{all_rules_acc[idx]}\nstatus::Remove\n")
        f.close()
    all_rules_acc = [
        all_rules_acc[idx]
        for idx in range(len(all_rules_acc))
        if idx not in idx_to_remove
    ]
    return all_rules_acc, oracle_queries


#############################################STRICTINEQ###################################


def get_sat_model_strictInq(boundary, s_plus, other_constr, sel_constr, ope_types_dict):
    s = z3.Solver()
    s.add(s_plus)
    if "ante" in boundary.keys():
        if "&&" in boundary["ante"]:
            s.add(make_and_expr(boundary["ante"], ope_types_dict))
        else:
            s.add(make_plain_expr(boundary["ante"], ope_types_dict))
    var1 = get_typed_exp(boundary["var1"], ope_types_dict)
    var2 = get_typed_exp(boundary["var2"], ope_types_dict)
    s.add(var1 == var2)
    s.add(sel_constr)
    s.add(other_constr)
    cex = get_solutions(s, 1)
    if cex:
        return [
            {d.name(): convert_to_python_types(ele[d]) for d in ele.decls()}
            for ele in cex
        ][0]
    else:
        return None


def strictInq(
    all_rules_acc,
    sel_constr,
    other_constr,
    ope_types_dict,
    sel_dict,
    url,
    oracle_queries,
):
    """This will just convert strict inequalities to non-strict inequalities if possible.
    Rules might be correct or may be incorrect, if incorrect will be removed by complex constraint handler
    """
    s_plus = encode_in_smt(all_rules_acc, ope_types_dict)
    for idx in range(len(all_rules_acc)):
        boundary = check_range(all_rules_acc[idx])
        if boundary and "var2" in boundary.keys():
            rule = all_rules_acc.pop(idx)
            ex_rule = s_plus.pop(idx)
            cex = get_sat_model_strictInq(
                boundary, s_plus, other_constr, sel_constr, ope_types_dict
            )
            if cex:
                # cex = counter_to_data(cex, ope_types_dict, sel_dict)
                oracle_queries += 1

                # print(f"Strict::{cex}")
                res = validate_counter_ex(cex, url)
                if res == "accepted":
                    if "ante" in boundary.keys():
                        if boundary["id"] == ">":
                            all_rules_acc.insert(
                                idx,
                                f'({boundary["ante"]}) ==> ({boundary["var1"]} >= {boundary["var2"]})',
                            )
                            s_plus.insert(
                                idx,
                                encode_in_smt(
                                    [
                                        f'({boundary["ante"]}) ==> ({boundary["var1"]} >= {boundary["var2"]})'
                                    ],
                                    ope_types_dict,
                                )[0],
                            )
                        else:
                            all_rules_acc.insert(
                                idx,
                                f'({boundary["ante"]}) ==> ({boundary["var1"]} <= {boundary["var2"]})',
                            )
                            s_plus.insert(
                                idx,
                                encode_in_smt(
                                    [
                                        f'({boundary["ante"]}) ==> ({boundary["var1"]} <= {boundary["var2"]})'
                                    ],
                                    ope_types_dict,
                                )[0],
                            )
                    else:
                        if boundary["id"] == ">":
                            all_rules_acc.insert(
                                idx, f'{boundary["var1"]} >= {boundary["var2"]}'
                            )
                            s_plus.insert(
                                idx,
                                encode_in_smt(
                                    [f'{boundary["var1"]} >= {boundary["var2"]}'],
                                    ope_types_dict,
                                )[0],
                            )
                        else:
                            all_rules_acc.insert(
                                idx, f'{boundary["var1"]} <= {boundary["var2"]}'
                            )
                            s_plus.insert(
                                idx,
                                encode_in_smt(
                                    [f'{boundary["var1"]} <= {boundary["var2"]}'],
                                    ope_types_dict,
                                )[0],
                            )
                else:
                    all_rules_acc.insert(idx, rule)
                    s_plus.insert(idx, ex_rule)
            else:
                all_rules_acc.insert(idx, rule)
                s_plus.insert(idx, ex_rule)

    return all_rules_acc, oracle_queries


##################################################### Main for SMT #######################################


def smt_main(
    max_iter,
    all_rules_acc: list,
    sel_dict: dict,
    all_cols,
    ope_types_dict,
    url,
    oracle_queries,
    logging,
):
    all_rules_rej = []
    all_rules_acc_prev = []
    sel_constr = get_sel_constr(sel_dict)
    other_constr = get_other_constr(all_cols, ope_types_dict)
    idxc = 0
    while set(all_rules_acc) != set(all_rules_acc_prev) and idxc < max_iter:
        print(f"Current Iteration: {idxc}")
        print("Hypothesis Pruning Starts")
        start_idxc = time.time()
        all_rules_acc_prev = all_rules_acc
        all_rules_acc, oracle_queries = strictInq(
            all_rules_acc,
            sel_constr,
            other_constr,
            ope_types_dict,
            sel_dict,
            url,
            oracle_queries,
        )
        all_rules_acc, oracle_queries = complex_contraints_handler(
            all_rules_acc,
            sel_constr,
            other_constr,
            ope_types_dict,
            sel_dict,
            url,
            oracle_queries,
            logging,
        )
        print("Relaxing Hypothesis with Binary Search")
        all_rules_acc, oracle_queries = range_constraints_handler(
            all_rules_acc,
            sel_constr,
            other_constr,
            ope_types_dict,
            sel_dict,
            url,
            oracle_queries,
        )
        # print(f"Printing all rules at the end of iter {idxc}".format(idxc))
        # print(f"Total Rules: {len(all_rules_acc)}")
        # for rule in all_rules_acc:
        #     print(f"{rule}")
        if logging:
            f = open(f"{PATH}/log.txt", "a")
            f.write(f"No of rules in iter {idxc} : {len(all_rules_acc_prev)}\n")
            f.write(f"Time taken in iter {idxc} : {time.time()-start_idxc}\n")
            f.close()
        idxc += 1
        print(f"Current Iteration: {idxc}")
    all_rules_acc = filter_rules(all_rules_acc)
    all_rules_rej = [f"not({all_rules_acc[idx]})" for idx in range(len(all_rules_acc))]
    with open(
        f'{PATH}/results/accepted/{url.replace("-", "")}.txt',  # replaced url.split("/")[-2].replace("-", "") with this url.replace("-", "")
        "w",
    ) as f:
        for acc in all_rules_acc:
            f.write(f"{acc}\n")
    with open(
        f'{PATH}/results/rejected/{url.replace("-", "")}.txt',  # replaced url.split("/")[-2].replace("-", "") with this url.replace("-", "")
        "w",
    ) as f:
        for rej in all_rules_rej:
            f.write(f"{rej}\n")
    return all_rules_acc, oracle_queries
