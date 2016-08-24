#!/usr/bin/python

# Created 2013-12-11, Jordi Huguet, Dept. Radiology AMC Amsterdam

# This work is based on parrec2nii binary tool developed in the NiBabel package covered by MIT License
# Copyrighted (c) to Matthew Brett <matthew.brett@gmail.com> et al. 

####################################
__author__      = 'Jordi Huguet'  ##
__dateCreated__ = '20150611'      ##
__version__     = '0.1.0'         ##
__versionDate__ = '20150611'      ##
####################################

'''PAR/REC to NIfTI MRI data converter as a function
'''

import os
import sys
import numpy
import nibabel

def convert(infile, options):
	'''Parse and process PAR/REC files and convert them to NIFTI file format. If DTI, bvec/bval might also be created'''
	'''[@arg] infile :: PAR header file (REC file expected in the same directory with exact name)'''
	'''[@arg] options :: class instance with input arguments (for integration purposes with early command-line tool version of parrec2nii)'''
	'''Returns a structure with the output file names generated and their format'''
	
	if options['verbose'] : print('[parrec2nii] Processing %s' % infile)
	outputFiles = {}
	
	if options['origin'] not in ['scanner', 'fov']:
		raise Exception("[parrec2nii] Unrecognized value for origin: '%s'" % options['origin'])
	if options['dwell_time'] and options['field_strength'] is None:
		raise Exception("[parrec2nii] Need field-strength option for dwell time calculation")
	
	# figure out the output filename, and see if it exists
	basefilename = nibabel.filename_parser.splitext_addext(os.path.basename(infile))[0]
	if options['outdir'] is not None:
		# set output path
		basefilename = os.path.join(options['outdir'], basefilename)

	# prep a file
	if options['compressed']:
		if options['verbose'] : print('[parrec2nii] Using gzip compression')
		outfilename = basefilename + '.nii.gz'
	else:
		outfilename = basefilename + '.nii'
	if os.path.isfile(outfilename) and not options['overwrite']:
		raise IOError('Output file "%s" exists, use overwrite option to '
					  'replace it' % outfilename)

	# load the PAR header and data
	scaling = 'dv' if options['scaling'] == 'off' else options['scaling']
	infile = nibabel.volumeutils.fname_ext_ul_case(infile)
	pr_img = nibabel.parrec.load(infile,
					 permit_truncated=options['permit_truncated'],
					 scaling=scaling)
	pr_hdr = pr_img.header
	affine = pr_hdr.get_affine(origin=options['origin'])
	slope, intercept = pr_hdr.get_data_scaling(scaling)
	if options['scaling'] != 'off':
		if options['verbose'] : print('[parrec2nii] Using data scaling "%s"' %options['scaling'])
	# get original scaling, and decide if we scale in-place or not
	if options['scaling'] == 'off':
		slope = numpy.array([1.])
		intercept = numpy.array([0.])
		in_data = pr_img.dataobj.get_unscaled()
		out_dtype = pr_hdr.get_data_dtype()
	elif not numpy.any(numpy.diff(slope)) and not numpy.any(numpy.diff(intercept)):
		# Single scalefactor case
		slope = slope.ravel()[0]
		intercept = intercept.ravel()[0]
		in_data = pr_img.dataobj.get_unscaled()
		out_dtype = pr_hdr.get_data_dtype()
	else:
		# Multi scalefactor case
		slope = numpy.array([1.])
		intercept = numpy.array([0.])
		in_data = numpy.array(pr_img.dataobj)
		out_dtype = numpy.float64
	# Reorient data block to LAS+ if necessary
	ornt = nibabel.orientations.io_orientation(numpy.diag([-1, 1, 1, 1]).dot(affine))
	if numpy.all(ornt == [[0, 1],
					   [1, 1],
					   [2, 1]]):  # already in LAS+
		t_aff = numpy.eye(4)
	else:  # Not in LAS+
		t_aff = nibabel.orientations.inv_ornt_aff(ornt, pr_img.shape)
		affine = numpy.dot(affine, t_aff)
		in_data = nibabel.orientations.apply_orientation(in_data, ornt)

	bvals, bvecs = pr_hdr.get_bvals_bvecs()
	if not options['keep_trace']:  # discard Philips DTI trace if present
		if bvals is not None:
			bad_mask = numpy.logical_and(bvals != 0, (bvecs == 0).all(axis=1))
			if bad_mask.sum() > 0:
				pl = 's' if bad_mask.sum() != 1 else ''
				if options['verbose'] : print('[parrec2nii] Removing %s DTI trace volume%s'
						% (bad_mask.sum(), pl))
				good_mask = ~bad_mask
				in_data = in_data[..., good_mask]
				bvals = bvals[good_mask]
				bvecs = bvecs[good_mask]

	# Make corresponding NIfTI image
	nimg = nibabel.nifti1.Nifti1Image(in_data, affine, pr_hdr)
	nhdr = nimg.header
	nhdr.set_data_dtype(out_dtype)
	nhdr.set_slope_inter(slope, intercept)

	if 'parse' in options['minmax']:
		# need to get the scaled data
		if options['verbose'] : print('[parrec2nii] Loading (and scaling) the data to determine value range')
	if options['minmax'][0] == 'parse':
		nhdr['cal_min'] = in_data.min() * slope + intercept
	else:
		nhdr['cal_min'] = float(options['minmax'][0])
	if options['minmax'][1] == 'parse':
		nhdr['cal_max'] = in_data.max() * slope + intercept
	else:
		nhdr['cal_max'] = float(options['minmax'][1])

	# container for potential NIfTI1 header extensions
	if options['store_header']:
		# dump the full PAR header content into an extension
		with open(infile, 'rb') as fobj:  # contents must be bytes
			hdr_dump = fobj.read()
			dump_ext = nibabel.nifti1.Nifti1Extension('comment', hdr_dump)
		nhdr.extensions.append(dump_ext)

	if options['verbose'] : print('[parrec2nii] Writing %s' % outfilename)
	nibabel.save(nimg, outfilename)
	outputFiles['nii'] = outfilename

	# write out bvals/bvecs if requested
	if options['bvs']:
		if bvals is None and bvecs is None:
			if options['verbose'] : print('[parrec2nii] No DTI volumes detected, bvals and bvecs not written')
		else:
			if os.path.isfile(basefilename + '.bval') and not options['overwrite']:
				raise IOError('Output file "%s" exists, use overwrite option to '
							  'replace it' % basefilename + '.bval')
			if os.path.isfile(basefilename + '.bvec') and not options['overwrite']:
				raise IOError('Output file "%s" exists, use overwrite option to '
							  'replace it' % basefilename + '.bvec')
			if options['verbose'] : print('[parrec2nii] Writing .bvals and .bvecs files')
			# Transform bvecs with reorientation affine
			orig2new = numpy.linalg.inv(t_aff)
			bv_reorient = nibabel.affines.from_matvec(nibabel.affines.to_matvec(orig2new)[0], [0, 0, 0])
			bvecs = nibabel.affines.apply_affine(bv_reorient, bvecs)
			with open(basefilename + '.bval', 'w') as fid:
				# np.savetxt could do this, but it's just a loop anyway
				for val in bvals:
					fid.write('%s ' % val)
				fid.write('\n')
			outputFiles['bval'] = basefilename + '.bval'
			with open(basefilename + '.bvec', 'w') as fid:
				for row in bvecs.T:
					for val in row:
						fid.write('%s ' % val)
					fid.write('\n')
			outputFiles['bvec'] = basefilename + '.bvec'

	# write out dwell time if requested
	if options['dwell_time']:
		if os.path.isfile(basefilename + '.dwell_time') and not options['overwrite']:
				raise IOError('Output file "%s" exists, use overwrite option to '
							  'replace it' % basefilename + '.dwell_time')
		try:
			dwell_time = nibabel.mriutils.calculate_dwell_time(
				pr_hdr.get_water_fat_shift(),
				pr_hdr.get_echo_train_length(),
				options['field_strength'])
		except MRIError:
			if options['verbose'] : print('[parrec2nii] No EPI factors, dwell time not written')
		else:
			if options['verbose'] : print('[parrec2nii] Writing dwell time (%r sec) calculated assuming %sT magnet' % (dwell_time, options['field_strength']))
			with open(basefilename + '.dwell_time', 'w') as fid:
				fid.write('%r\n' % dwell_time)
			outputFiles['dwell_time'] = basefilename + '.dwell_time'
	# done
	return outputFiles
