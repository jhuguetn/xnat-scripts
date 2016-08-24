#!/usr/bin/python

# Created 2015-09-30, Jordi Huguet, Dept. Radiology AMC Amsterdam
# Credits to Russ Poldrack

####################################
__author__      = 'Jordi Huguet'  ##
__dateCreated__ = '20150930'      ##
__version__     = '0.2'           ##
__versionDate__ = '20151006'      ##
####################################

# mosaicCreator.py
# Script for, given a numpy readable 3D/4D image, make a mosaic composition and save as a image file (scan snapshot/preview)
#
# TO DO:
# - ...
# - 

import os
import sys
import argparse
import nibabel
import numpy
import math
import matplotlib
# by default matplotlib ships configured to work with a graphical user interface which may require an X11 connection (errors running on background!)
# 	+info:: http://matplotlib.org/faq/howto_faq.html#matplotlib-in-a-web-application-server
matplotlib.use('Agg') 
import matplotlib.pyplot as plot
import traceback

#supported image formats
inFormats = ['NII', 'PAR', 'REC'] # more supported input formats may come, eventually
outFormat = 'PNG'

def locatePARRECFiles(fileName):
	'''Given a file (PAR or REC), silly method for locating pairs of PAR and REC image files'''
	'''Returns an struct with the file names'''
	
	originalName = fileName
	PARRECfilepair = {}
	fileName, fileExtension = os.path.splitext(originalName)
	if fileExtension.upper() == '.PAR' :
		#is a PAR file, lets look for the REC
		if os.path.exists(originalName) and os.path.isfile(originalName):
			PARRECfilepair['PAR'] = originalName
		else: 			
			raise Exception('[Error] File %s not found' %originalName)
			
		if os.path.exists(fileName+'.REC') and os.path.isfile(fileName+'.REC'):
			PARRECfilepair['REC'] = fileName+'.REC'
		elif os.path.exists(fileName+'.rec') and os.path.isfile(fileName+'.rec'):
			PARRECfilepair['REC'] = fileName+'.rec'
		else: 			
			raise Exception('[Error] File %s not found' %fileName+'.rec')
			
	elif fileExtension.upper() == '.REC' :
		#is a REC file, lets look for the PAR
		if os.path.exists(originalName) and os.path.isfile(originalName):
			PARRECfilepair['REC'] = originalName
		else: 			
			raise Exception('[Error] File %s not found: %s' %originalName)
			
		if os.path.exists(fileName+'.PAR') and os.path.isfile(fileName+'.PAR'):
			PARRECfilepair['PAR'] = fileName+'.PAR'
		elif os.path.exists(fileName+'.par') and os.path.isfile(fileName+'.par'):
			PARRECfilepair['PAR'] = fileName+'.par'
		else: 			
			raise Exception('[Error] File %s not found' %fileName+'.par')
			
	else :
		raise Exception('[Error] Unknown format of the file: %s' %originalName)
		
	return PARRECfilepair

def fileExtension(fileName):
	
	return (os.path.splitext(fileName)[1][1:]).upper()		
	
def imageExtractor(inFile):
	
	# Check input file path is valid 
	if not os.path.isfile(inFile) : 
		raise Exception('Input file not found: %s' %inFile )
	
	# Assert is a NIFTI file by checking extension
	ext = fileExtension(inFile)
	if ext not in inFormats :
		raise Exception('Unsuported file format (extension) for: %s' %os.path.basename(inFile) )	 

	# Load image data (either NIFTI or PAR/RECs)
	if ext == 'NII' :
		img=nibabel.load(inFile)
	else :	
		parrecFilePair = locatePARRECFiles(inFile)	
		img=nibabel.load(parrecFilePair['PAR'])
	
	#get data blob from image object
	imageData=img.get_data()
	
	return imageData

def mosaicCreator(imageData,outFile,title=None,ncols=None,colorbar=False,thumb=False):
	
	# Assert output file extension
	if fileExtension(outFile) != outFormat :
		outFile += '.png'
		if args['verbose'] : print '[Warning] Output file name modified to match file format extension: %s' %outFile 
	
	# Check output file path exists
	if os.path.isfile(outFile) or os.path.exists(outFile) : 
		raise Exception('Output file already exists: %s' %outFile )
	
	# Check output file parent directory exists
	if not os.path.exists(os.path.dirname(outFile)) : 
		raise Exception('Output file location (parent directory) not found: %s' %os.path.dirname(outFile) )
	
	# Particular case :: fMRI with several image dynamics, accept it but pick solely the first one
	if len(imageData.shape)==4 : imageData = imageData[:,:,:,0]
		
	if len(imageData.shape)!=3:
		raise Exception('Input file %s is not a valid multiframe image or has an unsupported size: %s' %(outFile, imageData.shape)) 
	
	# Check image dimensions for the min. one
	min_dim=numpy.where(numpy.min(imageData.shape[0:3])==imageData.shape[0:3])[0]
	slice_dims=numpy.where(numpy.min(imageData.shape[0:3])!=imageData.shape[0:3])[0]		
	
	# Auto-compute the number of cols if not provided manually
	if ncols == None :
		ncols = int(math.ceil(math.sqrt(imageData.shape[min_dim])))
	
	# Compute the number of rows the mosaic composition will have as well as the mosaic canvas size	
	nrows=int(numpy.ceil(numpy.float(imageData.shape[min_dim])/ncols))
	mosaic=numpy.zeros((nrows*imageData.shape[slice_dims[0]],ncols*imageData.shape[slice_dims[1]]))
	
	ctr=0
		
	for row in range(nrows):
		rowstart=row*imageData.shape[slice_dims[0]]
		rowend=(row+1)*imageData.shape[slice_dims[0]]
		for col in range(ncols):
			if ctr<imageData.shape[min_dim]:
				colstart=col*imageData.shape[slice_dims[1]]
				colend=(col+1)*imageData.shape[slice_dims[1]]
				
				if min_dim==0:
					imgslice=imageData[ctr,:,::-1].T					
				elif min_dim==1:
					imgslice=imageData[:,ctr,::-1].T
				elif min_dim==2:
					imgslice=imageData[:,::-1,ctr].T
				try:
					mosaic[rowstart:rowend,colstart:colend]=imgslice#[:,:,0]
				except:
					mosaic[rowstart:rowend,colstart:colend]=imgslice.T#[:,:,0]
					
				ctr+=1
	
	# decent figsize for being embedded in XNAT session pages			
	plot.figure(figsize=(12,12),frameon=False)
	plot.imshow(mosaic,cmap=plot.cm.gray)
	if title is not None:
		plot.title(title)
	if colorbar:
		plot.colorbar()
	plot.axis('off')
	plot.savefig(outFile,bbox_inches='tight')
	plot.close()
	
	thumbFile = None
	# if specified, create a lightweight thumbnail version of the mosaic image 
	if thumb :
		baseDirName = os.path.dirname(outFile)
		baseFileName = os.path.splitext(os.path.basename(outFile))[0]
		thumbFile = os.path.join(baseDirName, baseFileName + "_thumb.png")
		
		# Check if thumbnail file exists
		if os.path.isfile(thumbFile) or os.path.exists(thumbFile) : 
			raise Exception('Output file already exists: %s' %outFile )
		
		plot.figure(figsize=(4,4),frameon=False)
		plot.imshow(mosaic,cmap=plot.cm.gray)
		if title is not None:
			plot.title(title)
		if colorbar:
			plot.colorbar()
		plot.axis('off')
		plot.savefig(thumbFile,bbox_inches='tight')
		plot.close()
	
	return { 'ORIGINAL' : outFile, 'THUMBNAIL' : thumbFile }
	
###													###
# Top-level script environment					 	  #
###													###

if __name__=="__main__" :
	print ''
	
	# argparse trickery
	parser = argparse.ArgumentParser(description='%s :: Create a mosaic composition of a scan dataset and save as a image file' %os.path.basename(sys.argv[0]))
	parser.add_argument('-in','--inputFile', dest="inputFile", help='Input image file (NIfTI formatted)', required=True)
	parser.add_argument('-out','--outputFile', dest="outputFile", help='Output image file (PNG formatted)', required=True)
	parser.add_argument('-c','--cols', dest="columns", help='Number of columns/rows of the mosaic image (optional)', required=False)
	parser.add_argument('-t','--thumb', dest="thumbnail", action='store_true', default=False, help='Create thumbnail version of the mosaic(optional)', required=False)
	parser.add_argument('-v','--verbose', dest="verbose", action='store_true', default=False, help='Display verbosal information(optional)', required=False)
	
	
	args = vars(parser.parse_args())
	
	try: 		
		imageDataBlob = imageExtractor(args['inputFile'])
		
		if args['columns'] : 
			outputFiles = mosaicCreator(imageDataBlob,args['outputFile'],ncols=int(args['columns']), thumb=args['thumbnail'])
		else : 
			outputFiles = mosaicCreator(imageDataBlob,args['outputFile'], ncols=args['columns'], thumb=args['thumbnail'])
		
		if args['verbose'] : 
			print '[Info] Snapshot file created! %s' %outputFiles['ORIGINAL']
			if len(outputFiles) == 2 : print '[Info] Snapshot thumbnail file created! %s' %outputFiles['THUMBNAIL']
		
	except Exception as err:
		if args['verbose'] : print ' [Error] ', err	
		print(traceback.format_exc())