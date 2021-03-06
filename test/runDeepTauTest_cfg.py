
import FWCore.ParameterSet.Config as cms

process = cms.Process("runDeepTauTest")

process.load('Configuration.StandardSequences.Services_cff')
process.load('SimGeneral.HepPDTESSource.pythiapdt_cfi')
process.load('FWCore.MessageService.MessageLogger_cfi')
process.load('Configuration.Geometry.GeometryExtended2026D49Reco_cff')
process.load('Configuration.StandardSequences.MagneticField_cff')
process.load('Configuration.StandardSequences.Reconstruction_cff')
process.load('Configuration.StandardSequences.FrontierConditions_GlobalTag_cff')

process.maxEvents = cms.untracked.PSet(
    input = cms.untracked.int32(-1)
)

process.source = cms.Source("PoolSource",
    fileNames = cms.untracked.vstring(
        'file:/home/veelken/Phase2HLT/CMSSW_11_1_0/src/HLTrigger/Phase2HLTPFTaus/test/step3_RAW2DIGI_RECO.root'
    ),
    ##eventsToProcess = cms.untracked.VEventRange(
    ##    '1:128:18039'
    ##) 
)

##inputFilePath = '/hdfs/cms/store/user/rdewanje/VBFHToTauTau_M125_14TeV_powheg_pythia8_correctedGridpack_tuneCP5/HLTConfig_VBFHToTauTau_M125_14TeV_powheg_pythia8_correctedGridpack_tuneCP5_wOfflineVtx_wDeepTau3/'
inputFilePath = None
inputFileNames = [ 'file:/hdfs/cms/store/user/rdewanje/VBFHToTauTau_M125_14TeV_powheg_pythia8_correctedGridpack_tuneCP5/HLTConfig_VBFHToTauTau_M125_14TeV_powheg_pythia8_correctedGridpack_tuneCP5_wOfflineVtx_wDeepTau4/200826_185528/0000/step3_RAW2DIGI_RECO_1.root' ]
processName = "qqH_htt"
hlt_srcVertices = 'offlinePrimaryVertices'
hlt_algorithm = "hps"
hlt_isolation_maxDeltaZOption = "primaryVertex"
hlt_isolation_minTrackHits = 8
outputFileName = "deepTauTest_%s.root" % processName

#--------------------------------------------------------------------------------
# set input files
if inputFilePath:
    from HLTrigger.TallinnHLTPFTauAnalyzer.tools.jobTools import getInputFileNames
    print("Searching for input files in path = '%s'" % inputFilePath)
    inputFileNames = getInputFileNames(inputFilePath)
    print("Found %i input files." % len(inputFileNames))
    process.source.fileNames = cms.untracked.vstring(inputFileNames)
else:
    print("Processing %i input files: %s" % (len(inputFileNames), inputFileNames))
    process.source.fileNames = cms.untracked.vstring(inputFileNames)
#--------------------------------------------------------------------------------

from Configuration.AlCa.GlobalTag import GlobalTag
process.GlobalTag = GlobalTag(process.GlobalTag, 'auto:phase2_realistic', '')

process.analysisSequence = cms.Sequence()

process.load("PhysicsTools.HepMCCandAlgos.genParticles_cfi")
process.analysisSequence += process.genParticles

process.load("PhysicsTools.JetMCAlgos.TauGenJets_cfi")
process.tauGenJets.GenParticles = cms.InputTag('genParticles')
process.analysisSequence += process.tauGenJets

process.load("PhysicsTools.JetMCAlgos.TauGenJetsDecayModeSelectorAllHadrons_cfi")
process.analysisSequence += process.tauGenJetsSelectorAllHadrons

process.selectedGenHadTaus = cms.EDFilter("GenJetSelector",
  src = cms.InputTag('tauGenJetsSelectorAllHadrons'),
  cut = cms.string('pt > 20. & abs(eta) < 2.4'),
  filter = cms.bool(False)
)
process.analysisSequence += process.selectedGenHadTaus

hlt_pfTauLabel = None
if hlt_algorithm == "shrinking-cone":
  hlt_pfTauLabel = "PFTau"
elif hlt_algorithm == "hps":
  hlt_pfTauLabel = "HpsPFTau"
else:
  raise ValueError("Invalid parameter hlt_algorithm = '%s' !!" % hlt_algorithm)

hlt_pfTauSuffix = "%iHits" % hlt_isolation_minTrackHits
if hlt_isolation_maxDeltaZOption == "primaryVertex":
  hlt_pfTauSuffix += "MaxDeltaZ"
elif hlt_isolation_maxDeltaZOption == "leadTrack":
  hlt_pfTauSuffix += "MaxDeltaZToLeadTrack"
else:
  raise ValueError("Invalid parameter hlt_isolation_maxDeltaZOption = '%s' !!" % hlt_isolation_maxDeltaZOption)
if hlt_srcVertices == "offlinePrimaryVertices":
  hlt_pfTauSuffix += "WithOfflineVertices"
elif hlt_srcVertices == "hltPhase2PixelVertices":
  hlt_pfTauSuffix += "WithOnlineVertices"
elif hlt_srcVertices == "hltPhase2TrimmedPixelVertices":
  hlt_pfTauSuffix += "WithOnlineVerticesTrimmed"
else:
  raise ValueError("Invalid parameter hlt_srcVertices = '%s' !!" % hlt_srcVertices)

#----------------------------------------------------------------------------
# CV: add DeepTau tau ID discriminator
from HLTrigger.TallinnHLTPFTauAnalyzer.tools.addDeepTauDiscriminator import addDeepTauDiscriminator
hlt_srcPFTaus = 'hltSelected%ss%s' % (hlt_pfTauLabel, hlt_pfTauSuffix)
hlt_srcPFJets = 'hlt%sAK4PFJets%s' % (hlt_pfTauLabel, hlt_pfTauSuffix)
deepTauSequenceName = "hltDeep%sSequence%s" % (hlt_pfTauLabel, hlt_pfTauSuffix)
deepTauSequence = addDeepTauDiscriminator(process, hlt_srcPFTaus, hlt_srcPFJets, hlt_srcVertices, hlt_pfTauLabel, hlt_pfTauSuffix, deepTauSequenceName)
process.analysisSequence += deepTauSequence
#----------------------------------------------------------------------------

# CV: restrict DeepTau to generator-level matched taus (for easier debugging)
moduleName_selectedPatTaus = "hltSelectedPat%ss%s" % (hlt_pfTauLabel, hlt_pfTauSuffix)
module_selectedPatTaus = getattr(process, moduleName_selectedPatTaus)
process.genMatchedPatTaus = cms.EDFilter("PATTauAntiOverlapSelector",
  src = cms.InputTag(moduleName_selectedPatTaus),
  srcNotToBeFiltered = cms.VInputTag('selectedGenHadTaus'),
  dRmin = cms.double(0.3),
  invert = cms.bool(True),
  filter = cms.bool(False)                                                          
)
deepTauSequence.replace(module_selectedPatTaus, module_selectedPatTaus + process.genMatchedPatTaus)
moduleName_slimmedTaus = "hltSlimmed%ss%s" % (hlt_pfTauLabel, hlt_pfTauSuffix)
module_slimmedTaus = getattr(process, moduleName_slimmedTaus)
module_slimmedTaus.src = cms.InputTag('genMatchedPatTaus')

# CV: restrict debugging to DeepTau that was trained on even events (for easier debugging)
moduleName_deepTau_odd = "hltDeep%sOdd%s" % (hlt_pfTauLabel, hlt_pfTauSuffix)
deepTauSequence.remove(getattr(process, moduleName_deepTau_odd))
moduleName_updatedPatTaus_odd = "hltUpdatedPat%ssOdd%s" % (hlt_pfTauLabel, hlt_pfTauSuffix)
deepTauSequence.remove(getattr(process, moduleName_updatedPatTaus_odd))
moduleName_updatedPatTaus = "hltUpdatedPat%ss%s" % (hlt_pfTauLabel, hlt_pfTauSuffix)
deepTauSequence.remove(getattr(process, moduleName_updatedPatTaus))

# CV: enable debug output for DeepTauId module
##moduleName_deepTau_even = "hltDeep%sEven%s" % (hlt_pfTauLabel, hlt_pfTauSuffix)
##module_deepTau_even = getattr(process, moduleName_deepTau_even)
##module_deepTau_even.debug_level = cms.int32(1)
##module_deepTau_even.save_inputs = cms.bool(True)

moduleName_updatedPatTaus_even = "hltUpdatedPat%ssEven%s" % (hlt_pfTauLabel, hlt_pfTauSuffix)
process.testDeepTau = cms.EDAnalyzer("DeepTauTest",
  taus = cms.InputTag(moduleName_updatedPatTaus_even),
  genEvent = cms.InputTag('generator'),
  genParticles = cms.InputTag('genParticles'),
  isMC = cms.bool(True)
)
process.analysisSequence += process.testDeepTau

process.p = cms.Path(process.analysisSequence)

process.TFileService = cms.Service('TFileService', 
  fileName = cms.string(outputFileName) 
)

process.options = cms.untracked.PSet(
    wantSummary = cms.untracked.bool(True)
)
