#!/usr/bin/python

# Created 2016-05-10, Jordi Huguet, Dept. Radiology AMC Amsterdam

####################################
__author__      = 'Jordi Huguet'  ##
__dateCreated__ = '20160510'      ##
__version__     = '0.1.0'         ##
__versionDate__ = '20161101'      ##
####################################

# xnatDownloader
# Download all data from XNAT (batch-mode)
# A humble attempt to temporarily replace the functionality of the downloader Java applet 

import os
import sys
import getpass
import argparse
import traceback
import urllib
import zipfile
import xnatLibrary


# FUNCTIONS
def get_mrsession_list(xnatURL, project):
    ''' Helper. Get list of MRi sessions '''
    
    query_options = {}
    query_options['xsiType'] = 'xnat:mrSessionData'
    query_options['format'] = 'json'
    query_options['columns'] = 'subject_label,label'
    query_options = urllib.urlencode(query_options)
    
    URL = amcXNAT.normalizeURL(xnatURL) + '/data/projects/%s/experiments' % project
    
    experiments,response = amcXNAT.queryURL(URL, query_options)
    
    return experiments
    
    
def get_resource_zip(xnatURL, experimentUID, resource_type, output_location, scan_list=None):
    ''' Helper. Download MRi session resources '''
    
    if not resource_type in ['scans', 'reconstructions'] :
        raise Exception('Wrong or unexpected resource type ("%s")' %resource_type)
    
    if scan_list is None :
        scan_list = ['ALL'] 
    elif len(scan_list) == 0 :
        return
        
    scan_list_str = ','.join(scan_list)
    query_options = {}
    query_options['format'] = 'zip'
    query_options = urllib.urlencode(query_options)
    
    URL = amcXNAT.normalizeURL(xnatURL) + '/data/experiments/%s/%s/%s/files' % (experimentUID,resource_type,scan_list_str)
    output, response = amcXNAT.getResource(URL, query_options)
    
    try:
        tmpFile = os.tmpfile()
    
        tmpFile.write(output)
        zipfile.ZipFile(tmpFile, 'r').extractall(output_location)
    
    except Exception as e:
       raise e 
    finally:
        # Always close the temporary file object created for retrieving ZIP data
        tmpFile.close()        
    
    return
   
    
###                                                    ###
#       top-level script environment                   #
###                                                    ###
if __name__ == "__main__":
    
    # argparse trickery
    parser = argparse.ArgumentParser(description='%s : retrieve project resources from XNAT (batch-mode)' %os.path.basename(sys.argv[0]))
    parser.add_argument('-H','--host', dest="hostname", help='XNAT hostname URL (e.g. https://3tmri.nl/xnat)', required=True)
    parser.add_argument('-p','--proj', dest="project", help='XNAT project ID', required=True)
    parser.add_argument('-u','--user', dest="username", help='XNAT username (will be prompted for password)', required=True)
    parser.add_argument('-o','--outdir', dest="outdir", help='Output directory where to store downloaded data', required=True)    
    parser.add_argument('-r','--recons', dest="recons", action='store_true', default=False, help='Download reconstructed/derived data (optional)', required=False)        
    parser.add_argument('-s','--scans', dest="scans", action='store_true', default=False, help='Download scanned/raw data (optional)', required=False)
    parser.add_argument('-f','--filter', dest="filter", help='Filter out scans by type', required=False)
    parser.add_argument('-fp','--rich_filepath', dest="rich_filepath", action='store_true', default=False, help='Include subject in file paths', required=False)
    parser.add_argument('-v','--verbose', dest="verbose", action='store_true', default=False, help='Display verbosal information (optional)', required=False)
    
    args = vars(parser.parse_args())
    
    # compose the HTTP basic authentication credentials string
    password = getpass.getpass('Password for user %s:' %args['username'])
    usr_pwd = args['username']+':'+password
    print ''
    
    try:         
        
        if not args['recons'] and not args['scans']:
            sys.exit(0)
        
        # check validity of output directory provided
        if not os.path.exists(args['outdir']) :
            raise Exception('Output directory ("%s") not found' %args['outdir'])
            
        with xnatLibrary.XNAT(args['hostname'],usr_pwd) as amcXNAT :
            if args['verbose']:
                print '[Info] XNAT session %s opened' %amcXNAT.jsession
            
            # get list of experiments
            experiments = get_mrsession_list(args['hostname'], args['project'])
            
            for expt in experiments:
                
                working_dir = args['outdir']
                if args['rich_filepath'] :               
                    working_dir = os.path.join(args['outdir'], expt['subject_label'])
                    if not os.path.exists(working_dir):
                        os.makedirs(working_dir)
                
                if args['scans'] :
                    try:
                        scans_list = None
                        if args['filter'] :
                            scans_list = []
                            scans_data = amcXNAT.getScans(expt['xnat:mrsessiondata/id'])
                            for scan in scans_data :
                                if args['filter'].lower() in scans_data[scan]['type'].lower() :
                                    scans_list.append(scan) 
                        get_resource_zip(args['hostname'], expt['xnat:mrsessiondata/id'], 'scans', working_dir, scans_list)
                    except xnatLibrary.XNATException as xnatErr:
                        print '[Warning] XNAT-related issue at retrieving scan resource files for %s. %s' %(expt['label'],xnatErr)  
                if args['recons'] :
                    try:
                        get_resource_zip(args['hostname'], expt['xnat:mrsessiondata/id'], 'reconstructions', working_dir)
                    except xnatLibrary.XNATException as xnatErr:
                        print '[Warning] XNAT-related issue at retrieving reconstruction resource files for %s. %s' %(expt['label'],xnatErr)  
                
            if args['verbose']:
                print '[Info] XNAT session %s closed' %amcXNAT.jsession
    
    except xnatLibrary.XNATException as xnatErr:
        print '[Error] XNAT-related issue:', xnatErr        
    
    except Exception as e:
        print '[Error]', e    
        print(traceback.format_exc())
            
    