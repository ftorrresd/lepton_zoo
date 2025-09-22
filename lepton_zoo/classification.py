from enum import StrEnum

import uproot

from lepton_zoo.datasets import Dataset


class Redirectors(StrEnum):
    FNAL = "root://cmsxrootd.fnal.gov//"
    INFN = "root://xrootd-cms.infn.it//"
    CERN = "root://cms-xrd-global.cern.ch//"
    RWTH = "root://grid-dcache.physik.rwth-aachen.de//"


def load_file(file_lfn: str):
    for redirector in Redirectors:
        try:
            nanoaod_file = uproot.open(f"{redirector}{file_lfn}")
            return nanoaod_file
        except:
            pass

    raise RuntimeError("File is not accessible for any redirector")


def run_classification(file_to_process: str | int, dataset: Dataset) -> None:
    """
    Will classify one file
    """

    match file_to_process:
        case str():
            pass
        case int():
            assert dataset.lfns is not None
            file_to_process = dataset.lfns[file_to_process]
        case _:
            ValueError("Invalid type for file_to_process")

    nanoaod_file = load_file(file_to_process)
    print(nanoaod_file)
    return
