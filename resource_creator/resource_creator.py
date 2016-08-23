#!/usr/bin/python

# Created 2016-08-16, Jordi Huguet, Dept. Radiology AMC Amsterdam

####################################
__author__      = 'Jordi Huguet'  ##
__dateCreated__ = '20160816'      ##
__version__     = '0.1.2'         ##
__versionDate__ = '20160823'      ##
####################################

# resource_creator.py
# Tools for the creation of XNAT resources

# TO DO:
# - Include meta-information attributes (resource file/collection Format & Content) when used in script-mode

# IMPORT FUNCTIONS
import os
import sys
import urllib
import zipfile
import xnatLibrary
import re
import getpass
import contextlib
import argparse
import traceback
import datetime
import tempfile
import shutil


# CLASSES
# class Entity():
    # ''' Class defining the structure of an XNAT entity, understanding a entity as an element of the set {project,subject,experiment}'''
    
    # def __init__(self, type=None, identifier=None):
        # self.type = type
        # self.id = identifier


# class RC_metainfo():
    # ''' Class defining the attributes of Resource Collection metainformation (metadata)'''
    
    # def __init__(self, format=None, content=None):
        # self.format = format
        # self.content = content        
        
        
# FUNCTIONS
def create_resource_collection(connection,entity_type,entity_name,label,meta_rcFormat=None,meta_rcContent=None,force_create=False):
    '''Create a entity-related resource collection (RC) for hosting data, understanding a entity as an element of the set {project,subject,experiment}'''
    '''Returns the xnat_abstractresource_id of the created resource if successful'''    
    
    #Compose the root-entity URL
    root_entity_URL = connection.host + '/data/%s/%s' %(entity_type,entity_name)
    
    #Verify root entity exists in XNAT (security check)
    if connection.resourceExist(root_entity_URL).status != 200 :
        raise xnatLibrary.XNATException('No %s with ID "%s" reachable at: %s' % (entity_type, entity_name, connection.host) )
    
    #Compose the resource collection URL
    URL = root_entity_URL + '/resources/%s' %label
    
    #Verify if resource collection already exists OR there's an Internal Server Error (Subject entities REST API inconsistency)
    if connection.resourceExist(URL).status in [200, 500] :
        if force_create : 
            raise xnatLibrary.XNATException('A %s-based Resource Collection with such name (%s) already exists in the current context' %(entity_type,label))
        else : 
            print '[Warning] A %s-based Resource Collection with such name (%s) already exists in the current context' %(entity_type,label)            
    
    #Otherwise, lets create it!        
    else:
        #When present, encode meta-information attributes (i.e. Resource Collection format and content) for the HTTP PUT request
        opts = None
        opts_dict = {}
        if meta_rcFormat : 
            opts_dict.update({'format': meta_rcFormat.upper()})
        if meta_rcContent : 
            opts_dict.update({'content': meta_rcContent})
        
        if opts_dict :
            opts = urllib.urlencode(opts_dict)
        
        #Create the resource collection
        response,_ = connection.putURL(URL, opts)
        
        if response.status == 200 : 
            if args['verbose'] : print '[Info] Resource collection "%s" successfully created' %label
    
    #Verify it was created and get the xnat_abstractresource_id 
    resources_set = get_resources(connection, entity_type, entity_name)
    matched_res = [resources_set[current_resource] for current_resource in resources_set if resources_set[current_resource]['label'] == label]
    assert(len(matched_res) == 1)
    
    return matched_res[0]['xnat_abstractresource_id']


def add_resource_file(connection,entity_type,entity_name,resource_filepath,resource_collection=None,meta_rFormat=None,meta_rContent=None,extract_dir=False):
    '''Upload an entity-related file resource, understanding a entity as an element of the set {project,subject,experiment}'''
    '''If 'resource_collection' is not specified, XNAT will create a 'NO LABEL' one or use an already existing one'''
    '''Field 'resource_collection' accepts both a label or a unique id (xnat_abstractresource_id)'''
    '''If meta-information attribute meta_rFormat is not set, function will attempt to pull it out from the filename by isolating the file extension'''
    '''Returns an HTTP response object'''    
    
    #Compose the root URL for the REST call
    root_entity_URL = connection.host + '/data/%s/%s' %(entity_type,entity_name)
    if resource_collection :
        root_entity_URL += '/resources/%s' %resource_collection
   
    #Check if root entity exists
    if connection.resourceExist(root_entity_URL).status not in [200, 500] :
        raise xnatLibrary.XNATException('Resource %s is not reachable' %root_entity_URL )
    
    if not os.path.exists(resource_filepath) :
        raise ValueError('"%s" is not a valid path in the file system' %resource_filepath )
    if not os.path.isfile(resource_filepath) :
        raise ValueError('"%s" is not a file' %resource_filepath )
    
    resource_basename = os.path.basename(resource_filepath)
    _,resource_extension = os.path.splitext(resource_basename)
    resource_extension = resource_extension[1:]
    resource_basename = normalize_name(resource_basename)
    
    URL = root_entity_URL + '/files/%s' %resource_basename
        
    #Check if resource file already exists or there's an Internal Server Error (subjects REST API inconsistency)
    if connection.resourceExist(URL).status == 200 :
        raise xnatLibrary.XNATException('A %s-based Resource file with such name (%s) already exists in the current context' %(entity_type,resource_basename))
    #Otherwise, lets upload it!
    
    #If present, encode metainformation attributes (i.e. Resource Collection format and content) for the HTTP PUT request
    opts = None
    opts_dict = {}
    if meta_rFormat : 
        opts_dict.update({'format': meta_rFormat.upper()})
    elif resource_extension and not extract_dir :
        opts_dict.update({'format': resource_extension.upper()})        
    if meta_rContent : 
        opts_dict.update({'content': meta_rContent})
    if extract_dir :
        opts_dict.update({'extract': 'true'})
        
    if opts_dict :
        opts = urllib.urlencode(opts_dict)
    
    response = connection.putFile(URL, resource_filepath, opts)
    
    if response.status == 200 : 
        if args['verbose'] :
            print '[Info] Resource "%s" successfully uploaded' %resource_basename
            
    return response
    
    
def get_resources(connection, entity_type, entity_name):
    '''Helper: Query for resource collections given an entity'''
    '''Returns a dictionary with all resource collections found'''
    
    #compose the URL for the REST call
    URL = connection.host + '/data/%s/%s/resources' %(entity_type, entity_name)
    
    resultSet,_ = connection.queryURL(URL)    
        
    #parse the results out  
    resourceDict = {}    
    for record in resultSet :
        resourceDict[record['xnat_abstractresource_id']] = record        
    
    return resourceDict


def normalize_name(name_string):
    '''Helper: Replace awkward chars for underscores'''
    '''Returns a normalized name string'''
    
    name_string  = re.sub(r'/^([!#$&-;=?-[]_a-z~]|%[0-9a-fA-F]{2})+$/',' ', name_string)
    name_string = name_string.replace(" ", "_")
    
    return name_string
        

def zipdir(input_dir, zip_filename):
    '''Helper: Zip-compress a whole directory'''
    '''Returns a dictionary with all resource collections found'''

    with contextlib.closing(zipfile.ZipFile(zip_filename, "w", zipfile.ZIP_DEFLATED)) as z:
        for root, dirs, files in os.walk(input_dir):
            #NOTE: ignore empty directories
            for filename in files:
                abs_filepath = os.path.join(root, filename)
                relative_filepath = abs_filepath[len(input_dir)+len(os.sep):] #relative path!
                z.write(abs_filepath, relative_filepath)
    
    return zip_filename
    
    
@contextlib.contextmanager
def make_temp_directory():
    '''Helper: Automatically creates a temporary directory. The contextmanager decorator allows defining as factory function '''
    '''As decorated function, it can be bound in a 'with' statement as clause. Exceptions from the with block are handled there '''
    
    temp_dir = tempfile.mkdtemp()
    try:
        yield temp_dir
    finally:
        shutil.rmtree(temp_dir)
        
        
def main (connection,args):    
    
    if os.path.isfile(args['input']):
        # case: resource file upload
        if args['resource_collection'] :
            rc_name = args['resource_collection']
        else :
            print '[Warning] No resource collection specified, archiving "%s" under UNSPECIFIED resource collection' %args['input']
            rc_name = 'UNSPECIFIED'
        
        rc_id = create_resource_collection(connection,args['e_type'],args['e_name'],rc_name,force_create=False)#,meta_rcFormat=None,meta_rcContent=None)
        add_resource_file(connection,args['e_type'],args['e_name'],args['input'],str(rc_id))#,meta_rFormat=None,meta_rContent=None)
        
    elif os.path.isdir(args['input']):
        # case: directory (or set of files) batch upload
        if args['resource_collection'] :
            rc_name = args['resource_collection']
        else :
            print '[Warning] No resource collection specified, archiving "%s" under its root directory name: %s' %(args['input'],os.path.basename(args['input']))
            rc_name = normalize_name(os.path.basename(args['input']))
        
        # Force the creation of the resource collection, otherwise may be reusing an existing one and resource files might be overwrote
        rc_id = create_resource_collection(connection,args['e_type'],args['e_name'],rc_name,force_create=True)#,meta_rcFormat=None,meta_rcContent=None)
        
        # Compress directory content
        with make_temp_directory() as temp_dir:
            # Create a temporary directory and filename
            temp_name = normalize_name(os.path.basename(args['input']))
            temp_zipfile = os.path.join(temp_dir,temp_name)
            # ZIP-compress all data to the temporary file 
            zipdir(args['input'], temp_zipfile)
            add_resource_file(connection,args['e_type'],args['e_name'],temp_zipfile,str(rc_id),extract_dir=True)#,meta_rFormat=None,meta_rContent=None)
    
    
###                                                        ###
#           top-level script environment                     #
###                                                        ###

if __name__=="__main__" :
    print ''
    
    # argparse trickery
    parser = argparse.ArgumentParser(description='%s :: Create and uploads additional resource files into XNAT' %os.path.basename(sys.argv[0]))
    parser.add_argument('-H','--host', dest="hostname", help='XNAT hostname URL (e.g. https://3tmri.nl/xnat)', required=True)
    parser.add_argument('-u','--user', dest="username", help='XNAT username (will be prompted for password)', required=True)
    parser.add_argument('-t','--type', dest="e_type", help='Entity type/level where to create resource; can either be: {projects,subjects,experiments}', required=True)
    parser.add_argument('-id','--identifier', dest="e_name", help='Entity name/identifier where to create resource', required=True)
    parser.add_argument('-i','--input', dest="input", help='Input file/directory location', required=True)    
    parser.add_argument('-rc','--resource_collection', dest="resource_collection", default=None, help='Resource collection name (optional)', required=False)
    parser.add_argument('-v','--verbose', dest="verbose", action='store_true', default=False, help='Display verbosal information (optional)', required=False)
    
    args = vars(parser.parse_args())
    
    # compose the HTTP basic authentication credentials string
    password = getpass.getpass('Password for user %s:' %args['username'])
    usr_pwd = args['username']+':'+password
    print ''
    
    try:         
        # connect to XNAT
        with xnatLibrary.XNAT(args['hostname'],usr_pwd) as xnat_connection :
            if args['verbose'] : print '[Info] session %s opened' %xnat_connection.jsession
            
            main(xnat_connection,args)    
            
            if args['verbose'] : print '[Info] session %s closed' %xnat_connection.jsession
            # disconnect from XNAT
        
    except xnatLibrary.XNATException as xnatErr:
        print '[Error] XNAT-related issue:', xnatErr        
        sys.exit(1)
    
    except Exception as e:
        print '[Error]', e    
        print(traceback.format_exc())
        sys.exit(1)
        
    sys.exit(0)

