# nifti2xnat

## Introduction 

Some XNAT users have their input scan data in NIfTI format which is not supported 'per-se' by XNAT. This tool allows to automate the uploading process of NIfTI input data. 

## Installation procedure

Get the lattest version of the scripts as follows: 
  ```
  git clone https://github.com/jhuguetn/xnat-scripts.git scripts
  ```

## Usage
```
nifti2xnat [-h] -H HOSTNAME -p PROJECT -u USERNAME -i INPUT [-v]
```

1. A valid XNAT account (usr/pwd) in {HOSTNAME} is required.
2. User access to existing project {PROJECT} in XNAT is required.
3. Local directory specified in {INPUT} will be recursively scanned for valid NIfTI files to be sent to XNAT. 
4. This tool will create the required resources (i.e. Subject, Session, Scan) for hosting such data based on following assumptions made based on the nonexistence of metadata in NIfTI format data:
	* NIfTI files should include extension '.nii' or '.NII' to be processed by the script (.bvec and .bval files also will be processed)
	* Subject name = local file name OR parent directory name
	* A single session is expected per subject, thus Session name = Subject name
	* Sessions may contain structural and/or functional scan files.

	
## Dependencies

Python framework at version 2.7.X is required to run such application script. Might also run in version 3.X but it's not being extensively tested.

## Notes

* Code developed uses a function based on Pietro Abate's work for encoding HTTP messages as a multipart/form-data HTTP message.

## Extra (Windows only): 

A 'setup.py' script is included to wrap up the Python application as an stand-alone Windows executable file. Thus, no Python framework is needed. 
* Usage: 
  ```
  "python setup.py py2exe -c -d nifti2xnat.exe"
  ```

## Questions/Comments?

Submit an issue, fork and/or PR. Alternatively, reach me at jhuguetn(at)google.com
