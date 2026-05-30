import os
from llm_generated import validation
from smt_utilities import *
from utilities import *
from validation import validate_cex_data

PATH = os.path.realpath("")

def get_cex_data(all_rules_acc, sel_constr, all_vars):
    s = z3.Solver()
    all_constraints = all_rules_acc + sel_constr
    s.add(all_constraints)
    cex = get_solutions_complex(s, len(all_vars), all_vars)
    data = [
        {str(var): convert_to_python_types(d[var]) for var in d.keys()} for d in cex
    ]
    s.reset()
    data = hyper_sample(s, data, all_constraints, all_vars)
    return data


def get_acceptance_rate(url, all_rules_acc, ope_types_dict, sel_dict, oracle_queries):
    all_vars = get_all_vars(all_rules_acc, ope_types_dict)
    all_rules_acc = encode_in_smt(all_rules_acc, ope_types_dict)
    sel_constr = get_sel_constr(sel_dict)
    data = get_cex_data(all_rules_acc, sel_constr, all_vars)
    oracle_queries += len(data)
    dxd, result = validate_cex_data(data, ope_types_dict, sel_dict, url)
    dxd = pd.DataFrame(dxd)
    dxd["result"] = result
    return (
        len([ele for ele in result if ele == "accepted"]) / len(result),
        oracle_queries,
        dxd,
    )
