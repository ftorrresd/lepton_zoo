from .datasets import Dataset
from .events import Events


def run_classification(
    file_to_process: str | int, dataset: Dataset, silence_mode: bool, enable_cache: bool
) -> None:
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

    events = Events.build_events(file_to_process, enable_cache)
    if not silence_mode:
        print(events)

    return
