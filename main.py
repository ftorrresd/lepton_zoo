from lepton_zoo import foo, Year
import typer
from pathlib import Path
from functools import wraps
import time


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
    inputs: Path = Path("inputs.txt"),
):
    """
    Build analysis config.
    """
    print(inputs)


@classification_app.command(name="classification")
@execution_time
def run(
    process_name: str,
    year: Year,
    max_files: int | None = None,
    config_file: Path = Path("analysis_config.json"),
):
    print(foo, config_file, process_name, year, max_files)


@plotter_app.command(name="plotter")
@execution_time
def plot(
    distribution_name: str,
    force: bool = typer.Option(False, help="Brute force plot."),
):
    pass


if __name__ == "__main__":
    app()
