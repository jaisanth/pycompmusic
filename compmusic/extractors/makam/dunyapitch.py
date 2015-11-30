# -*- coding: utf-8 -*-
# Copyright 2013,2014 Music Technology Group - Universitat Pompeu Fabra
#
# This file is part of Dunya
#
# Dunya is free software: you can redistribute it and/or modify it under the
# terms of the GNU Affero General Public License as published by the Free Software
# Foundation (FSF), either version 3 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
# PARTICULAR PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# this program.  If not, see http://www.gnu.org/licenses/
#
# If you are using this extractor please cite the following paper:
#
# Atlı, H. S., Uyar, B., Şentürk, S., Bozkurt, B., and Serra, X. (2014). Audio
# feature extraction for exploring Turkish makam music. In Proceedings of 3rd
# International Conference on Audio Technologies for Music and Media, Ankara,
# Turkey.

import compmusic.extractors.makam.pitch
from docserver import util

from alignedpitchfilter import alignedpitchfilter
from alignednotemodel.PitchDistribution import hz_to_cent, cent_to_hz
from alignednotemodel import alignednotemodel

from numpy import size
from numpy import array
from numpy import vstack
from numpy import transpose

import os
import struct
import json
import scipy.io
import cStringIO

class CorrectedPitchMakam(compmusic.extractors.ExtractorModule):
  _version = "0.2"
  _sourcetype = "mp3"
  _slug = "correctedpitchmakam"
  _output = {
          "pitch": {"extension": "json", "mimetype": "application/json"},
          "notemodels": {"extension": "json", "mimetype": "application/json"},
          "histogram": {"extension": "json", "mimetype": "application/json"},
          "corrected_alignednotes": {"extension": "json", "mimetype": "application/json"},
  }

  def run(self, musicbrainzid, fname):
    # Compute the pitch octave correction

    pitchfile = util.docserver_get_filename(musicbrainzid, "initialmakampitch", "pitch", version="0.6")
    tonicfile = util.docserver_get_filename(musicbrainzid, "tonictempotuning", "tonic", version="0.1")
    tuningfile = util.docserver_get_filename(musicbrainzid, "tonictempotuning", "tuning", version="0.1")
    alignednotefile = util.docserver_get_filename(musicbrainzid, "scorealign", "notesalign", version="0.1")

    pitch = array(json.load(open(pitchfile, 'r')))
    tonic = json.load(open(tonicfile, 'r'))['scoreInformed']
    tuning = json.load(open(tuningfile, 'r'))['scoreInformed']
    notes = json.load(open(alignednotefile, 'r'))['notes']

    pitch_corrected, synth_pitch, notes_corrected = alignedpitchfilter.correctOctaveErrors(pitch, notes)
   
    #notes = json.load(open(alignednotefile, 'r'))['notes']

    noteModels, pitchDistribution, newTonic = alignednotemodel.getModels(pitch_corrected, notes_corrected, tonic, tuning, kernel_width=7.5)
   
    dist_json = [{'bins': pitchDistribution.bins.tolist(), 'vals': pitchDistribution.vals.tolist(),
                  'kernel_width': pitchDistribution.kernel_width, 'ref_freq': pitchDistribution.ref_freq, 
                  'step_size': pitchDistribution.step_size}]
    output = {}
    output["corrected_alignednotes"] = notes_corrected
    output["notemodels"] = noteModels
    output["histogram"] = dist_json
    output["pitch"] = pitch_corrected
    return output

class DunyaPitchMakam(compmusic.extractors.makam.pitch.PitchExtractMakam):
  _version = "0.2"
  _sourcetype = "mp3"
  _slug = "dunyapitchmakam"
  _output = {
          "pitch": {"extension": "dat", "mimetype": "application/octet-stream"},
          "pitchmax": { "extension": "json", "mimetype": "application/json"},
  }

  def setup(self):
    self.add_settings(hopSize = 196, # default hopSize of PredominantMelody
                      frameSize = 2048, # default frameSize of PredominantMelody
                      sampleRate = 44100,
                      binResolution = 7.5, # ~1/3 Hc; recommended for makams
                      minFrequency = 55, # default minimum of PitchSalienceFunction
                      maxFrequency = 1760, # default maximum of PitchSalienceFunction
                      magnitudeThreshold = 0, # default of SpectralPeaks; 0 dB?
                      peakDistributionThreshold = 1.4, # default in PitchContours is 0.9; we need higher in makams
                      filterPitch = True, # call PitchFilter
                      confidenceThreshold = 36, # default confidenceThreshold for pitchFilter
                      minChunkSize = 50) # number of minimum allowed samples of a chunk in PitchFilter; ~145 ms with 128 sample hopSize & 44100 Fs

  def run(self, musicbrainzid, fname):
    output = super(DunyaPitchMakam, self).run(musicbrainzid, fname)

    # Compute the pitch octave correction for display in dunya

    tonicfile = util.docserver_get_filename(musicbrainzid, "tonictempotuning", "tonic", version="0.1")
    alignednotefile = util.docserver_get_filename(musicbrainzid, "scorealign", "notesalign", version="0.1")

    pitch = array(output['pitch'])
    tonic = json.load(open(tonicfile, 'r'))['scoreInformed']
    notes = json.load(open(alignednotefile, 'r'))['notes']

    pitch_corrected, synth_pitch, notes = alignedpitchfilter.correctOctaveErrors(pitch, notes )
    
    pitch = [p[1] for p in pitch_corrected] 
    
    # pitches as bytearray 
    packed_pitch = cStringIO.StringIO()
    max_pitch = max(pitch) 
    temp = [p for p in pitch if p>0]
    min_pitch = min(temp) 
    
    height = 255
    for p in pitch:
        if p < min_pitch:
            packed_pitch.write(struct.pack("B", 0))
        else:
            packed_pitch.write(struct.pack("B", int((p - min_pitch) * 1.0 / (max_pitch - min_pitch) * height)))
                             
    
    output['pitch'] = packed_pitch.getvalue()
    output['pitchmax'] = {'max': max_pitch, 'min': min_pitch}
                                   
    del output["matlab"]
    del output["settings"]
    return output
