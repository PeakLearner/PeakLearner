#!/bin/bash
#SBATCH --job-name=PLSlurm
#SBATCH --output=/home/tristan/Research/PeakLearner/runlog.txt
#SBATCH --chdir=/home/tristan/Research/PeakLearner/
#SBATCH --open-mode=append
#SBATCH --time=2:00

SCHEDULE='* * * * *'

srun python3 Slurm/run.py

sbatch --quiet --begin=$(next-cron-time "$SCHEDULE") /home/tristan/Research/PeakLearner/PeakLearnerSlurm.sh
