#!/usr/bin/python

# Created 2014-11-25, Jordi Huguet, Dept. Radiology AMC Amsterdam

####################################
__author__      = 'Jordi Huguet'  ##
__dateCreated__ = '20141125'      ##
__version__     = '1.1'           ##
__versionDate__ = '20160621'      ##
####################################

# pipeline_launcher.py
# Script for triggering XNAT pipeline jobs (batch mode)
#
# TO DO:
# - ...
# - 

import os
import sys
import getpass
import argparse
import xnatLibrary
import datetime
import csv
import time


def csv_parser(filename, header=None):
    '''Walk-through a CSV file and parse its values, resilient to different delimiters , and ;'''    
    '''By default use 'Session' as header (session unique ID)'''
    '''Returns a list with all the column values based on header ID'''
    
    # By-default column header is Session (image session UID or accession number)
    if not header :
        header = 'Session'
    
    sessionList = []
    with open(filename, 'rb') as csvfile:
        dialect = csv.Sniffer().sniff(csvfile.read(), delimiters=';,')
        csvfile.seek(0)
        reader = csv.reader(csvfile, dialect)
        
        csvList = list(reader)
        mIndex = csvList[0].index(header)
        csvList.pop(0)
        
        for line in csvList:
            sessionList.append(line[mIndex])            
        
    return sessionList

    
###                                                    ###
# Top-level script environment                           #
###                                                    ###

if __name__=="__main__" :
    print ''
    
    parser = argparse.ArgumentParser(description='%s :: Parse data from an OpenClinica CRF XML object and populate XNAT datatyped instances of that CRF' %os.path.basename(sys.argv[0]))
    parser.add_argument('-H','--host', dest="hostname", help='full XNAT URL (e.g. https://myHost.url/xnat)', required=True)
    parser.add_argument('-u','--user', dest="username", help='XNAT username (will be prompted for password)', required=True)
    parser.add_argument('-pr','--project', dest="project", help='XNAT project ID', required=True)
    parser.add_argument("-pi","--pipeline", dest="pipeline", help="Datatype ID in XNAT", required=True)
    parser.add_argument("-i","--inputCSV", dest="input_csv", help="expermient list CSV file", required=True)
    parser.add_argument('-v','--verbose', dest="verbose", action='store_true', default=False, help='Display verbosal information(optional)', required=False)
    
    args = vars(parser.parse_args())
    
    #Waiting time between each pipeline is launched not to overstress the system when many jobs are triggered
    #sleep_timespan = 1800 #set to 1/2 hour
    sleep_timespan = 300 #set to 5 mins.
    
    # compose the HTTP basic authentication credentials string
    password = getpass.getpass('Password for user %s:' %args['username'])
    usr_pwd = args['username']+':'+password
    print ''
        
    if not os.path.isfile(args['input_csv']) :
        raise Exception('CSV file %s not found' %args['input_csv'])
    
    try:         
        # connect to XNAT
        with xnatLibrary.XNAT(args['hostname'],usr_pwd) as XNAT :
            if args['verbose'] : print '[Info] session %s opened' %XNAT.jsession
            
            projects = XNAT.getProjects()
            if args['project'] not in projects.keys() :
                raise Exception('Project %s not found or unaccessible' %args['project'])
            
            pipelines = XNAT.getProjectPipelines(args['project'])                
            if args['pipeline'] not in pipelines.keys() :
                raise Exception('Pipeline %s not found or unaccessible in the given context (project: %s)' %(args['pipeline'],args['project']))
                
            sessionList = csv_parser(args['input_csv'])
            i = 0
            for session in sessionList :
                i += 1
                sURL = XNAT.host + '/data/archive/experiments/' + session
                if XNAT.resourceExist(sURL).status == 200 :
                    response = XNAT.launchPipeline(args['project'], session, args['pipeline'])
                    time.sleep(sleep_timespan)
                    #if i%1 == 0 :
                    #    time.sleep(sleep_timespan)
                    
                else :
                    if args['verbose'] : print '[Warning] XNAT image session #"%s" not found' %session                                                    
                        
            if args['verbose'] : print '[Info] session %s closed' %XNAT.jsession
    
    except xnatLibrary.XNATException as xnatErr:
        print ' [Error] XNAT-related issue:', xnatErr
    except Exception as anyErr:
        print ' [Error] ', anyErr