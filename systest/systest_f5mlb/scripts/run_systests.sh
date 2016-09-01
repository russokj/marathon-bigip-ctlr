#!/usr/bin/env bash
set -ex

if [ "$1" == "" ]; then
    echo "ERROR: no systest_pkg value provided!"
    exit 1
else
    systest_pkg="$1"
fi

if [ "$2" == "" ]; then
    echo "ERROR: no session value provided!"
    exit 1
else
    session="$2"
fi

if [ "$3" == "" ]; then
    echo "ERROR: no include_tags value provided!"
    exit 1
else
    # - include tags is a (potentially space-delimited) value like "func",
    #   "scale" or "func perf"
    include_tags="$3"
fi

# - create the local results directory
results_dir="~/test_results"
if [[ ! -e "$results_dir" ]]; then
    mkdir -p "$results_dir"
fi

# - enter the systest virtualenv
source systest/bin/activate

# - run the system tests
systestdir=$(python -c "import $systest_pkg; print $systest_pkg.__path__[0]")
cd $systestdir

py.test \
    -svvra \
    --symbols ~/testenv_symbols/testenv_symbols.json \
    --include $include_tags \
    --exclude incomplete no_regression \
    --autolog-outputdir $results_dir \
    --autolog-session $session \
    -- testsuites