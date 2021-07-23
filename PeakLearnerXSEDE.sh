#!/bin/bash
#SBATCH --job-name=PLSlurm
#SBATCH --output=/local-scratch/deltarod/runlog.txt
#SBATCH --chdir=/home/deltarod/PeakLearner/
#SBATCH --open-mode=append
#SBATCH --ntasks=1
#SBATCH --mem=4096
#SBATCH --time=1:00:00
#SBATCH --export=ALL

module load R
module load python/3.5.2
source venv/bin/activate

python3 Slurm/run.py monsoon

sbatch PeakLearnerXSEDE.sh
