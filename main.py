import importlib
import json
import subprocess as sp
import time
from functools import wraps
from pathlib import Path

import typer
from rich.progress import track

from lepton_zoo import Year
from lepton_zoo.datasets import Dataset
import os
import sys
import subprocess as sp
from typing import Sequence, Union, Literal

StreamMode = Literal["auto", "lines", "chars"]


def run_stream_shell(
    cmd: Union[str, Sequence[str]],
    *,
    cwd: str | None = None,
    env: dict | None = None,
    shell_exe: str | None = "/bin/bash",  # POSIX shell to run under
    merge_stderr: bool = True,  # show progress bars printed to stderr
    stream_mode: StreamMode = "auto",  # "auto" picks "chars" if merge_stderr else "lines"
    line_buffer_hint: bool = True,  # add stdbuf (POSIX) to coax timely flushing
) -> int:
    """
    Run a command *via a shell* and stream output as it appears.

    - If stream_mode="chars", reads raw bytes and writes them through (best for progress bars).
    - If stream_mode="lines", reads text lines (nice for typical logs).
    - "auto": uses "chars" when merge_stderr=True (common for progress bars), else "lines".
    """
    # Normalize to a single command string for the shell
    if not isinstance(cmd, str):
        import shlex

        cmd = " ".join(shlex.quote(str(c)) for c in cmd)

    # Heuristic: if user merges stderr (likely progress bars), prefer char streaming
    if stream_mode == "auto":
        stream_mode = "chars" if merge_stderr else "lines"

    # Reduce buffering of the child (POSIX)
    if line_buffer_hint and os.name == "posix":
        # For progress bars, unbuffered (-o0 -e0) makes \r updates snappy
        if stream_mode == "chars":
            cmd = f"stdbuf -o0 -e0 {cmd}"
        else:
            cmd = f"stdbuf -oL -eL {cmd}"

    # Build Popen kwargs
    popen_kwargs = dict(
        cwd=cwd,
        env=env,
        shell=True,
    )
    if os.name == "posix" and shell_exe:
        popen_kwargs["executable"] = shell_exe

    # Choose text/binary mode based on streaming style
    if stream_mode == "chars":
        popen_kwargs.update(
            stdout=sp.PIPE,
            stderr=sp.STDOUT if merge_stderr else sp.PIPE,
            text=False,
            bufsize=0,
        )  # binary, unbuffered
    else:  # "lines"
        popen_kwargs.update(
            stdout=sp.PIPE,
            stderr=sp.STDOUT if merge_stderr else sp.PIPE,
            text=True,
            bufsize=1,
        )  # text, line-buffered

    # Launch
    proc = sp.Popen(cmd, **popen_kwargs)

    try:
        if merge_stderr:
            # Single stream path
            assert proc.stdout is not None
            if stream_mode == "chars":
                out = proc.stdout
                w = sys.stdout.buffer
                for chunk in iter(lambda: out.read(1024), b""):
                    w.write(chunk)
                    w.flush()
            else:
                for line in proc.stdout:
                    print(line, end="")
        else:
            # Dual-stream path
            import threading, queue

            q: "queue.Queue[tuple[str, bytes|str|None]]" = queue.Queue()

            def pump_bytes(stream, tag):
                for chunk in iter(lambda: stream.read(1024), b""):
                    q.put((tag, chunk))
                q.put((tag, None))

            def pump_lines(stream, tag):
                for line in iter(stream.readline, ""):
                    q.put((tag, line))
                q.put((tag, None))

            if stream_mode == "chars":
                t_out = threading.Thread(
                    target=pump_bytes, args=(proc.stdout, "out"), daemon=True
                )
                t_err = threading.Thread(
                    target=pump_bytes, args=(proc.stderr, "err"), daemon=True
                )
            else:
                t_out = threading.Thread(
                    target=pump_lines, args=(proc.stdout, "out"), daemon=True
                )
                t_err = threading.Thread(
                    target=pump_lines, args=(proc.stderr, "err"), daemon=True
                )

            t_out.start()
            t_err.start()

            done = {"out": False, "err": False}
            while not all(done.values()):
                tag, payload = q.get()
                if payload is None:
                    done[tag] = True
                    continue
                if stream_mode == "chars":
                    buf = sys.stdout.buffer
                    if tag == "err":
                        # minimal prefixing without breaking \r animations too much
                        buf.write(b"[stderr] ")
                    buf.write(payload)
                    buf.flush()
                else:
                    if tag == "err":
                        print(f"[stderr] {payload}", end="")
                    else:
                        print(payload, end="")

            t_out.join()
            t_err.join()
    except KeyboardInterrupt:
        # Forward Ctrl-C to the whole group on POSIX
        try:
            if os.name == "posix":
                import signal

                os.killpg(proc.pid, signal.SIGINT)
        except Exception:
            pass
        finally:
            proc.wait()
    finally:
        return proc.wait()


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

    with Path("parsed_datasets.json").open("w", encoding="utf-8") as f:
        json.dump(
            [u.model_dump(mode="json") for u in datasets],
            f,
            ensure_ascii=False,
            indent=2,
        )

    print(f"Successfully Parsed and build datasets ...")


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
                            f"lepzoo classification run-serial {dataset.process_name} {dataset.year} --file-index {i} --silence-mode"
                        )

    Path("cmds.txt").write_text("\n".join(cmds) + "\n", encoding="utf-8")

    cmd = "parallel --results parallel_outputs --bar --retries 3 --halt soon,fail=1 --joblog joblog.tsv < cmds.txt"

    os.system("rm -rf parallel_outputs")
    os.system("mkdir -p parallel_outputs")

    rc = run_stream_shell(
        cmd,
        merge_stderr=True,  # show the --bar progress
        stream_mode="auto",  # auto picks "chars" when merge_stderr=True
        shell_exe="/bin/bash",  # ensure bash features if you use them
    )
    print(f"\n[exit code: {rc}]")


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
