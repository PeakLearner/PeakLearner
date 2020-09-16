#!/bin/bash
#SBATCH --job-name=lazy                     # the name of your job
#SBATCH --output=/scratch/tem83/lazy.txt    # this is the file your output and errors go to
#SBATCH --chdir=/scratch/tem83            # your work directory
#SBATCH --time=1:10                	    # (max time) 30 minutes, hmm ya that sounds good 
#SBATCH --mem=600                          # (total mem) 4GB of memory hmm, sounds good to me
#SBATCH -c4                                 # 4 cpus, sounds good to me

module load workshop

# use 500MB of memory 
#srun stress -m 1 --vm-bytes 500M --timeout 65s

# use 500MB of memory and 3 cpu threads
srun stress -c 3 -m 1 --vm-bytes 500M --timeout 65s

# the secret command
srun exercise4
