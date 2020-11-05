#!/bin/bash
#SBATCH --job-name=PeakLearnerSlurm
#SBATCH --output=/home/tristan/Research/PeakLearner/runlog.txt
#SBATCH --chdir=/home/tristan/Research/PeakLearner/server/
#SBATCH --time=10:01

srun python3 run.py
