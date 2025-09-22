from enum import StrEnum, auto


class NanoADODVersion(StrEnum):
    V9 = auto()
    V10 = auto()
    V11 = auto()
    V12 = auto()
    V13 = auto()
    V14 = auto()
    V15 = auto()


class LHCRun(StrEnum):
    Run2 = "Run2"
    Run3 = "Run3"


class Year(StrEnum):
    RunSummer24 = auto()
    RunSummer23BPix = auto()
    RunSummer23 = auto()
    RunSummer22EE = auto()
    RunSummer22 = auto()
    Run2018 = auto()
    Run2017 = auto()
    Run2016preVFP = auto()
    Run2016postVFP = auto()
