import importlib
import json
import shlex
import subprocess as sp
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
    silence_mode: bool = False,
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
                            run_classification(i, dataset, silence_mode)
                case int():
                    if not silence_mode:
                        print(
                            f"Processing {dataset.lfns[file_index]} of {dataset.short_str()} ..."
                        )
                    run_classification(file_index, dataset, silence_mode)


@classification_app.command()
@execution_time
def run_parallel(
    process_name: str | None = None,
    year: Year | None = None,
    max_files: int = -1,
    parsed_datasets_file: Path = Path("parsed_datasets.json"),
):
    """
    Run selection and classification.
    """

    with parsed_datasets_file.open("r", encoding="utf-8") as f:
        parsed_datasets: list[Dataset] = json.load(f)
    parsed_datasets: list[Dataset] = [
        Dataset.model_validate(obj) for obj in parsed_datasets
    ]

    cmds: list[str] = []
    for dataset in parsed_datasets:
        if dataset.process_name == process_name or process_name is None:
            if dataset.year == year or year is None:
                assert dataset.lfns is not None
                for i, _ in enumerate(dataset.lfns):
                    if max_files <= 0 or (max_files > 0 and i + 1 <= max_files):
                        cmds.append(
                            f"lepzoo classification run-serial {dataset.process_name} {dataset.year} --file-index {i} --silence_mode"
                        )

    Path("cmds.txt").write_text("\n".join(cmds) + "\n", encoding="utf-8")

    def run_stream(cmd, *, cwd=None, env=None):
        # Force line-buffered text
        proc = sp.Popen(
            cmd,
            cwd=cwd,
            env=env,
            stdout=sp.PIPE,
            stderr=sp.STDOUT,  # merge stderr into stdout (optional)
            text=True,
            bufsize=1,  # line buffering
        )
        try:
            # Iterate as lines arrive
            assert proc.stdout is not None
            for line in proc.stdout:
                print(line, end="")
        finally:
            # Ensure pipes closed; wait for exit code
            ret = proc.wait()
        return ret

    print(f"Will run {len(cmds)} in parallel ...")

    code = run_stream(
        shlex.split(
            "parallel -j 4 --bar --retries 3 --halt soon,fail=1 --joblog joblog.tsv < cmds.txt"
        )
    )
    print(f"\nExit code: {code}")


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
