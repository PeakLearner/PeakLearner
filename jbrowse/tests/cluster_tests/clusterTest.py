import subprocess

        #This next block is our simulation of the cluster and using Dr. Hockings R code
        ############################################

        # Define command and arguments
        command = 'Rscript'
        path2script = '../PeakSegDisk-master/R/PeakSegFPOP_dir.R'

        # the function we want to run has 2 arguments
        #a path to the coverage data we are observing
        #penalty > 0
        args = ['../PeakLearner-1.1/jbrowse/tests/data/all_labels.bigBed', '1']

        # Build subprocess command
        cmd = [command, path2script] + args

        # check_output will run the command and store to result
        newModel = subprocess.check_output(cmd, universal_newlines=True)

        print('The new model we got:', newModel)
        ############################################
        #For now, in this section we will always send back a specific model which we will write to here
        #this should make jbrowse redraw when it gets a response to view the model
