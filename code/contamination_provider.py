import logging
import numpy as np
import argparse
import os
import errno
import subprocess

from validphys.loader import Loader
from pathlib import Path
from validphys.core import DataSetInput
from validphys.core import TupleComp

log = logging.getLogger(__name__)
l = Loader()

def write_basic_cfac(cfacpath, name, dataset, cfac_mapping, cfac_quad_info, default_file_path, cfac_multiply, new_file_path, value_name, quad_file_path=None):
    """Writes a single new cfactor file.
    """
    with open(default_file_path,"r+") as f:
        cfac = f.readlines()
        f.close()

    if cfac_quad_info[name]:
        with open(quad_file_path) as f2:
            quad_cfac = f2.readlines()
            f2.close()

        # Parse the quadratic C-factor file, and store the results
        quad_values = []
        data_flag = False
        line_num = 0
        for line in quad_cfac:
            if data_flag:
                quad_values += [float(line.split()[0])]
            if line_num != 0 and line.find("***") > -1:
                data_flag = True
            line_num += 1                       

    # Parse the C-factor, and make the necessary changes.
    new_cfac = []
    data_flag = False
    line_num = 0

    for line in cfac:
        if line.find("Coefficient:") > -1:
            line = "Coefficient: " + str(cfac_mapping[name]) + "\n"

        if data_flag:
            value = float(line.split()[0])
            value_new = 1 + cfac_multiply[name] * ( value - 1 )
                      
            if cfac_quad_info[name]:
                value_new += cfac_multiply[name]**2 * ( quad_values[0] - 1 )
                quad_values = quad_values[1:]
                       
            line = str(value_new) + "\t0.00000\n"

        if line_num != 0 and line.find("***") > -1:
            data_flag = True

        new_cfac += [line]
        line_num += 1

    with open(new_file_path,'w+') as fnew:
        fnew.writelines(new_cfac)
        fnew.close()

def write_compound_cfac(cfacpath, name, dataset, cfac_mapping, cfac_quad_info, num_file_path, den_file_path, cfac_multiply, new_num_path, new_den_path, value_name, quad_num_path, quad_den_path):
    """Writes two new compound cfactor files, one for numerator, one for denominator.
    """
    # Write two basic C-factors, one for the denominator, one for the numerator.
    write_basic_cfac(cfacpath, name, dataset, cfac_mapping, cfac_quad_info, num_file_path, cfac_multiply, new_num_path, value_name, quad_num_path)
    write_basic_cfac(cfacpath, name, dataset, cfac_mapping, cfac_quad_info, den_file_path, cfac_multiply, new_den_path, value_name, quad_den_path)

def write_cfactor_files(write_cfactors_data, dataset_inputs, theory):
    """Writes new cfactor files according to the cfactors_data
    dictionary.
    """

    log.info("Writing scaled C-factor files to theory folder.")

    theoryid = theory["theoryid"].id
    cfacpath = l.datapath / ('theory_%s' % theoryid) / 'cfactor'

    # Collect the names of the C-factors we wish to read and write.
    cfac_mapping, cfac_multiply = _get_cfac_mappings(write_cfactors_data)
    cfac_quad_info = _get_cfac_quad_info(write_cfactors_data)

    # For each dataset in dataset inputs, try to read the default C-factor
    # from the correct theory.
    for dataset in dataset_inputs:
        for name in cfac_mapping:
            if name in dataset.cfac:
                default_file_path = cfacpath / ("CF_" + name + "_" + dataset.name + ".dat")
                compound_flag = False
                
                if not os.path.exists(default_file_path):
                    # Either the C-factor doesn't exist, or it might be a compound C-factor.
                    compound_flag = True
                    log.info("Couldn't find C-factor at " + str(default_file_path) + ". Trying to locate compound C-factors.")
                    num_file_path = cfacpath / ("CF_" + name + "_" + dataset.name + "_NUM.dat")
                    den_file_path = cfacpath / ("CF_" + name + "_" + dataset.name + "_DEN.dat")

                    if not os.path.exists(num_file_path) or not os.path.exists(den_file_path):
                        log.error("Could not find a default C-factor, or a compound default C-factor. Are you sure they exist in the given theory?")
                        raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), default_file_path)

                if cfac_quad_info[name] and not compound_flag:
                    # Quadratic corrections are switched on for this C-factor. 
                    quad_file_path = cfacpath / ("CF_" + name + "quad_" + dataset.name + ".dat")
                elif cfac_quad_info[name] and compound_flag:
                    # Compound quadratic corrections are switched on for this C-factor.
                    quad_num_path = cfacpath / ("CF_" + name + "quad_" + dataset.name + "_NUM.dat")
                    quad_den_path = cfacpath / ("CF_" + name + "quad_" + dataset.name + "_DEN.dat")
                elif not cfac_quad_info[name] and not compound_flag:
                    quad_file_path = None
                else:
                    quad_num_path = None
                    quad_den_path = None

                value_name = str(cfac_mapping[name]).replace(".","p").replace("-","m")

                if not compound_flag:
                    new_file_path = cfacpath / ("CF_" + name + value_name + "_" + dataset.name + ".dat")
                else:
                    new_num_path = cfacpath / ("CF_" + name + value_name + "_" + dataset.name + "_NUM.dat")
                    new_den_path = cfacpath / ("CF_" + name + value_name + "_" + dataset.name + "_DEN.dat")

                if not compound_flag:
                    write_basic_cfac(cfacpath, name, dataset, cfac_mapping, cfac_quad_info, default_file_path, cfac_multiply, new_file_path, value_name, quad_file_path)
                else:
                    write_compound_cfac(cfacpath, name, dataset, cfac_mapping, cfac_quad_info, num_file_path, den_file_path, cfac_multiply, new_num_path, new_den_path, value_name, quad_num_path, quad_den_path)

    return 0

def _get_cfac_mappings(write_cfactors_data):
    cfac_mapping = {}
    cfac_multiply = {}
    for entry in write_cfactors_data:
        name = entry["name"]
        value = float(entry["new_value"]) / float(entry["default_value"])
        cfac_mapping.update({ name : entry["new_value"] })
        cfac_multiply.update({ name : value })
    return cfac_mapping, cfac_multiply

def _get_cfac_quad_info(write_cfactors_data):
    cfac_quad_info = {}
    for entry in write_cfactors_data:
        name = entry["name"]
        quad_on = entry["quad_on"]
        cfac_quad_info.update({ name : quad_on })
    return cfac_quad_info

def write_runcard(write_cfactors_data, dataset_inputs, output_name, write_cfactor_files):
    """Reads a runcard line by line and returns a new runcard ready for a
    contaminated fit.
    """

    log.info("Writing contaminated runcard ready for fit.")

    # Construct a dictionary of the contaminated sets for later use.
    cfac_mapping, _ = _get_cfac_mappings(write_cfactors_data)

    # Create a mapping between old C-factor names and new C-factor names.
    old_to_new_cfac = {}
    for name in cfac_mapping:
        new_name = name + str(cfac_mapping[name]).replace(".","p").replace("-","m")
        old_to_new_cfac.update({name : new_name})

    contaminated_sets = {}
    for dataset in dataset_inputs:
        for name in cfac_mapping:
            cfac_list = []
            if name in dataset.cfac:
                cfac_list += [old_to_new_cfac[name]]
            contaminated_sets.update({ dataset.name : cfac_list })

    # Remove anything that hasn't been contaminated
    new_contaminated_sets = {}
    for set in contaminated_sets:
        if len(contaminated_sets[set]) != 0:
            new_contaminated_sets.update({ set : contaminated_sets[set] })

    contaminated_sets = new_contaminated_sets

    new_dataset_inputs = []
    for i in range(len(dataset_inputs)):
        dataset_name = dataset_inputs[i].name
        if dataset_name in contaminated_sets.keys():
            new_cfacs = []
            for cfac in dataset_inputs[i].cfac:
                if cfac in old_to_new_cfac.keys():
                    new_cfacs += [old_to_new_cfac[cfac]]
                else:
                    new_cfacs += [cfac]
            new_set = DataSetInput(
                name=dataset_inputs[i].name,
                sys=dataset_inputs[i].sys,
                cfac=new_cfacs,
                frac=dataset_inputs[i].frac,
                weight=dataset_inputs[i].weight,
                custom_group=dataset_inputs[i].custom_group,
            )
            new_dataset_inputs += [new_set]
        else:
            new_dataset_inputs += [dataset_inputs[i]]

    args = process_args()
    input_runcard_name = args.input_card

    current_directory = Path(os.getcwd())
    input_path = current_directory / input_runcard_name

    output_path = current_directory / (output_name + ".yaml")

    with open(input_path,'r+') as f:
        runcard = f.readlines()
        f.close()

    new_runcard = []

    dataset_count = 0
    for line in runcard:
        # Check if the line is a dataset line. If so, check if the dataset is
        # a contaminated one, and update the cfactors if appropriate.
        if line.find("dataset:") > -1 and dataset_count < len(dataset_inputs):
            if len(new_dataset_inputs[dataset_count].cfac) != 0:
                line = "- {dataset: " + new_dataset_inputs[dataset_count].name + ", frac: " + str(new_dataset_inputs[dataset_count].frac) + ", cfac: " + str(new_dataset_inputs[dataset_count].cfac) + ", weight: " + str(new_dataset_inputs[dataset_count].weight) + "}\n"
            else:
                line = "- {dataset: " + new_dataset_inputs[dataset_count].name + ", frac: " + str(new_dataset_inputs[dataset_count].frac) + ", weight: " + str(new_dataset_inputs[dataset_count].weight) + "}\n"
            dataset_count += 1

        # Remove the actions ready for the fit
        if not (line.find("actions_") > -1 or line.find("write_cfactor_files") > -1 or line.find("write_runcard") > -1 or line.find("launch_vpsetupfit") > -1 or line.find("launch_vprebuilddata") > -1 or line.find("write_sm_runcard") > -1):
            new_runcard += [line]

    with open(output_path,'w+') as fnew:
        fnew.writelines(new_runcard)
        fnew.close()

    return 0

def launch_vpsetupfit(output_name, write_runcard):
    """Launches vp-setupfit for a contaminated fit.
    """
    current_directory = Path(os.getcwd())
    output_path = current_directory / (output_name + ".yaml")

    os.system('vp-setupfit ' + str(output_path))

    return 0

def launch_vprebuilddata(output_name, launch_vpsetupfit):
    """Launches vp-rebuild-data for a contaminated fit.
    """
    current_directory = Path(os.getcwd())
    output_path = current_directory / output_name

    os.system('vp-rebuild-data ' + str(output_path))

    return 0

def write_sm_runcard(write_cfactors_data, output_name, dataset_inputs, launch_vprebuilddata):
    """Removes the C-factors from the runcard.
    """

    log.info("Writing SM runcard ready for fit, and replacing filter.yaml in fit folder.")

    # Construct a dictionary of the contaminated sets for later use.
    cfac_mapping, _ = _get_cfac_mappings(write_cfactors_data)

    # Create a mapping between old C-factor names and new C-factor names.
    old_to_new_cfac = {}
    for name in cfac_mapping:
        new_name = name + str(cfac_mapping[name]).replace(".","p").replace("-","m")
        old_to_new_cfac.update({name : new_name})

    contaminated_sets = {}
    for dataset in dataset_inputs:
        for name in cfac_mapping:
            cfac_list = []
            if name in dataset.cfac:
                cfac_list += [old_to_new_cfac[name]]
            contaminated_sets.update({ dataset.name : cfac_list })

    # Remove anything that hasn't been contaminated
    new_contaminated_sets = {}
    for set in contaminated_sets:
        if len(contaminated_sets[set]) != 0:
            new_contaminated_sets.update({ set : contaminated_sets[set] })

    contaminated_sets = new_contaminated_sets

    new_dataset_inputs = []
    for i in range(len(dataset_inputs)):
        dataset_name = dataset_inputs[i].name
        if dataset_name in contaminated_sets.keys():
            new_cfacs = []
            for cfac in dataset_inputs[i].cfac:
                if cfac in old_to_new_cfac.keys():
                    # This time, we want nothing in place of the SMEFT C-factors
                    new_cfacs += []
                else:
                    new_cfacs += [cfac]
            new_set = DataSetInput(
                name=dataset_inputs[i].name,
                sys=dataset_inputs[i].sys,
                cfac=new_cfacs,
                frac=dataset_inputs[i].frac,
                weight=dataset_inputs[i].weight,
                custom_group=dataset_inputs[i].custom_group,
            )
            new_dataset_inputs += [new_set]
        else:
            new_dataset_inputs += [dataset_inputs[i]]

    # The path we are about the overwrite
    current_directory = Path(os.getcwd())
    output_path = current_directory / (output_name + ".yaml")

    with open(output_path,'r+') as f:
        runcard = f.readlines()
        f.close()

    new_runcard = []

    dataset_count = 0
    for line in runcard:
        # Check if the line is a dataset line. If so, check if the dataset is
        # a contaminated one, and update the cfactors if appropriate.
        if line.find("dataset:") > -1 and dataset_count < len(dataset_inputs):
            if len(new_dataset_inputs[dataset_count].cfac) != 0:
                line = "- {dataset: " + new_dataset_inputs[dataset_count].name + ", frac: " + str(new_dataset_inputs[dataset_count].frac) + ", cfac: " + str(new_dataset_inputs[dataset_count].cfac) + ", weight: " + str(new_dataset_inputs[dataset_count].weight) + "}\n"
            else:
                line = "- {dataset: " + new_dataset_inputs[dataset_count].name + ", frac: " + str(new_dataset_inputs[dataset_count].frac) + ", weight: " + str(new_dataset_inputs[dataset_count].weight) + "}\n"
            dataset_count += 1    

        new_runcard += [line]

    # Remove existing runcard
    os.system('rm ' + str(output_path))    

    with open(output_path,'w') as fnew:
        runcard = fnew.writelines(new_runcard)
        fnew.close()

    # Finally, overwrite the filters.yaml file in the output directory with the new runcard.
    filter_path = current_directory / output_name / "filter.yml"
    os.system('cp ' + str(output_path) + ' ' + str(filter_path))

    # Overwrite the md5 file to actually allow us to upload the fit
    md5_path = current_directory / output_name / "md5"
    os.system('rm ' + str(md5_path))
    output = subprocess.check_output("md5sum " + str(filter_path), shell=True)
    output = output.decode()
    md5_string = output.split(" ")[0]
    os.system('echo ' + md5_string + ' >> ' + str(md5_path))
    os.system('truncate -s -1 ' + str(md5_path))

    return 0

def process_args():
    parser = argparse.ArgumentParser(
        description="Script to generate contaminated fit runcard."
    )
    parser.add_argument("input_card", help="Name of input card.")
    parser.add_argument("-x") # This is to help the provider out.
    args = parser.parse_args()
    return args
