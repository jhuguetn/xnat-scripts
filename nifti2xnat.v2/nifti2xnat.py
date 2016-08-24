#!/usr/bin/python

# Created 2014-03-04, Jordi Huguet, Dept. Radiology AMC Amsterdam

####################################
__author__      = 'Jordi Huguet'  ##
__dateCreated__ = '20140304'      ##
__version__     = '2.1'           ##
__versionDate__ = '20160623'      ##
####################################

# TO DO:
# - ...

import os
import sys
import argparse
import xnatLibrary
import getpass
import urllib
import traceback

def normalizeName(name) :
    ''' Replace white-spaces for underscore chars or any other oddities '''
    ''' Returns a normalized name string '''
    #name = name.replace(".", " ")
    #name = name.replace("^", " ")
    return name.replace(" ", "_")

def isFileImage(fileName, extensions):    
    '''Checks a file extension against a list of extensions provided, returning a boolean depending on if it fits or not in the set'''
    return any( (fileName.lower()).endswith(ext) for ext in extensions)    

def imageFinder(dirName, extensions):
    '''Given a directory, traverses it, checks all files that are of an specific format by its name extension and returns a list of matches'''
    fileList = []
    
    for file in os.listdir(dirName):
        if os.path.isfile(os.path.join(dirName,file)) and isFileImage(file, extensions) :     
            fileList.append(file)
    
    return fileList

def getExtension(fileName):
    
    return (os.path.splitext(fileName)[1][1:]).lower()
    
def checkSessionCompleteness(dirRoot, fileList) :    
    ''' Assume it: NIFTI data is crap, no metadata provided to parse data provenance nor type...lets check MRStudy completion based on file names '''    
    '''[@arg] fileList :: List with input files defining a MR Session'''
    '''[@arg] dirRoot :: root directory containing the files'''
    
    mrSessionFiles = {}
    mrSessionFiles.update({ 'root' : dirRoot })
    
    for file in fileList:
        extension = getExtension(file)
        
        if extension == 'nii' :
            if 'T1' in file.upper() and 'T1' not in mrSessionFiles :
                mrSessionFiles.update({ 'T1' : file })
            elif 'DTI' in file.upper() and 'DTI' not in mrSessionFiles : 
                mrSessionFiles.update({ 'DTI' : file })
            else :
                print '[Warning] Unknown/unexpected file (or simply bad naming scheme) %s' %file
                
        elif extension == 'bvec' and 'BVEC' not in mrSessionFiles :
            mrSessionFiles.update({ 'BVEC' : file })    
        elif getExtension(file) == 'bval' and 'BVAL' not in mrSessionFiles :
            mrSessionFiles.update({ 'BVAL' : file })
        else :
            raise Exception('[Error] Unknown/unexpected file (or simply bad naming scheme) %s' %file)
    
    if ( 'BVEC' in mrSessionFiles.keys() or 'BVAL' in mrSessionFiles.keys() ) and ( 'DTI' not in mrSessionFiles.keys() ):
        raise Exception('[Error] BVEC/BVAL files present but not the DTI scan file at directory %s' %dirRoot)
    elif ( 'DTI' in mrSessionFiles.keys() and ('BVEC' not in mrSessionFiles.keys() or 'BVAL' not in mrSessionFiles.keys() )):
        print '[Warning] BVEC/BVAL files not found at %s' %dirRoot
        
    return mrSessionFiles
    
def pullSubjectName(scanFilesDict, fnFlag=True) :    
    ''' Given files or parent directory names, try to pull out the subjectName '''    
    '''[@arg] scanFilesDict :: Dictionary with input files defining a MR Session'''
    '''[@arg] fnFlag :: Filename boolean flag, if set to True infer the subjectName from file names. Use the parent directory name if set to False'''
    
    subjectName = None 
    
    if fnFlag : 
        # pick a random file, extract the scan definition (T1,DTI,...) and try matching with others
        if 'T1' in scanFilesDict.keys() :
            # only DTI scan 
            subjectName = os.path.splitext((scanFilesDict['DTI'].replace('DTI', '')).replace('_', ''))[0]            
            #if scanFilesDict['BVAL'] and scanFilesDict['BVEC'] and subjectName in [scanFilesDict['BVAL'], scanFilesDict['BVEC']] :                        
        elif 'DTI' in scanFilesDict.keys() :
            # only T1 scan
            subjectName = os.path.splitext((scanFilesDict['T1'].replace('T1', '')).replace('_', ''))[0]                                
    else : 
        subjectName= normalizeName( os.path.basename(scanFilesDict['root']) )
    
    return subjectName

def main(XNAT,args)    :
    ''' Main script function: Locate, load and parse all NIFTI files at the specified location'''    
    '''[@arg] XNAT :: xnatLibrary XNAT class instance'''
    '''[@arg] args :: dictionary with input arguments'''
        
    # traverse all the input directory tree searching for image cases
    for root,dirs,files in os.walk(args['input']):                            
        # check if the directory contains NIFTI scan files (i.e. images)
        iList = imageFinder(root, ['nii','bvec','bval'])
        if len(iList) > 0 :
            
            identifiedScanFiles = checkSessionCompleteness(root,iList)
            
            # [STEP1] : Add a new Subject instance to XNAT                
            subjectName = pullSubjectName(identifiedScanFiles, False)        
            
            if not subjectName or subjectName == "" : 
                    raise Exception('Subject name not located')                
            try: 
                resp, subjectID = XNAT.addSubject(args['project'],subjectName)
                if resp.status == 201 and args['verbose'] : print ' [Info] Subject %s created' %subjectID
            
            except xnatLibrary.XNATException as xnatErr:
                print ' [Warning] Issue creating Subject.\r\n   Reason:: %s' %xnatErr
            
            # [STEP2] : add a new Session instance to XNAT                        
            sessOpts = {}
            examName = subjectName
            
            sessOpts['xnat:mrSessionData/modality'] = 'MR'#byDefault_modality
            
            try: 
                resp, sessionID = XNAT.addSession(args['project'],subjectName,examName, sessOpts)
                if resp.status == 201 and args['verbose'] : print ' [Info] Session %s created' %sessionID
            
            except xnatLibrary.XNATException as xnatErr:
                print ' [Warning] Issue creating Session.\r\n   Reason:: %s' %xnatErr
            
            # [STEP3] : add new Scan instance(s) to XNAT
            if 'T1' in identifiedScanFiles.keys() :
                # T1 scan 
                scanID = str(101)
                scanType = 'T1'
                
                dictScan = {}
                dictScan['xsiType'] = 'xnat:mrScanData'#byDefault_dataType
                dictScan['xnat:mrScanData/series_description'] = scanType
                dictScan['xnat:mrScanData/type'] = scanType
                dictScan['xnat:mrScanData/ID'] = scanID
                dictScan['xnat:mrScanData/modality'] = 'MR'#byDefault_modality
                #Assumption: if a scan has to be uploaded and created, data quality will probably be OK. Set to 'usable'
                dictScan['quality'] = 'usable'
                
                try: 
                    resp = XNAT.addScan(args['project'],subjectName,examName, scanID, dictScan)
                    if resp.status == 200 and args['verbose'] : print ' [Info] Scan %s created' %scanID
            
                except xnatLibrary.XNATException as xnatErr:
                    print ' [Warning] Issue creating Scan.\r\n   Reason:: %s' %xnatErr
                
                # [STEP3.5] : upload NIfTI scan file to XNAT
                nii_file = os.path.join(identifiedScanFiles['root'],identifiedScanFiles['T1'])
        
                fileExtension = (os.path.splitext(nii_file)[1]).lower()
                fileNameToUpload = scanID + '_' + scanType + fileExtension
                
                
                URL = XNAT.host + '/data/projects/'
                URL += args['project']
                URL += '/subjects/'
                URL += subjectName
                URL += '/experiments/'
                URL += examName
                URL += '/scans/'
                URL += scanID                
                nURL = URL + '/resources/NIFTI/files/'
                nURL += fileNameToUpload
                #nURL += fileExtension
                
                if XNAT.resourceExist(nURL).status == 200 :
                    print '[Warning] File with same name %s already exists in XNAT' %fileNameToUpload
    
                else:                            
                    opts_dict = { 'format': 'NIFTI', 'content': 'RAW' }            
                    #Convert the options to an encoded string suitable for the HTTP request
                    opts = urllib.urlencode(opts_dict)
                    resp = XNAT.putFile(nURL, nii_file, opts)
                    
                    if resp.status == 200 and args['verbose'] : print ' [Info] NIfTI scan file %s successfully uploaded' %fileNameToUpload 

            # [STEP4] : add new DTI Scan instance(s) to XNAT    
            if 'DTI' in identifiedScanFiles.keys() :
                # DTI scan
                scanID = str(101)
                scanType = 'DTI'
                
                # if full pack, T1 and DTI scan --> modify the scanID accordingly
                if 'T1' in identifiedScanFiles.keys() : scanID = str(( int(scanID) * 2 ) - 1)
                
                dictScan = {}
                dictScan['xsiType'] = 'xnat:mrScanData'#byDefault_dataType
                dictScan['xnat:mrScanData/series_description'] = scanType
                dictScan['xnat:mrScanData/type'] = scanType
                dictScan['xnat:mrScanData/ID'] = scanID
                dictScan['xnat:mrScanData/modality'] = 'MR'#byDefault_modality
                #Assumption: if a scan has to be uploaded and created, data quality will probably be OK. Set to 'usable'
                dictScan['quality'] = 'usable'
                
                try: 
                    resp = XNAT.addScan(args['project'],subjectName,examName, scanID, dictScan)
                    if resp.status == 200 and args['verbose'] : print ' [Info] Scan %s created' %scanID
            
                except xnatLibrary.XNATException as xnatErr:
                    print ' [Warning] Issue creating Scan.\r\n   Reason:: %s' %xnatErr
                    
                # [STEP4.5] : upload NIfTI scan file to XNAT
                nii_file = os.path.join(identifiedScanFiles['root'],identifiedScanFiles['DTI'])
        
                fileExtension = (os.path.splitext(nii_file)[1]).lower()
                fileNameToUpload = scanID + '_' + scanType + fileExtension
                
                
                URL = XNAT.host + '/data/projects/'
                URL += args['project']
                URL += '/subjects/'
                URL += subjectName
                URL += '/experiments/'
                URL += examName
                URL += '/scans/'
                URL += scanID                
                nURL = URL + '/resources/NIFTI/files/'
                nURL += fileNameToUpload
                
                if XNAT.resourceExist(nURL).status == 200 :
                    print '[Warning] File with same name %s already exists in XNAT' %fileNameToUpload
    
                else:                            
                    opts_dict = { 'format': 'NIFTI', 'content': 'RAW' }            
                    #Convert the options to an encoded string suitable for the HTTP request
                    opts = urllib.urlencode(opts_dict)
                    resp = XNAT.putFile(nURL, nii_file, opts)
                    
                    if resp.status == 200 and args['verbose'] : print ' [Info] NIfTI scan file %s successfully uploaded' %fileNameToUpload 
                        
                # [STEP4.5] : upload NIfTI BVEC/BVAL scan files to XNAT
                if 'BVEC' in identifiedScanFiles.keys() :
                    bvec_file = os.path.join(identifiedScanFiles['root'],identifiedScanFiles['BVEC'])
        
                    fileExtension = (os.path.splitext(bvec_file)[1]).lower()
                    fileNameToUpload = scanID + '_' + scanType + fileExtension
                    
                    nURL = URL + '/resources/NIFTI/files/'
                    nURL += fileNameToUpload
                                        
                    if XNAT.resourceExist(nURL).status == 200 :
                        print '[Warning] File with same name %s already exists in XNAT' %fileNameToUpload
        
                    else:                            
                        opts_dict = { 'format': 'BVEC', 'content': 'RAW' }            
                        #Convert the options to an encoded string suitable for the HTTP request
                        opts = urllib.urlencode(opts_dict)
                        resp = XNAT.putFile(nURL, bvec_file, opts)
                        
                        if resp.status == 200 and args['verbose'] : print ' [Info] BVEC file %s successfully uploaded' %fileNameToUpload 
                
                if 'BVAL' in identifiedScanFiles.keys() :
                    bval_file = os.path.join(identifiedScanFiles['root'],identifiedScanFiles['BVAL'])
        
                    fileExtension = (os.path.splitext(bval_file)[1]).lower()
                    fileNameToUpload = scanID + '_' + scanType + fileExtension
                    
                    nURL = URL + '/resources/NIFTI/files/'
                    nURL += fileNameToUpload
                    
                    if XNAT.resourceExist(nURL).status == 200 :
                        print '[Warning] File with same name %s already exists in XNAT' %fileNameToUpload
        
                    else:                            
                        opts_dict = { 'format': 'BVAL', 'content': 'RAW' }            
                        #Convert the options to an encoded string suitable for the HTTP request
                        opts = urllib.urlencode(opts_dict)
                        resp = XNAT.putFile(nURL, bval_file, opts)
                        
                        if resp.status == 200 and args['verbose'] : print ' [Info] BVAL file %s successfully uploaded' %fileNameToUpload         
                
                
    return


###                                                    ###
#  top-level script environment                            #    
###                                                    ###

if __name__ == "__main__":
    print ''
    print '%s v%s - %s (%s)' %(os.path.basename(sys.argv[0]), __version__, __versionDate__, __author__)
    print ''
    #print 'nifti2xnat :: Parse and upload NIFTI data to XNAT archive, also checks for DTI files: .bvec and .bval'

    # argparse trickery
    parser = argparse.ArgumentParser(description='%s :: Humble attempt to upload NIFTI scan data (DTI bval/bvec included) to XNAT archive' %os.path.basename(sys.argv[0]))
    parser.add_argument('-H','--host', dest="hostname", help='XNAT hostname URL', required=True)
    parser.add_argument('-p','--proj', dest="project", help='XNAT project ID', required=True)
    parser.add_argument('-u','--user', dest="username", help='XNAT username (will be prompted for password)', required=True)
    parser.add_argument('-i','--input', dest="input", help='Location of input NIFTI data', required=True)    
    parser.add_argument('-v','--verbose', dest="verbose", action='store_true', default=False, help='Display verbosal information about outputs retrieved (optional)', required=False)
    #parser.add_argument('-l','--list', dest="list", action='store_true', default=False, help='Do not download anything but just list all matched cases', required=False)
    args = vars(parser.parse_args())
    
    # check validity of input directory provided
    if not os.path.exists(args['input']) :
        raise Exception('[Error] Input directory '"'%s'"' not found' %args['input'])
    
    # compose the HTTP basic authentication credentials string
    password = getpass.getpass('Password for user %s:' %args['username'])
    usr_pwd = args['username']+':'+password
    print ''
    
    try:         
        # connect to XNAT
        with xnatLibrary.XNAT(args['hostname'],usr_pwd) as XNAT :
            if args['verbose'] : print ' [Info] session %s opened' %XNAT.jsession
            
            # check if XNAT project exists
            if XNAT.resourceExist('%s/data/projects/%s' %(XNAT.host,args['project'])).status != 200 :
                raise xnatLibrary.XNATException('project ("%s") is unreachable at: %s' % (args['project'], XNAT.host) )
            
            # if all went OK, proceed to the main processing stage
            main(XNAT,args)    
            
            # disconnect from XNAT
            if args['verbose'] : print ' [Info] session %s closed' %XNAT.jsession
        
    except xnatLibrary.XNATException as xnatErr:
        print ' [Error] XNAT-related issue:', xnatErr

    except Exception as e:
        print '[Error]', e    
        print(traceback.format_exc())