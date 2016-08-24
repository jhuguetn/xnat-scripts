#!/usr/bin/python

# Created 2014-09-26, Jordi Huguet, Dept. Radiology AMC Amsterdam

####################################
__author__      = 'Jordi Huguet'  ##
__dateCreated__ = '20140926'      ##
__version__     = '0.2'           ##
__versionDate__ = '20151209'      ##
####################################

# projectCleanUp.py (based on old legacy script: bulkRemoval.py)
# Script for deleting MR sessions and derived data for a given XNAT project
#
# TO DO:
# - Selective removal: input CSV file with list of experiment IDs (or subjects?) to be selectively removed
# - ...

import xnatLibrary

import subprocess as sub
import os
import sys
import getpass
import argparse
import urllib
#import json
import csv
import datetime

def utils_csv_parser(filename, indexLabel):
    '''Walk-through a CSV file and parse its values, resilient to different delimiters , and ;'''    
    '''Returns a list with all the session IDs'''
    
    with open(filename, 'rb') as csvfile:
        dialect = csv.Sniffer().sniff(csvfile.read(), delimiters=';,')
        csvfile.seek(0)
        reader = csv.reader(csvfile, dialect)
        
        csvList = list(reader)
        mIndex = csvList[0].index(indexLabel)
        csvList.pop(0)
        sessionList = []
        for line in csvList:
            sessionList.append(line[mIndex])            
        
        return sessionList
    
def deleteReconstruction(XNAT, experimentID, reconstructionID, removeFiles=True):
    '''Delete an experiment reconstruction'''
        
    #compose the URL for the REST call
    URL = XNAT.host + '/data/experiments/%s/reconstructions/%s' %(experimentID, reconstructionID)
    
    opts = None    
    if removeFiles == True :
        opts = urllib.urlencode({ 'removeFiles': 'true' })
        
    response = XNAT.deleteURL(URL,opts)
    
    responseOutput = False
    if response.status == 200 :
        responseOutput = True
        
    return responseOutput

def deleteSession(XNAT,project,subject,experimentID, removeFiles=True):
    '''Delete an XNAT Session'''
    
    #compose the URL for the REST call
    URL = XNAT.host + '/data/archive/projects/%s/' % project
    URL += 'subjects/%s/' % subject
    URL += 'experiments/%s' % experimentID
    
    opts = None    
    if removeFiles == True :
        opts = urllib.urlencode({ 'removeFiles': 'true' })
    
    response = XNAT.deleteURL(URL,opts)
    
    responseOutput = False
    if response.status == 200 :
        responseOutput = True
    
    return responseOutput    

def deleteSubject(XNAT, project,subject,removeFiles=True):
    '''Delete an XNAT Subject'''
    
    #compose the URL for the REST call
    URL = XNAT.host + '/data/archive/projects/%s/' % project
    URL += 'subjects/%s/' % subject
    
    opts = None    
    if removeFiles == True :
        opts = urllib.urlencode({ 'removeFiles': 'true' })        
    
    response = XNAT.deleteURL(URL,opts)
    
    responseOutput = False
    if response.status == 200 :
        responseOutput = True
    
    return responseOutput
    
def deleteData(XNAT, projectDict, keepOriginalFlag, daysPreserved=None):    
    '''Specific script for cleaning up a project from data entities contained'''
    '''Recurs over projects/subjects/experiments/reconstructions and all matched entities are deleted'''
    
    # flagForRemovingDataFilesPermanently
    remFilesFlag = True
    
    if daysPreserved :
        now = datetime.datetime.now()
        dateThresh = now - datetime.timedelta(days=int(daysPreserved))
        if args['verbose'] :
            dateThreshStr = str("{:%H:%M %d %B %Y}".format(dateThresh))
            print '[Debug] Removing imaging sessions and/or subjects older than: %s' %dateThreshStr
    
    for project in projectDict.keys() :
        if args['verbose'] : print '[Debug] Project %s :' % project
        subjectDict = XNAT.getSubjects(project)            
        
        for subject in subjectDict.keys() :
            #if args['verbose'] : print '[Debug] - Subject %s :' % subjectDict[subject]['label']
            imgDict = XNAT.getMRSessionsBySubj( project, subject, { 'xsiType': 'xnat:imageSessionData' } ) #get ALL types of imaging sessions, not only MRs
            
            for session in imgDict.keys() :
                if daysPreserved :
                    insert_date = datetime.datetime.strptime(imgDict[session]['insert_date'], "%Y-%m-%d %H:%M:%S.%f")
                    if dateThresh <= insert_date : # meaning inserted in an newer -or equal- than specified threshold date 
                        imgDict.pop(session)                    
                        
            for session in imgDict.keys() :            
                reconDict = XNAT.getReconstructions(session)
                if reconDict != None :
                    for reconstruction in reconDict.keys() :
                        delResp = deleteReconstruction(XNAT, session, reconstruction, remFilesFlag)
                        if args['verbose'] and delResp : print '[Debug]   + Reconstruction %s from Session %s --> deleted' % (reconDict[reconstruction]['ID'],imgDict[session]['label'])
                        
                if not keepOriginalFlag :
                    delResp = deleteSession(XNAT,project,subjectDict[subject]['ID'],session, remFilesFlag)
                    if args['verbose'] and delResp : print '[Debug]  + Session %s --> deleted' % imgDict[session]['label']                                    
                                            
                    
            if ((not keepOriginalFlag) and (len(imgDict) == 0)) :
                if daysPreserved :
                    insert_date = datetime.datetime.strptime(subjectDict[subject]['insert_date'], "%Y-%m-%d %H:%M:%S.%f")
                    if dateThresh > insert_date : # meaning inserted in an older than specified threshold date 
                        delResp = deleteSubject(XNAT,project,subject, remFilesFlag)
                        if args['verbose'] and delResp : print '[Debug] + Subject %s --> deleted' % subjectDict[subject]['label']                                    
                else :
                    delResp = deleteSubject(XNAT,project,subject, remFilesFlag)
                    if args['verbose'] and delResp : print '[Debug] + Subject %s --> deleted' % subjectDict[subject]['label']                                    
                        
                
def main(XNAT,args):    
    '''Query data tree'''
    
    #subjectList = utils_csv_parser(args['csvFile'], 'Subject')
    projectDict = {}
    projectDict = XNAT.getSingleProject(args['project'])
    
    if args['daysPreserved'] :
        deleteData(XNAT,projectDict,args['keepOriginal'], args['daysPreserved'])
    else : 
        deleteData(XNAT,projectDict,args['keepOriginal'])

    return

###                                                    ###
# Top-level script environment                           #
###                                                    ###

if __name__=="__main__" :
    print ''
    
    # argparse trickery
    parser = argparse.ArgumentParser(description='%s :: Clean up an XNAT project by deleting contained data' %os.path.basename(sys.argv[0]))
    parser.add_argument('-H','--host', dest="hostname", help='XNAT hostname URL', required=True)
    parser.add_argument('-p','--proj', dest="project", help='XNAT project ID', required=True)
    parser.add_argument('-u','--user', dest="username", help='XNAT username (will be prompted for password)', required=True)
    parser.add_argument('-pwd','--password', dest="password", help='XNAT password (optional)', required=False)
    parser.add_argument('-dp','--daysPreserved', dest="daysPreserved", help='Any data element created before specified number of days -counting from now- will be removed (optional)', required=False)
    #parser.add_argument('-f','--csvFile', dest="csvFile", help='CSV file with specific list of subjects, if not present ALL matching cases will be cleaned (optional)', required=False)    
    parser.add_argument('-k','--keepOriginal', dest="keepOriginal", action='store_true', default=False, help='Keep original imaging data and solely remove derived data, otherwise all project\'s data will be deleted (optional)', required=False)
    parser.add_argument('-v','--verbose', dest="verbose", action='store_true', default=False, help='Display verbosal information(optional)', required=False)
    
    args = vars(parser.parse_args())
    
    # compose the HTTP basic authentication credentials string
    if args['password'] is None :
        password = getpass.getpass('Password for user %s:' %args['username'])
    else :
        password = args['password']
    
    usr_pwd = args['username']+':'+password
    print ''
    
    try:         
        #if args['csvFile'] is not None and not os.path.isfile(args['csvFile']) :
        #    raise Exception('CSV file %s not found' %args['csvFile'])
    
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
        print ' [Error] Unexpected issue:', e        
    