import importlib
import json
import time
from functools import wraps
from pathlib import Path

import typer
from rich.progress import track

from lepton_zoo import Year
from lepton_zoo.datasets import Dataset


def execution_time(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        elapsed_time = end_time - start_time
        formatted_time = time.strftime("%H:%M:%S", time.gmtime(elapsed_time))
        print(f"Execution time of {func.__name__}: {formatted_time}")
        return result

    return wrapper


# Create the main Typer application instance
classification_app = typer.Typer(
    help="Run event selection and classification.",
)
plotter_app = typer.Typer(
    help="Plot distributions.",
)
app = typer.Typer(
    name="lepzoo",
    help="Lepton Zoo analysis.",
    pretty_exceptions_enable=False,
)
app.add_typer(classification_app, name="classification")
app.add_typer(plotter_app, name="plotter")


@app.command()
@execution_time
def build(
    inputs: Path = Path("datasets.py"),
):
    """
    Build analysis config.
    """

    datasets = importlib.import_module(str(inputs).replace(".py", ""))

    from datasets import datasets

    print([print(d.short_str()) for d in datasets])

    with Path("parsed_datasets.json").open("w", encoding="utf-8") as f:
        json.dump(
            [u.model_dump(mode="json") for u in datasets],
            f,
            ensure_ascii=False,
            indent=2,
        )


@app.command()
@execution_time
def list_processes(
    parsed_datasets_file: Path = Path("parsed_datasets.json"),
):
    """
    List parsed datasets.
    """

    with parsed_datasets_file.open("r", encoding="utf-8") as f:
        parsed_datasets = json.load(f)
    parsed_datasets: list[Dataset] = [
        Dataset.model_validate(obj) for obj in parsed_datasets
    ]

    for d in parsed_datasets:
        print(d.short_str())


@classification_app.command()
@execution_time
def run_serial(
    process_name: str,
    year: Year,
    max_files: int = -1,
    file_index: int | None = None,
    parsed_datasets_file: Path = Path("parsed_datasets.json"),
):
    """
    Run selection and classification.
    """
    from lepton_zoo import run_classification

    with parsed_datasets_file.open("r", encoding="utf-8") as f:
        parsed_datasets: list[Dataset] = json.load(f)
    parsed_datasets: list[Dataset] = [
        Dataset.model_validate(obj) for obj in parsed_datasets
    ]

    for dataset in parsed_datasets:
        if dataset.process_name == process_name and dataset.year == year:
            assert dataset.lfns is not None
            match file_index:
                case None:
                    for i, _ in enumerate(
                        track(
                            dataset.lfns,
                            description=f"Processing {dataset.short_str()} ...",
                            total=len(dataset.lfns),
                        )
                    ):
                        if max_files <= 0 or (max_files > 0 and i + 1 <= max_files):
                            run_classification(i, dataset)
                case int():
                    print(
                        f"Processing {dataset.lfns[file_index]} of {dataset.short_str()} ..."
                    )
                    run_classification(file_index, dataset)


@plotter_app.command()
@execution_time
def plot(
    distribution_name: str,
    force: bool = typer.Option(False, help="Brute force plot."),
):
    """
    Run plotter.
    """
    pass


if __name__ == "__main__":
    app()
