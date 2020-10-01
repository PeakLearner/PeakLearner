#!/bin/bash
#SBATCH --job-name=PeakLearnerUpdate                     # the name of your job
#SBATCH --output=/scratch/tem83/result.txt    # this is the file your output and errors go to
#SBATCH --chdir=/scratch/tem83            # your work directory
#SBATCH --time=1:10                	    # (max time) 30 minutes, hmm ya that sounds good
#SBATCH --mem=600                          # (total mem) 4GB of memory hmm, sounds good to me
#SBATCH -c4                                 # 4 cpus, sounds good to me


srun python3 server/generateProblems.py
