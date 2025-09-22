from pydantic import BaseModel
from enum import StrEnum, auto
from .eras import Year, LHCRun, NanoADODVersion


class ProcessGroup(StrEnum):
    DRELLYAN = "Drell-Yan"
    QCD = "QCD"
    TTBAR = "ttbar"
    WJETS = "WJets"
    ZZ = "ZZ"
    WW = "WW"
    ZGAMMA = "ZGamma"
    WGAMMA = "WGamma"


class DatasetType(StrEnum):
    DATA = auto()
    BKG = auto()
    SIGNAL = auto()


class Dataset(BaseModel):
    das_names: str | list[str]
    process_name: str
    process_group: ProcessGroup
    year: Year
    nanoadod_version: NanoADODVersion
    lhc_run: LHCRun
    dataset_type: DatasetType
    x_sec: float
    filter_eff: float
    k_factor: float
    lfn: str | None

    def __str__(self) -> str:
        return f"[{self.process_name}]_[{self.process_group}]_[{self.year}]_[{self.lhc_run}]_[{self.dataset_type}]"

    def is_complete(self):
        return self.lfn is not None
