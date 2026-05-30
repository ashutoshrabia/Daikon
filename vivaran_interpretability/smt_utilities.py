import z3
import pandas as pd
import json
import os
import numpy as np
import random


PATH = os.path.dirname(os.path.realpath(__file__))
z3.set_param("smt.random_seed", 42)

############################ Extracting variables from rules #############################################


def get_ope(s: str):
    for ope in ["<=", ">=", "==", "!=", "<", ">"]:
        if ope in s:
            return ope
    return None


def isfloatInt(s):
    try:
        eval(s)
        return True
    except NameError:
        return False


def get_plain_expr_vars(part: str):
    """a part in general can have not, <=, >=, ==, <, >, !="""
    vars = set()
    part = part.replace(" ", "")
    part_copy = part.replace("not(", "(").replace("(", "").replace(")", "")
    ope = get_ope(part_copy)
    if ope:
        lhs, rhs = part_copy.split(ope)[0].strip(), part_copy.split(ope)[1].strip()
        vars.add(lhs)
        if not isfloatInt(rhs):
            vars.add(rhs)
    else:
        vars.add(part_copy)
    return vars


def get_and_expr_vars(ante):
    ante = ante.replace(" ", "")
    ante_copy = ante.replace("not(", "(")
    and_vars = set()
    for ele in ante_copy.split("&&"):
        vars = get_plain_expr_vars(ele)
        and_vars = and_vars.union(vars)
    return and_vars


def get_vars_in_imply(rule):
    implies_vars = set()
    ante, cons = rule.split("==>")[0].strip(), rule.split("==>")[1].strip()
    if "&" in ante:
        and_vars = get_and_expr_vars(ante)
        implies_vars = implies_vars.union(and_vars)
    else:
        vars = get_plain_expr_vars(ante)
        implies_vars = implies_vars.union(vars)
    if "&" in cons:
        and_vars = get_and_expr_vars(cons)
        implies_vars = implies_vars.union(and_vars)
    else:
        vars = get_plain_expr_vars(cons)
        implies_vars = implies_vars.union(vars)
    return implies_vars


def get_rule_vars(rule):
    if "==>" in rule:
        return list(get_vars_in_imply(rule))
    else:
        return list(get_plain_expr_vars(rule))


def get_all_vars(all_rules, ope):
    all_vars = []
    all_typed_vars = []
    for rule in all_rules:
        all_vars += get_rule_vars(rule)
    all_vars = list(set(all_vars)) + ope["Select"]
    for var in all_vars:
        all_typed_vars.append(get_typed_exp(var, ope))
    return all_typed_vars


################################### Encode Daikon Invs in SMT #######################################
def get_typed_exp(var, ope_types_dict):
    if var in ope_types_dict["Choice"] or "ne_" in var or var in ope_types_dict["Bool"]:
        return z3.Bool(var)
    elif var in (
        ope_types_dict["Select"] + ope_types_dict["NumInt"] + ope_types_dict["Date"]
    ):
        return z3.Int(var)
    elif var in ope_types_dict["NumFloat"]:
        return z3.Real(var)
    else:
        return eval(var)


def get_z3_encoding(s: str, ope, ope_types_dict):
    lhs, rhs = s.split(ope)[0].strip(), s.split(ope)[1].strip()
    lhs, rhs = get_typed_exp(lhs, ope_types_dict), get_typed_exp(rhs, ope_types_dict)
    if ope == "<=":
        return lhs <= rhs
    elif ope == ">=":
        return lhs >= rhs
    elif ope == "==":
        if type(lhs) == z3.BoolRef and type(rhs) == int and rhs == 0:
            return lhs == False
        elif type(lhs) == z3.BoolRef and type(rhs) == int and rhs == 1:
            return lhs == True
        return lhs == rhs
    elif ope == "!=":
        if type(lhs) == z3.BoolRef and type(rhs) == int and rhs == 0:
            return lhs != False
        elif type(lhs) == z3.BoolRef and type(rhs) == int and rhs == 1:
            return lhs != True
        return lhs != rhs
    elif ope == "<":
        return lhs < rhs
    else:
        return lhs > rhs


def make_plain_expr(part: str, ope_types_dict):
    """a part in general can have not, <=, >=, ==, <, >, !="""
    part = part.replace(" ", "")
    part_copy = part.replace("not(", "(").replace("(", "").replace(")", "")
    ope = get_ope(part_copy)
    if ope:
        part_copy = get_z3_encoding(part_copy, ope, ope_types_dict)
    else:
        part_copy = get_typed_exp(part_copy, ope_types_dict)
    if "not" in part:
        return z3.Not(part_copy)
    else:
        return part_copy


def make_and_expr(ante, ope_types_dict):
    ante = ante.replace(" ", "")
    ante_copy = ante.replace("not(", "(")
    and_lst = []
    for ele in ante_copy.split("&&"):
        ele = make_plain_expr(ele, ope_types_dict)
        and_lst.append(ele)
    if "not" in ante:
        return z3.Not(z3.And(and_lst))
    else:
        return z3.And(and_lst)


def smt_implies(rule, split: bool, ope_types_dict):
    ante, cons = rule.split("==>")[0].strip(), rule.split("==>")[1].strip()
    if "&" in ante:
        ante = make_and_expr(ante, ope_types_dict)
    else:
        ante = make_plain_expr(ante, ope_types_dict)
    if "&" in cons:
        cons = make_and_expr(cons, ope_types_dict)
    else:
        cons = make_plain_expr(cons, ope_types_dict)
    if split == True:
        return ante, cons
    else:
        return z3.Implies(ante, cons)


def encode_in_smt(rules, ope_types_dict):
    implications = [ele for ele in rules if "==>" in ele]
    others = [ele for ele in rules if ele not in implications]
    smt_rules = []
    for rule in implications:
        smt_rules.append(smt_implies(rule, False, ope_types_dict))
    for rule in others:
        ope = get_ope(rule)
        smt_rules.append(get_z3_encoding(rule, ope, ope_types_dict))
    return smt_rules


################################### Encode boundary constraints in SMT #######################################
def get_sel_constr(sel_dict):
    """If None is one of the select options then start from 1 else 0"""
    sel_constr = []
    for key, value in sel_dict.items():
        # if None in value:
        #     sel_constr.append(z3.Int(key) >= 1)
        # else:
        sel_constr.append(z3.Int(key) >= 0)
        sel_constr.append(z3.Int(key) <= (len(value) - 1))
    return sel_constr


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


def read_interval():
    with open(f"{PATH}/interval.json", "r") as json_file:
        def_interval = json.load(json_file)
        json_file.close()
    return def_interval


def get_other_constr(all_cols, ope_types_dict):
    """Encodes boundary constraints for each type of variable in SMT"""
    def_interval = read_interval()
    # def_interval["Date"] = convert_to_int(def_interval["Date"])
    other_constr = []
    for col in all_cols:
        if col in ope_types_dict["Date"]:
            other_constr.append(z3.Int(col) >= def_interval["Date"][0])
            other_constr.append(z3.Int(col) <= def_interval["Date"][1])
        elif col in ope_types_dict["NumInt"]:
            other_constr.append(z3.Int(col) >= def_interval["NumInt"][0])
            other_constr.append(z3.Int(col) <= def_interval["NumInt"][1])
        elif col in ope_types_dict["NumFloat"]:
            other_constr.append(z3.Real(col) >= def_interval["NumFloat"][0])
            other_constr.append(z3.Real(col) <= def_interval["NumFloat"][1])
    #print(f"other_constr: {other_constr}")
    return other_constr


################################################ PRUNE UNSAT PART ######################################################
def add_and_track(s, constraint_dict):
    for label, cons in constraint_dict.items():
        s.assert_and_track(cons, label)
    return s


def get_minimal_unsat_core(s, cons_d):
    unsat_dict = {
        key: value
        for key, value in cons_d.items()
        if z3.Bool(f"{key}") in s.unsat_core()
    }
    return unsat_dict


def prune_unsat(s_plus, sel_constr, other_constr, neg_constr):
    s_plus = s_plus + sel_constr + other_constr + [z3.Not(neg_constr)]
    s = z3.Solver()
    s.set(unsat_core=True)
    cons_d = {f"a{idx}": ele for idx, ele in enumerate(s_plus)}
    s = add_and_track(s, cons_d)
    if s.check() == z3.sat:
        return s_plus
    else:
        unsat_dict = get_minimal_unsat_core(s, cons_d)
        unsat_dict = {
            key: value
            for key, value in unsat_dict.items()
            if value not in [z3.Not(neg_constr)]
        }
        #print(f'{unsat_dict=}')
        """You cannot not remove everyting that resides in unsat core (it will be a blunder) rather everytime first remove the constraint matching cons,
        if there is no such constraint then randomly remove one constraint from unsat core and check if it is sat or not, if it is sat then we can remove that constraint else we put it back and try with another constraint from unsat core"""
        s_plus = [ele for ele in s_plus if ele not in unsat_dict.values()]
        """We add sel_constr and other_constr since sometimes they are also removed in unsat core"""
        s_plus = list(set(s_plus + sel_constr + other_constr))
        return s_plus


def maxSat(s_plus, sel_constr, other_constr, neg_constr, unsat_check=False):

    if unsat_check:
        final_constraints = s_plus + sel_constr + other_constr + [z3.Not(neg_constr)]
        tracked = []
        solver = z3.Solver()
        for i, c in enumerate(final_constraints):
            label = z3.Bool(f"c{i}")
            solver.assert_and_track(c, label)
            tracked.append((label, c))
        # solver.add(final_constraints)
        if solver.check() == z3.sat:
            return final_constraints
        else:
            core = solver.unsat_core()
            #print("Unsat core labels:", core)
            print("Unsat core constraints:")
            for lbl, c in tracked:
                if lbl in core:
                    print(c)
    optimizer = z3.Optimize()
    # Add hard constraints
    hard_constraints = sel_constr + other_constr + [z3.Not(neg_constr)]
    for constraint in hard_constraints:
        optimizer.add(constraint)

    # Add soft constraints with a penalty
    soft_constraints = []
    for constraint in s_plus:
        optimizer.add_soft(constraint)
        soft_constraints.append(constraint)

    # Check if the optimization problem is satisfiable
    if optimizer.check() == z3.sat:
        model = optimizer.model()
        satisfiable_constraints = []
        satisfiable_constraints.extend(hard_constraints)
        for constraint in soft_constraints:
            if z3.is_true(model.evaluate(constraint, model_completion=True)):
                satisfiable_constraints.append(constraint)
        return satisfiable_constraints
    else:
        print("This was Unsat")
        return hard_constraints


############################################Getting Counter Examples##############################
def block_model(s, m):
    s.add(z3.Or([f() != m[f] for f in m.decls() if f.arity() == 0]))


def get_solutions(s, no_sols=1):
    solutions = []
    for _ in range(no_sols):
        status = s.check()
        if status == z3.sat:
            solutions.append(s.model())
            block_model(s, s.model())
    return solutions


def combine_df(il, cl):
    al = [{d.name(): ele[d] for d in ele.decls()} for ele in il]
    rl = [{d.name(): ele[d] for d in ele.decls()} for ele in cl]
    al = pd.DataFrame(al)
    rl = pd.DataFrame(rl)
    frames = [al, rl]
    final_df = pd.concat(frames, axis=0, ignore_index=True)
    return final_df


def convert_to_python_types(val):
    if z3.is_int(val):
        return val.as_long()
    elif z3.is_bool(val):
        return eval(f"{val}")
    else:
        val = val.numerator_as_long() / val.denominator_as_long()
        return round(float(val), 2)


#####################################################Hyperplane Sampling####################################################
def get_solutions_complex(s, no_sols, var_list):
    solutions = []
    for _ in range(no_sols):
        status = s.check()
        if status == z3.sat:
            solutions.append(
                {d: s.model().eval(d, model_completion=True) for d in var_list}
            )
            block_model(s, s.model())  # changes a parameter here s.model()
    return solutions


def fit_line_or_hyperplane(points):
    if len(points) == 2 and len(points[0]) == 2:
        x1, y1 = points[0]
        x2, y2 = points[1]
        # print(f"{points=}, {(x1, y1)=}, {(x2, y2)=}")
        slope = (y2 - y1) / (x2 - x1)
        intercept = y1 - slope * x1
        return slope, intercept
    elif len(points) >= 3 and len(points[0]) >= 2:
        centroid = np.mean(points, axis=0)
        u, s, vh = np.linalg.svd(points - centroid, full_matrices=False)
        normal = vh[-1]
        # print(f"{normal=}")
        coefficients = normal / np.linalg.norm(normal)
        intercept = -np.dot(coefficients, centroid)
        return coefficients, intercept
    else:
        raise ValueError("Invalid number of points or dimensions")


def construct_eq(coeffs, inter, all_vars):
    constr = []
    # print(f"{coeffs=}, {inter=}, {all_vars=}")

    for coef, var in zip(coeffs, all_vars):
        if z3.is_bool(var):
            exp = coef * z3.If(var, 1, 0)
        else:
            exp = coef * var
        constr.append(exp)
    constr.append(inter)
    return z3.Sum(constr)


def hyper_sample(s, data, all_constaints, all_vars):
    iterations = 0
    # print(data)
    init_len = len(data)
    """data: list of dictionaries, var:valuation pairs"""
    if init_len < len(all_vars):
        return data

    while len(data) <= init_len + 30 and iterations <= 100:
        cex = []
        points = [list(item.values()) for item in data]
        points = random.sample(points, len(all_vars))
        # print(f"{points=}")
        coeffs, inter = fit_line_or_hyperplane(points)
        coeffs = np.atleast_1d(coeffs)
        coeffs, inter = np.round(coeffs, decimals=2).tolist(), round(inter, 2)
        eq1 = construct_eq(coeffs, inter, all_vars)
        all_constaints.append(eq1 > 0)
        s.add(all_constaints)
        cex = get_solutions_complex(s, 1, all_vars)
        s.reset()
        all_constaints.pop()
        eq2 = construct_eq(coeffs, inter, all_vars)
        all_constaints.append(eq2 < 0)
        s.add(all_constaints)
        cex += get_solutions_complex(s, 1, all_vars)
        s.reset()
        all_constaints.pop()
        cex = [
            {str(var): convert_to_python_types(d[var]) for var in d.keys()} for d in cex
        ]
        cex = [ele for ele in cex if ele not in data]
        data += cex
        iterations += 1
    if len(data) > 20:
        data = random.sample(data, 20)
    return data


#################################################Binary Search Utilities####################################################
def antecedent_constr(boundary, ope_types_dict):
    ante_constr = []
    if "ante" in boundary.keys():
        if "&&" in boundary["ante"]:
            ante_constr.append(make_and_expr(boundary["ante"], ope_types_dict))
        else:
            ante_constr.append(make_plain_expr(boundary["ante"], ope_types_dict))
    return ante_constr


def remove_rules_matching_cons(boundary, s_plus, all_rules_acc):
    """If others have x >= 100 then when solving d ==> x > 28 we remove x >= 100"""
    matching_str = f"{boundary['var']} {boundary['id']}"
    idx_to_remove = []
    for idx, ele in enumerate(all_rules_acc):
        if matching_str in ele:
            val = ele.split(matching_str)[1].strip(")").strip()
            try:
                eval(val)
                idx_to_remove.append(idx)
            except NameError:
                continue
    #print(f"Removing rules matching consequent: {[all_rules_acc[i] for i in idx_to_remove]}")
    s_plus = [s_plus[i] for i in range(len(s_plus)) if i not in idx_to_remove]
    return s_plus


##############################FILTER FINAL RULES ############################################
def remove_redundant_implies(implications, others):
    """Removes implications that are always true as consequent is always true"""
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


def filter_rules(rules):
    implications = [line for line in rules if "==>" in line]
    others = [line for line in rules if line not in implications]
    implications = remove_redundant_implies(implications, others)
    return implications + others
