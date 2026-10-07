#!/bin/bash
# Usage: ./submitReconstruct.sh <time>
#
# Reconstructs one time step as two independent single-core batch jobs, so the
# particle cloud is done while the (much longer) field reconstruction runs.
# Reconstructing a collated case is slow, and long jobs are not allowed on the
# login nodes of some HPC systems.
#
# Uses reconstruct_local.slm, your adapted copy of reconstruct_template.slm.

if [ -z "$1" ]; then
    echo "Usage: $0 <time>"
    exit 1
fi

if [ ! -f reconstruct_local.slm ]; then
    echo "reconstruct_local.slm not found: copy reconstruct_template.slm to it and adapt it."
    exit 1
fi

TIME=$1

sbatch --export=ALL,FLAG=-no-lagrangian,TIME="$TIME" --job-name=reconstruct-fields reconstruct_local.slm
sbatch --export=ALL,FLAG=-no-fields,TIME="$TIME"     --job-name=reconstruct-cloud  reconstruct_local.slm
