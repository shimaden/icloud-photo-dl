# icloud-photo-dl
iCloud Photo Downloader

## Description
Download photo and video files from iCloud Photo.

## Requirement
Python 3

pyicloud library [https://github.com/picklepete/pyicloud]

## Usage
    icloud-photo-dl.py --titles
    
    Enumerate all album titles.
    
    icloud-photo-dl.py --all
    
    Download all photos in all albums except for "All Photos".

    icloud-photo-dl.py --all-no-download

    Simulate above.

    icloud-photo-dl.py --single album-title
    
    Download all photos in the specified album title.
    
    icloud-photo-dl.py --single-no-download album-title
    
    Simulate above.

## INSTALLATION
  make install
  
  The executable will be placed in /usr/local/bin.
    
  Create /usr/local/etc/icloud-photo-dl/password file in the below format:
  
  User: &lt;your-icloud-user-name&gt;

  Password: &lt;your-icloud-password&gt;
  
  It is highly recommended to change the owner of "password" file to your account and to set the permission to 600.

## Author
  Shimaden
  
  Copyright (c) 2019 shimaden. All right reserved.
  
    https://github.com/shimaden/icloud-photo-dl
