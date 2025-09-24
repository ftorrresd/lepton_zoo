from __future__ import annotations

import subprocess
from pathlib import Path
from threading import local
from typing import Any

import awkward as ak
import uproot
import vector
from pydantic import BaseModel

from .redirectors import Redirectors

vector.register_awkward()  # <- important


def load_file(file_lfn: str, enable_cache: bool) -> uproot.TTree:
    if enable_cache:
        local_path = Path(f"nanoaod_files_cache/{file_lfn.replace('/', '_')}")
        if local_path.exists():
            print("File already cached...")
            nanoaod_file = uproot.open(f"{str(local_path)}:Events")
            return nanoaod_file  # type: ignore
        else:
            print(f"Caching {file_lfn}...")
            for redirector in Redirectors:
                try:
                    subprocess.run(
                        f"xrdcp {redirector}{file_lfn} {str(local_path)}",
                        check=True,
                        shell=True,
                    )
                    nanoaod_file = uproot.open(f"{str(local_path)}:Events")
                    return nanoaod_file  # type: ignore
                except:
                    continue
            raise RuntimeError("File is not accessible by any redirector")

    for redirector in Redirectors:
        try:
            nanoaod_file = uproot.open(f"{redirector}{file_lfn}:Events")
            return nanoaod_file  # type: ignore
        except:
            continue

    raise RuntimeError("File is not accessible by any redirector")


class Events(BaseModel):
    input_file: str
    muons: Any
    electrons: Any
    jets: Any
    met: Any

    @staticmethod
    def build_events(input_file: str, enable_cache: bool) -> "Events":
        # muons
        MUON_PREFIX = "Muon_"
        evts = load_file(input_file, enable_cache)

        _muons = evts.arrays(
            [
                "Muon_pt",
                "Muon_eta",
                "Muon_phi",
                "Muon_mass",
                "Muon_charge",
            ]
        )

        if "Muon_mass" not in ak.fields(_muons):
            muon_mass = 0.105_658_374_5
            _muons = ak.with_field(
                _muons, ak.ones_like(_muons["Muon_pt"]) * muon_mass, "Muon_mass"
            )

        muons = ak.zip(
            {f[len(MUON_PREFIX) :]: _muons[f] for f in ak.fields(_muons)},
            with_name="Momentum4D",
        )
        print(ak.count(muons, axis=-1))

        # electrons
        ELECTRON_PREFIX = "Electron_"

        _electrons = evts.arrays(
            [
                "Electron_pt",
                "Electron_eta",
                "Electron_phi",
                "Electron_mass",
                "Electron_charge",
            ]
        )

        if "Electron_mass" not in ak.fields(_electrons):
            electron_mass = 0.000511
            _electrons = ak.with_field(
                _electrons,
                ak.ones_like(_electrons["Electron_pt"]) * electron_mass,
                "Electron_mass",
            )

        electrons = ak.zip(
            {f[len(ELECTRON_PREFIX) :]: _electrons[f] for f in ak.fields(_electrons)},
            with_name="Momentum4D",
        )
        print(ak.count(electrons, axis=-1))

        # jets
        JET_PREFIX = "Jet_"

        _jets = evts.arrays(
            [
                "Jet_pt",
                "Jet_eta",
                "Jet_phi",
                "Jet_mass",
            ]
        )

        jets = ak.zip(
            {f[len(JET_PREFIX) :]: _jets[f] for f in ak.fields(_jets)},
            with_name="Momentum4D",
        )
        print(ak.count(jets, axis=-1))
        print(len(ak.count(jets, axis=-1)))

        # met
        MET_PREFIX = "PuppiMET_"

        _met = evts.arrays(
            [
                "PuppiMET_pt",
                "PuppiMET_phi",
            ]
        )

        if "PuppiMET_mass" not in ak.fields(_met):
            _met = ak.with_field(
                _met,
                ak.zeros_like(_met["PuppiMET_pt"]),
                "PuppiMET_mass",
            )

        if "PuppiMET_eta" not in ak.fields(_met):
            _met = ak.with_field(
                _met,
                ak.zeros_like(_met["PuppiMET_pt"]),
                "PuppiMET_eta",
            )

        met = ak.zip(
            {f[len(MET_PREFIX) :]: _met[f] for f in ak.fields(_met)},
            with_name="Momentum4D",
        )
        print(ak.count(met, axis=-1))

        return Events(
            input_file=input_file,
            muons=muons,
            electrons=electrons,
            jets=jets,
            met=met,
        )
