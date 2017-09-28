#!/usr/bin/python

# Created 2013-12-11, Jordi Huguet, Dept. Radiology AMC Amsterdam

####################################
__author__      = 'Jordi Huguet'  ##
__dateCreated__ = '20131211'      ##
__version__     = '2.0.4'         ##
__versionDate__ = '20170328'      ##
####################################

#main packages
import os
import sys 
import shutil
import getpass
import argparse
import urllib
import tempfile
import traceback
import nibabel
# custom-brewed libraries
import parrec2nii
import xnatLibrary
import mosaicCreator

def normalizeName(name):
    '''Replace awkward chars for underscores'''
    '''Returns a normalized name string'''
    
    name = name.replace("/", " ")
    name = name.replace(",", " ")
    name = name.replace(".", " ")
    name = name.replace("^", " ")
    name = name.replace(" ", "_")
    return name

def locatePARRECfiles(fileName):
    '''Locate the pairs of PAR and REC image files'''
    '''Returns a struct with the file names'''
    
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
        raise Exception('[Error] Unknown format of the file to be uploaded: %s' %originalName)
        
    return PARRECfilepair
    
def parseParHeader(parFile):
##########################################################################
# Using nibabel package, provides r/w access to neuroimaging file formats
# Source: http://nipy.org/nibabel
# Authors: Matthew Brett and Michael Hanke Abate
##########################################################################    
    '''Open and parse the PAR file specified by using nibabel module'''
    '''Returns 2 metadata structures of the PARREC header (dictionary of general info, array of image info)'''
    
    #open PAR file and parse the PAR header
    try:
        fobj = open(parFile, 'r')
    except IOError:
        raise Exception('Cannot open file: %s' %parFile)
    else: 
        try: 
            dict,array = nibabel.parrec.parse_PAR_header(fobj)
        except Exception:
            raise Exception('%s cannot be parsed as a PAR file ' %parFile)
        finally:
            fobj.close()

    return dict,array
    
def getPARRECHeader(parFile,dict,array):
##########################################################################
# Using nibabel package, provides r/w access to neuroimaging file formats
# Source: http://nipy.org/nibabel
# Authors: Matthew Brett and Michael Hanke Abate
##########################################################################    
    '''Instantiate a PARRECHeader class object which provides additional info calculated/extracted from PAR/REC files'''
    '''Returns a nibabel.parrec.PARRECHeader instance'''
    
    hPARREC = None
    
    try: 
        hPARREC = nibabel.parrec.PARRECHeader(dict,array)
    except Exception as e:
        #just dump exception message, error parsing PARREC    
        if args['verbose'] : print '[Warning] PARREC header for %s cannot be parsed.\r\n   Reason:: %s' %(os.path.basename(parFile),e)
            
    return hPARREC            

def uploadParrecScan(XNAT,project,subject,session,scanID,fileName):
    '''Upload a duple of PAR/REC files representing an Scan resource'''
    '''Returns a HTTPlib response'''    
    
    resourceLabel = 'PARREC'
    
    # Check if file pair (.PAR and .REC) exist and is available
    filepair = locatePARRECfiles(fileName)
    
    #compose the URL for the REST call
    URL = XNAT.host + '/data/projects/'
    URL += project
    URL += '/subjects/'
    URL += subject
    URL += '/experiments/'
    URL += session
    URL += '/scans/'
    URL += scanID
    scanURL = URL
    URL += '/resources/'
    URL += resourceLabel
    URL += '/files/'
    URL_PAR = URL + scanID + '.PAR'
    URL_REC = URL + scanID +'.REC'
    
    # Check if scan exists and connectivity is unavailable    
    if XNAT.resourceExist(scanURL).status != 200 :
        raise xnatLibrary.XNATException('XNAT Scan %s is unreachable at: %s' % (session, scanURL) )
    
    #Otherwise, lets create it!
    #Create and convert the dict (metadata) to a encoded string suitable for the HTTP request
    opts_dict = { 'format': 'PARREC', 'content': 'RAW' }            
    opts = urllib.urlencode(opts_dict)
    
    #responses = []
    for key, value in filepair.iteritems():
        #For management purposes parse/split the URL
        if key == 'PAR' :
            cURL = URL_PAR
        elif key == 'REC' :
            cURL = URL_REC
        
        # Check if resource files already existed
        if XNAT.resourceExist(cURL).status == 200 :
            raise xnatLibrary.XNATException('A Resource with such name (%s) already exists within the current context' %(scanID+'.'+key))
        
        resp = XNAT.putFile(cURL, value, opts)
        if resp.status == 200 and args['verbose'] : print '[Info] File %s successfully uploaded' %value 
        #responses.append(resp)
        
    #return responses
    return
    
def uploadNiftiScan(XNAT,project,subject,session,scanID,fileSet):
    '''Upload NIFTI generated file(s) representing an Scan resource'''
    '''Returns a HTTPlib response'''    
    
    resourceLabel = 'NIFTI'
    
    #compose the URL for the REST call
    URL = XNAT.host + '/data/projects/'
    URL += project
    URL += '/subjects/'
    URL += subject
    URL += '/experiments/'
    URL += session
    URL += '/scans/'
    URL += scanID
    scanURL = URL
    URL += '/resources/'
    URL += resourceLabel
    URL += '/files/'
    URL_nii = URL + scanID + '.nii'
    URL_bval = URL + scanID + '.bval'
    URL_bvec = URL + scanID + '.bvec'
        
    # Check if scan exists and connectivity is unavailable    
    if XNAT.resourceExist(scanURL).status != 200 :
        raise xnatLibrary.XNATException('XNAT Scan %s is unreachable at: %s' % (session, scanURL) )
        
    #Otherwise, lets create it!
    #Create and convert the dict (metadata) to a encoded string suitable for the HTTP request
    opts_dict = { 'format': 'NIFTI', 'content': 'RAW' }            
    opts = urllib.urlencode(opts_dict)
    
    #responses = []
    for key, value in fileSet.iteritems():
        #For management purposes parse/split the URL
        if key == 'nii' :
            cURL = URL_nii
        elif key == 'bval' :
            cURL = URL_bval
        elif key == 'bvec' :
            cURL = URL_bvec
        
            
        # Check if resource files already existed
        if XNAT.resourceExist(cURL).status == 200 :
            raise xnatLibrary.XNATException('A Resource with such name (%s) already exists within the current context' %(scanID+'.'+key))
        
        resp = XNAT.putFile(cURL, value, opts)
        if resp.status == 200 and args['verbose'] : print '[Info] File %s successfully uploaded' %value 
        #responses.append(resp)
        
    #return responses
    return
    
def uploadSnapshots(XNAT,project,subject,session,scanID,files):
    '''Upload SNAPSHOT files for visual quality control'''
    '''Returns a HTTPlib response'''    
    resourceLabel = 'SNAPSHOTS'
    
    #compose the URL for the REST call
    URL = XNAT.host + '/data/projects/'
    URL += project
    URL += '/subjects/'
    URL += subject
    URL += '/experiments/'
    URL += session
    URL += '/scans/'
    URL += scanID
    scanURL = URL
    URL += '/resources/'
    URL += resourceLabel
    oURL = URL + '/files/'
    oURL += scanID + os.path.splitext(files['ORIGINAL'])[1]
    
    if XNAT.resourceExist(scanURL).status == 404 :
        raise xnatLibrary.XNATException('Scan could not be found at %s' %URL )
    
    # Requested resource collection could not be found (HTTP status code #404)
    if XNAT.resourceExist(URL).status == 404 :
        opts_dict = { 'format': os.path.splitext(files['ORIGINAL'])[1][1:].upper(), 'content': resourceLabel }            
        
        #Convert the options to an encoded string suitable for the HTTP request
        opts = urllib.urlencode(opts_dict)    
    
        resp,output = XNAT.putURL(URL, opts)
        if resp.status == 200 and args['verbose'] : print '[Info] Resource collection %s successfully created' %resourceLabel 
        
    if XNAT.resourceExist(oURL).status == 200 :
        raise xnatLibrary.XNATException('File with same name %s already exists' %files['ORIGINAL'])
    else:                            
        opts_dict = { 'format': os.path.splitext(files['ORIGINAL'])[1][1:].upper(), 'content': 'ORIGINAL' }            
        
        #Convert the options to an encoded string suitable for the HTTP request
        opts = urllib.urlencode(opts_dict)    
        resp = XNAT.putFile(oURL, files['ORIGINAL'], opts)
        
        if resp.status == 200 and args['verbose'] : print '[Info] Snapshot for %s successfully uploaded' %scanURL
            
    
    if files.has_key('THUMBNAIL'):
        
        tURL = URL + '/files/'
        tURL += scanID + '_thumb' + os.path.splitext(files['THUMBNAIL'])[1]
    
        if XNAT.resourceExist(tURL).status == 200 :
            raise xnatLibrary.XNATException('File with same name %s already exists' %files['THUMBNAIL'])
        else:                            
            opts_dict = { 'format': os.path.splitext(files['THUMBNAIL'])[1][1:].upper(), 'content': 'THUMBNAIL' }            
            
            #Convert the options to an encoded string suitable for the HTTP request
            opts = urllib.urlencode(opts_dict)    
            resp = XNAT.putFile(tURL, files['THUMBNAIL'], opts)
            
            if resp.status == 200 and args['verbose'] : print '[Info] Thumbnail for %s successfully uploaded' %scanURL
            
    return

def main(XNAT,args):
    '''Main function: Locate, load and parse all  recursively available PAR files at the specified location'''    
    '''[@arg] XNAT :: XNAT instance'''
    '''[@arg] args :: dictionary with input arguments'''
    
    for root,dirs,files in os.walk(args['input']):                            
        if len(files) > 0:            
            for n in xrange(len(files)):            
                if ( os.path.splitext(files[n])[1].upper() == '.PAR') :
                    
                    #[STEP 1] : parse the PAR header file content
                    dict, array = parseParHeader(os.path.join(root,files[n]))
                    #get PARRECHeader class instance
                    hPARREC = getPARRECHeader(os.path.join(root,files[n]),dict,array)
                    
                    #[STEP 2] : add a Subject instance to XNAT
                    if not dict['patient_name'] : 
                        raise Exception('SubjectName not included in PAR file %s' % os.path.join(root,files[n]) )
                    
                    subjectName = normalizeName(dict['patient_name'])
                    if not subjectName or subjectName == "" : 
                        raise Exception('Subject name not provided')                
                    try: 
                        resp, subjectID = XNAT.addSubject(args['project'],subjectName)
                        if resp.status == 201 and args['verbose'] : print '[Info] Subject %s created' %subjectID
                        
                    except xnatLibrary.XNATException as xnatErr:
                        if args['verbose'] : print '[Warning] Issue creating Subject.\r\n   Reason:: %s' %xnatErr
                        
                    #[STEP 3] : add a Session instance to XNAT
                    dictSess = {}
                    if 'MR' not in dict['series_type'] : 
                        raise Exception('Unsupported or no modality attribute found, infer is an MR scan. File: %s' %xnatErr)
                        
                    dictSess['xnat:mrSessionData/modality'] = 'MR'
                    dictSess['xsiType'] = 'xnat:mrSessionData'
                    
                    datetime = dict['exam_date'].split(" / ")
                    date = datetime[0].split(".")
                    dateString = date[1]+'/'+date[2]+'/'+date[0]
                    dictSess['xnat:mrSessionData/date'] = dateString
                    dictSess['xnat:mrSessionData/time'] = datetime[1]
                    
                    # [[W A R N I N G!]] This is always bringing problems due to bad PAR/REC data naming!
                    examName = normalizeName(dict['exam_name'])
                    #examName = subjectName + '_' + normalizeName(dict['exam_name'])
                    #examName = subjectName + '_MR1'
                    
                    try: 
                        resp, sessionID = XNAT.addSession(args['project'],subjectName,examName, dictSess)
                        if resp.status == 201 and args['verbose'] : print '[Info] Session %s created' %sessionID
                    
                    except xnatLibrary.XNATException as xnatErr:
                        if args['verbose'] : print '[Warning] Issue creating Session.\r\n   Reason:: %s' %xnatErr
                    
                    #[STEP 4] : add a Scan instance to XNAT
                    dictScan = {}
                    
                    if 'MR' in dict['series_type'] : 
                        dictScan['xsiType'] = 'xnat:mrScanData'
                        dictScan['xnat:mrScanData/modality'] = 'MR'
                    
                    dictScan['xnat:mrScanData/series_description'] = dict['protocol_name']
                    acqNumber = ( int(dict['acq_nr']) * 100 ) + 1
                    dictScan['xnat:mrScanData/ID'] = str(acqNumber)
                    
                    # Compute the # of slices (NSG DTIPreprocessing) and add DTI-specific XNAT metadata
                    nSlices = len(array['index in REC file'])
                    dictScan['xnat:mrScanData/frames'] = nSlices
                    
                    # Following attribute not present in old-school PAR/REC files
                    if 'max_gradient_orient' in dict :
                        dictScan['xnat:mrScanData/parameters/diffusion/orientations'] = dict['max_gradient_orient']
                    
                    # DICOM compatibility: parse protocol name from PAR/REC and split WIP substring 
                    protoName = dict['protocol_name']
                    wippedList = protoName.split('WIP')
                    if len(wippedList) == 1 : 
                        dictScan['xnat:mrScanData/type'] = wippedList[0]
                    else : 
                        #Assume there's some typo at the beginning of the description text
                        dictScan['xnat:mrScanData/type'] = wippedList[1]                        
                    
                    dictScan['xnat:mrScanData/parameters/fov/x'] = int(dict['fov'][0])
                    dictScan['xnat:mrScanData/parameters/fov/y'] = int(dict['fov'][1])
                    dictScan['xnat:mrScanData/parameters/tr'] = dict['repetition_time'][0]
                    
                    if hPARREC is not None: 
                        voxel = hPARREC.get_voxel_size()
                        dictScan['xnat:mrScanData/parameters/voxelRes/x'] = voxel[0]
                        dictScan['xnat:mrScanData/parameters/voxelRes/y'] = voxel[1]
                        dictScan['xnat:mrScanData/parameters/voxelRes/z'] = voxel[2]
                    
                    #params defined atomically at slice level at PAR/REC while homogeneously defined per scan at XNAT
                    #Assumption: value is constant per all scan's slices, so will just check one (slice)
                    dictScan['xnat:mrScanData/parameters/te'] = array['echo_time'][0]
                    dictScan['xnat:mrScanData/parameters/ti'] = array['Inversion delay'][0]
                    dictScan['xnat:mrScanData/parameters/flip'] = int(array['image_flip_angle'][0])
                    
                    #Assumption: if a scan has to be created, data quality will be set to 'usable'
                    dictScan['quality'] = 'usable'
                    
                    try: 
                        resp = XNAT.addScan(args['project'],subjectName,examName,dictScan['xnat:mrScanData/ID'],dictScan)
                        if resp.status == 200 and args['verbose'] : print '[Info] Scan %s created' %dictScan['xnat:mrScanData/ID']
                        
                    except xnatLibrary.XNATException as xnatErr:
                        if args['verbose'] : print '[Warning] Issue creating Scan.\r\n   Reason:: %s' %xnatErr
                    
                    #[STEP 5] : upload the corresponding Scan image files                        
                    try: 
                        uploadParrecScan(XNAT,args['project'],subjectName,examName,dictScan['xnat:mrScanData/ID'],os.path.join(root,files[n]))                                                            
                    except xnatLibrary.XNATException as xnatErr:
                        if args['verbose'] : print '[Warning] Unable to upload PARREC files for scan %s.\r\n   Reason:: %s' %(dictScan['xnat:mrScanData/ID'], xnatErr)
                    
                    #[STEP 6] : create and upload snapshot images for data preview (visual quality control) 
                    if args['snapshots']:
                        try:
                            tmpSnapLocation=tempfile.mkdtemp()
                            PARRECfilepair = locatePARRECfiles(os.path.join(root,files[n]))
                            
                            imageDataBlob = mosaicCreator.imageExtractor(PARRECfilepair['PAR'])
                            outSnapFileName = os.path.splitext(os.path.basename(PARRECfilepair['PAR']))[0] + '.png'
                            outSnapFullFileName = os.path.join(tmpSnapLocation,outSnapFileName)
                            
                            outputFiles = mosaicCreator.mosaicCreator(imageDataBlob,outSnapFullFileName,thumb=True)
                            
                        except Exception as e:
                            #just dump exception message and move ahead, they are only snapshots
                            if args['verbose'] : print '[Error] mosaic-related issue with file %s\r\n   Reason:: %s' % (PARRECfilepair['PAR'], e)
                        else: 
                            # upload the SNAPSHOT files to XNAT (REST trickery)
                            try: 
                                uploadSnapshots(XNAT,args['project'],subjectName,examName,dictScan['xnat:mrScanData/ID'],outputFiles)                                                            
                                
                            except xnatLibrary.XNATException as xnatErr:
                                if args['verbose'] : print '[Warning] Unable to upload SNAPSHOTS files for scan %s.\r\n   Reason:: %s' %(dictScan['xnat:mrScanData/ID'], xnatErr)                                
                        finally:
                            # Always delete the temporary directory
                            if os.path.exists(tmpSnapLocation) :
                                shutil.rmtree(tmpSnapLocation) 

                                
                    #[STEP 7] : convert PAR/REC to NIFTI and upload the generated Scan image files
                    if args['nifti']:
                        try:        
                            tmpNiiLocation=tempfile.mkdtemp()
                        
                            PARRECfilepair = locatePARRECfiles(os.path.join(root,files[n]))
                            # COMPOSE the opts for calling proc_file (parrec2nii)
                            opts = {
                            'verbose': args['verbose'], # verbosal mode on/off
                            'outdir': tmpNiiLocation, # destination directory for converted NIfTI files
                            'compressed': False, # write compressed NIfTI files (gz) or not
                            'permit_truncated' : False, # disable conversion of truncated recordings  (experimental setting)
                            'bvs' : True, # write out bvals/bvecs if DTI
                            'dwell_time' : False, # do not calculate the scan dwell time
                            'origin': 'scanner', # reference point of the q-form transformation of the NIfTI image. If 'scanner', (0,0,0) = scanner's iso center
                            'minmax': ('parse', 'parse'), # mininum and maximum settings stored in the header. If 'parse' -> data scanned
                            'store_header': False, # keep information from the PAR header in an extension of the NIfTI file header
                            'scaling': 'off', # data scaling setting disabled completely (off == dv)
                            'keep_trace': False, # keep the diagnostic Philips DTI trace volume, if exists (??!!)
                            'overwrite': True, # overwrite file if it exists
                               }
                            
                            generatedFiles = parrec2nii.convert(PARRECfilepair['PAR'],opts)
                            
                            # lets use as a workaround (bug found in the conversion) the mricron tool for converting to NIfTI
                            #if 'win' in sys.platform :
                            #    args = "-x N -b L:\\basic\\divi\\Users\\jhuguet\\dcm2nii.ini -f Y -o \"%s\" %s" %(tmpNiiLocation,PARRECfilepair['PAR'])
                            #    command = 'dcm2nii.exe ' + args
                            #    sub.call(command)#, stdout=FNULL, stderr=FNULL, shell=False)
                            #elif 'linux' in sys.platform :
                            #    command = ['dcm2nii', '-b', os.path.join(os.path.expanduser('~'),'.dcm2nii','dcm2nii.ini'), '-f', 'Y', '-o', tmpNiiLocation, PARRECfilepair['PAR']]
                            #    #command = 'dcm2nii ' + args                                
                            #    sub.call(command)#, stdout=FNULL, stderr=FNULL, shell=False)
                            
                        except Exception as e:
                            #just dump exception message and move ahead, error parsing PARREC
                            if args['verbose'] : print '[Error] parrec2nii-related issue with file %s.\r\n   Reason:: %s' % (PARRECfilepair['PAR'], e)
                        else: 
                            # upload the NIFTI converted data to XNAT (REST trickery)
                            if generatedFiles.get('nii') :
                                try: 
                                    uploadNiftiScan(XNAT,args['project'],subjectName,examName,dictScan['xnat:mrScanData/ID'],generatedFiles)                                                            
                                    
                                except xnatLibrary.XNATException as xnatErr:
                                    if args['verbose'] : print '[Warning] Unable to upload NIFTI files for scan %s.\r\n   Reason:: %s' %(dictScan['xnat:mrScanData/ID'], xnatErr)                                
                        finally:
                            # Always delete the temporary directory
                            if os.path.exists(tmpNiiLocation) :
                                shutil.rmtree(tmpNiiLocation) 
        
    return


###                                                        ###
#           top-level script environment                   #
###                                                        ###

if __name__=="__main__" :
    print ''
    #'parrec2xnat :: Parse and upload PARREC data to XNAT archive (version 2)'
    
    # argparse trickery
    parser = argparse.ArgumentParser(description='%s :: Upload PAR/REC MRI data to XNAT' %os.path.basename(sys.argv[0]))
    parser.add_argument('-H','--host', dest="hostname", help='XNAT hostname URL (e.g. https://3tmri.nl/xnat)', required=True)
    parser.add_argument('-p','--proj', dest="project", help='XNAT project ID', required=True)
    parser.add_argument('-u','--user', dest="username", help='XNAT username (will be prompted for password)', required=True)
    parser.add_argument('-i','--input', dest="input", help='Input PAR/REC data location', required=True)    
    parser.add_argument('-nii','--nifti', dest="nifti", action='store_true', default=False, help='Additionally upload input data in NIfTI format', required=False)    
    parser.add_argument('-s','--snapshots', dest="snapshots", action='store_true', default=False, help='Create snapshots for visual data quality control (optional)', required=False)
    parser.add_argument('-v','--verbose', dest="verbose", action='store_true', default=False, help='Display verbosal information (optional)', required=False)
    
    args = vars(parser.parse_args())
    
    # compose the HTTP basic authentication credentials string
    password = getpass.getpass('Password for user %s:' %args['username'])
    usr_pwd = args['username']+':'+password
    print ''
    
    try:         
        # check validity of input directory provided
        if not os.path.exists(args['input']) :
            raise Exception('Input directory ("%s") not found' %args['input'])
        
        # connect to XNAT
        with xnatLibrary.XNAT(args['hostname'],usr_pwd) as XNAT :
            if args['verbose'] : print '[Info] session %s opened' %XNAT.jsession
            
            # check if XNAT project exists
            if XNAT.resourceExist('%s/data/projects/%s' %(XNAT.host,args['project'])).status != 200 :
                raise xnatLibrary.XNATException('project ("%s") is unreachable at: %s' % (args['project'], XNAT.host) )
            
            # if all went OK, proceed to the main processing stage
            main(XNAT,args)    
            
            # disconnect from XNAT
            if args['verbose'] : print '[Info] session %s closed' %XNAT.jsession
        
    except xnatLibrary.XNATException as xnatErr:
        print '[Error] XNAT-related issue:', xnatErr        
    
    except Exception as e:
        print '[Error]', e    
        print(traceback.format_exc())
