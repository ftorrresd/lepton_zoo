from lepton_zoo import Dataset, DatasetType, LHCRun, NanoADODVersion, ProcessGroup, Year

datasets: list[Dataset] = []
datasets.append(
    Dataset(
        process_name="Foo",
        das_names="Foo",
        process_group=ProcessGroup.DRELLYAN,
        year=Year.Run2018,
        nanoadod_version=NanoADODVersion.V9,
        lhc_run=LHCRun.Run2,
        dataset_type=DatasetType.BKG,
        xsec=1.0,
        filter_eff=1.0,
        k_factor=1.0,
    )
)
