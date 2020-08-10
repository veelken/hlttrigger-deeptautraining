#!/usr/bin/env python

import getpass
import os
import subprocess
import time

from HLTrigger.DeepTauTraining.run_command import *

version_rawNtuples = "2020Aug05"
version_training = "training_v2"

outputDir_scratch = os.path.join("/home", getpass.getuser(), "temp/Phase2HLT_DeepTauTraining", version_rawNtuples, version_training)
run_command('mkdir -p %s' % outputDir_scratch)

outputDir_root_to_hdf = os.path.join("/hdfs/local", getpass.getuser(), "Phase2HLT/DeepTauTraining", version_rawNtuples, version_training, "training-hdf5")
run_command('mkdir -p %s' % outputDir_root_to_hdf)
run_command('mkdir -p %s/even-events-classified-by-DeepTau_even' % outputDir_root_to_hdf)
run_command('mkdir -p %s/even-events-classified-by-DeepTau_odd' % outputDir_root_to_hdf)
run_command('mkdir -p %s/even-events-classified-by-chargedIsoPtSum' % outputDir_root_to_hdf)
run_command('mkdir -p %s/odd-events-classified-by-DeepTau_even' % outputDir_root_to_hdf)
run_command('mkdir -p %s/odd-events-classified-by-DeepTau_odd' % outputDir_root_to_hdf)
run_command('mkdir -p %s/odd-events-classified-by-chargedIsoPtSum' % outputDir_root_to_hdf)

outputDir_plots = os.path.join("/home", getpass.getuser(), "Phase2HLT/DeepTauTraining", version_rawNtuples, version_training, "plots")
run_command('mkdir -p %s' % outputDir_plots)

# CV: clean scratch directory
run_command('rm -rf %s/*' % outputDir_scratch)

#----------------------------------------------------------------------------------------------------
# CV: run actual DeepTau training
print("Compiling _fill_grid_setup.py script...")
##run_command('source $CMSSW_BASE/src/HLTrigger/DeepTauTraining/test/compile_fill_grid_setup.sh')
print(" Done.")

models = {}
for part in [ "even", "odd" ]:
    print("Running DeepTau training for '%s' sample..." % part)
    models[part] = "DeepTauPhase2HLTv2%s" % part
    command = 'source $CMSSW_BASE/src/HLTrigger/DeepTauTraining/test/runDeepTau_training.sh %s %s' % \
      (os.path.join(outputDir_root_to_hdf, "%s-events" % part, outputFiles_root_to_hdf[part]), models[part])
    ##run_command(command)
    print(" Done.")
#----------------------------------------------------------------------------------------------------

#----------------------------------------------------------------------------------------------------
# CV: Convert DNN model to graph (.pb) format
for part in [ "even", "odd" ]:
    command = 'python $CMSSW_BASE/src/TauMLTools/Training/python/deploy_model.py --input $CMSSW_BASE/src/TauMLTools/Training/python/2017v2/%s_step1_final.hdf5' % \
      (models[part])
    ##run_command(command)
    ##run_command('mv %s_step1_final.pb $CMSSW_BASE/src/TauMLTools/Training/python/2017v2/' % models[part])
#----------------------------------------------------------------------------------------------------

#----------------------------------------------------------------------------------------------------
# CV: Classify tau candidates in events with even event numbers 
#     using DeepTau model trained on events with even event numbers and vice versa
outputDirs_root_to_hdf_classified = {}
for part_sample in [ "even", "odd" ]:
    for part_model in [ "even", "odd" ]:
        ##run_command('mkdir -p %s/testing-classified' % outputDir_scratch)
        command = 'python $CMSSW_BASE/src/TauMLTools/Training/python/apply_training.py --input %s --output %s --model $CMSSW_BASE/src/TauMLTools/Training/python/2017v2/%s_step1_final.pb --chunk-size 1000 --batch-size 100 --max-queue-size 20' % \
          (os.path.join(outputDir_root_to_hdf, "%s-events" % part_sample), os.path.join(outputDir_scratch, "testing-classified"), models[part])
        ##run_command(command)
        key = '%s-events-classified-by-DeepTau_%s' % (part_sample, part_model)
        outputDirs_root_to_hdf_classified[key] = os.path.join(outputDir_root_to_hdf, "%s-events-classified-by-DeepTau_%s" % (part_sample, part_model))
        ##move_all_files_to_hdfs(os.path.join(outputDir_scratch, "testing-classified"), outputDirs_root_to_hdf_classified[key])
        ##run_command('rm -rf %s/testing-classified' % outputDir_scratch)

    # CV: Classify events by cutting on charged isolation pT-sum of the tau candidates for comparison
    run_command('mkdir -p %s/testing-classified' % outputDir_scratch)
    command = 'python $CMSSW_BASE/src/TauMLTools/Training/python/apply_chargedIsoPtSum.py --input %s --output %s --chunk-size 1000 --batch-size 100 --max-queue-size 20' % \
      (os.path.join(outputDir_root_to_hdf, "%s-events" % part_sample), os.path.join(outputDir_scratch, "testing-classified"))
    run_command(command)
    key = '%s-events-classified-by-chargedIsoPtSum' % part_sample
    outputDirs_root_to_hdf_classified[key] = os.path.join(outputDir_root_to_hdf, "%s-events-classified-by-chargedIsoPtSum" % part_sample)
    move_all_files_to_hdfs(os.path.join(outputDir_scratch, "testing-classified"), outputDirs_root_to_hdf_classified[key])
    run_command('rm -rf %s/testing-classified' % outputDir_scratch)
#----------------------------------------------------------------------------------------------------

#----------------------------------------------------------------------------------------------------
# CV: Make DeepTau performance plots
#
#    1) Overtraining
for part_model in [ "even", "odd" ]:
    part_sample_train = part_model
    part_sample_test = None
    if part_model == "even":
        part_sample_test = "odd"
    elif part_model == "odd":
        part_sample_test = "even"
    else:
        raise ValueError("Invalid parameter 'part_model' = '%s' !!" % part_model)
    key_train = '%s-events-classified-by-DeepTau_%s' % (part_sample_train, part_model)
    key_test = '%s-events-classified-by-DeepTau_%s' % (part_sample_test, part_model)
    command = 'python $CMSSW_BASE/src/TauMLTools/Training/python/evaluate_performance.py --input-taus %s --input-other %s --other-type jet --deep-results %s --deep-results-label "Train" --prev-deep-results %s --prev-deep-results-label "Test" --output %s/rocCurve_DeepTau_%s_test_vs_train.pdf' % \
      (os.path.join(outputDir_root_to_hdf, "%s-events" % part_sample, outputFiles_root_to_hdf[part_sample]), 
       os.path.join(outputDir_root_to_hdf, "%s-events" % part_sample, outputFiles_root_to_hdf[part_sample]),
       os.path.join(outputDirs_root_to_hdf_classified[key_train], outputFiles_root_to_hdf[part_sample]),
       os.path.join(outputDirs_root_to_hdf_classified[key_test], outputFiles_root_to_hdf[part_sample]),
       outputDir_plots,
       part_model)
    ##run_command(command)
#
#    2) Performance of DeepTau compared to charged isolation pT-sum
    key_DeepTau = '%s-events-classified-by-DeepTau_%s' % (part_sample_test, part_model)
    key_chargedIsoPtSum = '%s-events-classified-by-chargedIsoPtSum' % part_sample_test
    command = 'python $CMSSW_BASE/src/TauMLTools/Training/python/evaluate_performance.py --input-taus %s --input-other %s --other-type jet --deep-results %s --deep-results-label "DeepTau" --prev-deep-results %s --prev-deep-results-label "chargedIsoPtSum" --output %s/rocCurve_DeepTau_%s_vs_chargedIsoPtSum.pdf' % \
      (os.path.join(outputDir_root_to_hdf, "%s-events" % part_sample, outputFiles_root_to_hdf[part_sample]), 
       os.path.join(outputDir_root_to_hdf, "%s-events" % part_sample, outputFiles_root_to_hdf[part_sample]),
       os.path.join(outputDirs_root_to_hdf_classified[key_DeepTau], outputFiles_root_to_hdf[part_sample]),
       os.path.join(outputDirs_root_to_hdf_classified[key_chargedIsoPtSum], outputFiles_root_to_hdf[part_sample]),
       outputDir_plots,
       part_model)
    ##run_command(command)
#----------------------------------------------------------------------------------------------------