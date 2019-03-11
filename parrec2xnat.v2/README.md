# parrec2xnat

## Introduction 

Python tool for importing PAR/REC formatted input data to XNAT as an additional compatible input format, including as many relevant metadata as possible in the process. Automates the usage of REST calls to push data and create the proper metadata infrastructure (equivalent to automated DICOM import).

## Installation procedure

Get the lattest version of the scripts as follows: 
  ```
  git clone https://github.com/jhuguetn/xnat-scripts.git scripts
  ```

## Usage
  ```
  parrec2xnat.py [-h] -H HOSTNAME -p PROJECT -u USERNAME -i INPUT [-nii] [-v] [-s]
  ```

1. A valid XNAT account (usr/pwd) in {XNAT_HOST} is required.
2. User access to existing project {PROJECT_ID} in XNAT is required.
3. Local directory specified in {DIRECTORY} will be recursively scanned for valid PAR/REC duple of files to be sent to XNAT. 
4. This tool will create the required resources (i.e. Subject, Session, Scan) for hosting such data based on header metadata.
5. An optional flag '-nii' enables NIfTI format conversion of PAR/REC data and also uploads the resulting additional files
6. An optional flag '-s' enables snapshot images to be composed and uploaded to XNAT for visual inspection of the scan imaging data

## Dependencies

Python framework at version 2.7.X is required to run such application script. Might also run in version 3.X but it's not being extensively tested.
The following Python scripts are being used in parrec2xnat (and therefore required for running such script tool):
  ```
  import parrec2nii
  import xnatLibrary
  import mosaicCreator
  ```

## Notes

* NIfTI format conversion code fpr parrec2nii (nibabel) has been slightly modified to fit the current parrec2xnat tool. 
* In order to properly run parrec2xnat, additional Python file 'parrec2nii.py','xnatLibrary.py' and 'mosaicCreator.py' should be located in the same directory as this tool is.
* Code developed uses Python package Nibabel (version 2.0) for PAR/REC format parsing

## Extra (Windows only): 

A 'setup.py' script is included to wrap up the Python application as an stand-alone Windows executable file. Thus, no Python framework is needed. 
* Usage: 
  ```
  "python setup.py py2exe -c -d parrec2xnat.exe"
  ```

## Questions/Comments?

Submit an issue, fork and/or PR. Alternatively, reach me at j.huguet(at)amc.uva.nl
