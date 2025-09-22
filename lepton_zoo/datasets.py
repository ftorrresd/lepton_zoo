from enum import StrEnum, auto
from typing import Self

from pydantic import BaseModel, model_validator

from .eras import LHCRun, NanoADODVersion, Year


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
    xsec: float
    filter_eff: float
    k_factor: float
    lfns: list[str] | None = None
    generator_filter: str | None = None

    def short_str(self) -> str:
        return f"[{self.process_name}]_[{self.process_group}]_[{self.year}]_[{self.lhc_run}]_[{self.dataset_type}]"

    @model_validator(mode="after")
    def set_xsec(self) -> Self:
        if self.dataset_type == DatasetType.DATA:
            self.xsec = 1.0
            self.k_factor = 1.0
            self.filter_eff = 1.0

        return self

    @model_validator(mode="after")
    def build_das_names(self) -> Self:
        if isinstance(self.das_names, str):
            self.das_names = [self.das_names]

        return self

    @model_validator(mode="after")
    def build_lfn_list(self) -> Self:
        if self.lfns is None:
            self.lfns = ["foo", "bar"]

        return self
