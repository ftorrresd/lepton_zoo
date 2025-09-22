bin/micromamba env export -p ./venv --no-builds | sed '/^prefix:/d' > environment.yml
