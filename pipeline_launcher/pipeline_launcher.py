#!/usr/bin/env python

# Created  2014-11-25, Jordi Huguet, Dept. Radiology AMC Amsterdam
# Modified 2018-02-28, Jordi Huguet, BarcelonaBeta Brain Research Centre

####################################
__author__      = 'Jordi Huguet'  ##
__dateCreated__ = '20141125'      ##
__version__     = '1.2.1'         ##
__versionDate__ = '20180228'      ##
####################################

# pipeline_launcher.py
# Script for triggering XNAT pipeline jobs (batch mode)
#

import os
import sys
import getpass
import argparse
import xnatLibrary
import datetime
import csv
import time
import xml.etree.ElementTree as etree


def get_project_archive_spec(xnat_connection, project):
    ''' Given a project, get extended archive-related information '''    
    '''Returns an xml object '''
    
    #compose the URL for the REST call
    URL = xnat_connection.host + '/data/projects/%s/archive_spec' %project
    #do the HTTP query to get the remote XML resource
    proj_arch_info_xml,_ = xnat_connection.getResource(URL)    
    
    return proj_arch_info_xml

    
def get_pipeline_alias(xnat_connection,project_name,pipeline_name):
    ''' Get project's archive_spec metainfo from XNAT and parse the project's available pipeline names VERSUS stepIds'''    
    '''Returns a pipeline stepId (pipeline runnable alias) for the given pipeline identified by pipeline_name '''
    
    # get the project archive-specs as an XML object
    xml_output = get_project_archive_spec(xnat_connection, project_name)
    
    #parse the output results as an XML object
    xml_object = etree.fromstring(xml_output)
    namespace = { 'archive' : 'http://nrg.wustl.edu/arc' }
    
    # traverse XML subelements named 'pipeline' and fetch pipeline names VS stepId attribute 
    # XNAT Pipeline Engine uses the later as actual names/ids for launching a pipeline programatically
    pipeline_list = xml_object.findall('archive:pipelines/archive:descendants/archive:descendant/archive:pipeline', namespace)
    pipeline_aliases = {(item.find('archive:name',namespace)).text : item.attrib['stepId'] for item in pipeline_list}
    
    return pipeline_aliases[pipeline_name]


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
    
    parser = argparse.ArgumentParser(description='%(prog)s :: Launch a processing pipeline over a set of XNAT experiments (batch mode)')
    parser.add_argument('-H','--host', dest="hostname", help='Full XNAT URL (e.g. https://myHostname.url/xnat)', required=True)
    parser.add_argument('-u','--user', dest="username", help='XNAT username (will be prompted for password)', required=True)
    parser.add_argument('-pr','--project', dest="project", help='XNAT project ID', required=True)
    parser.add_argument('-pi','--pipeline', dest="pipeline", help="Pipeline name to be executed", required=True)
    parser.add_argument('-i','--inputCSV', dest="input_csv", help="Expermient list (CSV file)", required=True)
    parser.add_argument('-v','--verbose', dest="verbose", action='store_true', default=False, help='Display verbosal information(optional)', required=False)
    parser.add_argument('--version', action='version', version='%(prog)s v{}'.format(__version__))
    
    args = vars(parser.parse_args())
    
    #Waiting time between each pipeline job is launched not to overstress the system when many jobs are triggered at once
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
        with xnatLibrary.XNAT(args['hostname'],usr_pwd) as xnat_connection :
            if args['verbose'] : print '[Info] session opened (%s)' %xnat_connection.host
            
            projects = xnat_connection.getProjects()
            if args['project'] not in projects.keys() :
                raise Exception('Project %s not found or unaccessible' %args['project'])
            
            pipelines = xnat_connection.getProjectPipelines(args['project'])                
            if args['pipeline'] not in pipelines.keys() :
                raise Exception('Pipeline %s not found or unaccessible in the given context (project: %s)' %(args['pipeline'],args['project']))
                
            # get the valid pipeline name alias (stepID) for properly launching the pipeline via REST API call
            # rationale: When a project's pipeline is configured to auto-launch, its ID is replaced automagically by an awkward alias (stepID)
            pipeline_alias = get_pipeline_alias(xnat_connection, args['project'], args['pipeline'])
            
            sessionList = csv_parser(args['input_csv'])
            i = 0
            for session in sessionList :
                i += 1
                sURL = xnat_connection.host + '/data/archive/experiments/' + session
                if xnat_connection.resourceExist(sURL).status == 200 :
                    #response = xnat_connection.launchPipeline(args['project'], session, args['pipeline'])
                    response = xnat_connection.launchPipeline(args['project'], session, pipeline_alias)
                    time.sleep(sleep_timespan)
                    #if i%1 == 0 :
                    #    time.sleep(sleep_timespan)
                    
                else :
                    if args['verbose'] : print '[Warning] XNAT image session #"%s" not found' %session                                                    
                        
            if args['verbose'] : print '[Info] session closed (%s)' %xnat_connection.host
    
    except xnatLibrary.XNATException as xnatErr:
        print ' [Error] XNAT-related issue:', xnatErr
    except Exception as anyErr:
        print ' [Error] ', anyErr

