#resource_creator

##Introduction
This script contains basic methods for the creation of resources in XNAT. Python 2.7.X is a prerequisite  for running the script. 

XNAT is a data management system for research-oriented imaging data, more info [here](https://www.xnat.org/). File resources can be attached to different XNAT entities to link file-based data to them.

##Installation procedure

Get the lattest version of the scripts as follows: 
  ```
  git clone https://github.com/jhuguetn/xnat-scripts.git scripts
  ```

## Running the script:
  ```
  python scripts/resource_creator/resource_creator.py {...}
  ```

usage: resource_creator.py [-h] -H HOSTNAME -u USERNAME -t E_TYPE -id E_NAME
                           -i INPUT [-rc RESOURCE_COLLECTION] [-v]

resource_creator.py :: Create and uploads additional resource files into XNAT

optional arguments:
  -h, --help            show this help message and exit
  -H HOSTNAME, --host HOSTNAME
                        XNAT hostname URL (e.g. https://3tmri.nl/xnat)
  -u USERNAME, --user USERNAME
                        XNAT username (will be prompted for password)
  -t E_TYPE, --type E_TYPE
                        Entity type/level where to create resource; can either
                        be: {projects,subjects,experiments}
  -id E_NAME, --identifier E_NAME
                        Entity name/identifier where to create resource
  -i INPUT, --input INPUT
                        Input file/directory location
  -rc RESOURCE_COLLECTION, --resource_collection RESOURCE_COLLECTION
                        Resource collection name (optional)
  -v, --verbose         Display verbosal information (optional)


##Questions/Comments?

Submit an issue, fork and/or PR. Alternatively, reach me at j.huguet(at)amc.uva.nl
