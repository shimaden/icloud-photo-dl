#!/usr/bin/python3
import sys
print('ちょっと待っててね。')
sys.stdout.flush()
import os
import time
import datetime
import re
import pprint
from pathlib import Path
from pyicloud import PyiCloudService

ETC_DIR = "/usr/local/etc/icloud-photo-dl"

class PhotoDownloader:

    def __init__(self):
        self.__api = None

    def get_api(self):
        return self.__api

    def set_api(self, api):
        self.__api = api

    api = property(get_api, set_api)

    def auth(self, username, password):

        if self.api != None:
            print("認証済みです。")
            return

        print("認証を受けます。")
        sys.stdout.flush()
        api = PyiCloudService(username, password)
        print("認証が終わりました。")
        sys.stdout.flush()
        self.api = api

        if self.api.requires_2sa:
            import click
            print("Two-step authentication required. Your trusted devices are:")

            devices = self. api.trusted_devices
            for i, device in enumerate(devices):
                print("  %s: %s" % (i, device.get('deviceName',
                    "SMS to %s" % device.get('phoneNumber'))))

            device = click.prompt('Which device would you like to use?', default=0)
            device = devices[device]
            if not self.api.send_verification_code(device):
                print("Failed to send verification code")
                sys.exit(1)

            code = click.prompt('Please enter validation code')
            if not self.api.validate_verification_code(device, code):
                print("Failed to verify verification code")
                sys.exit(1)

        #return api

    def read_account_info(self, filename):
        account = {'user': None, 'password': None}
        with open(filename, "r") as f:
            for line in f:
                arr = line.strip().split()
                if len(arr) != 2:
                    continue
                if arr[0].lower() == "user:":
                    account['user'] = arr[1]
                elif arr[0].lower() == "password:":
                    account['password'] = arr[1]

        return account

    def get_album_size(self, album_title):
        album = self.api.photos.albums[album_title]
        album_size = len(album)
        return album_size

    def enumerate_and_print_albums(self):
        print("----- List of Albums -----")
        for album_title in self.api.photos.albums:
            album_size = self.get_album_size(album_title)
            print("[{}] {} photos".format(album_title, album_size))

    def enumerate_album_titles(self):
        return self.api.photos.albums

    def mkdir_if_not_exist(self, directory):
        path = Path(directory)
        if not path.is_dir():
            path.mkdir(parents=True)

    # atime: 最終アクセス時刻
    # mtime: 最終変更時刻
    # Set atime and mtime of path to created time.
    def set_timestamp(self, path, timestamp):
        mtime = timestamp
        atime = mtime
        os.utime(path, times=(atime, mtime))

    def localtime(self, datetime):
        return datetime.astimezone()

    def save_to_file(self, photo_data, timestamp, fname):
        cnt = None
        with open(fname, 'wb') as f:
            f.write(photo_data)
            self.set_timestamp(fname, timestamp)
        return cnt == len(photo_data)

    # Excape forbidden characters for the file name.
    # Linux  : /
    # Windows: / > < ? : " \ * | ;
    # '%' is excluded to use as an escape character.
    def escape_for_filesystem(self, s):
        return s \
           .replace('%', '%25') \
           .replace('"', '%22') \
           .replace('#', '%23') \
           .replace('*', '%2A') \
           .replace('/', '%2F') \
           .replace(':', '%3A') \
           .replace(';', '%3B') \
           .replace('<', '%3C') \
           .replace('>', '%3E') \
           .replace('?', '%3F') \
           .replace('\\', '%5C') \
           .replace('|', '%7C')

    def download_and_save_a_photo(self, i, photo, album_size, dest_fname, show_only):
        fname = dest_fname
        path = Path(dest_fname)
        # Excape forbidden characters for the file name.
        # Linux  : /
        # Windows: / > < ? : " \ * | ;
        # '%' is excluded to use as an escape character.
        #photo_id = photo.id \
        #           .replace('%', '%25') \
        #           .replace('"', '%22') \
        #           .replace('#', '%23') \
        #           .replace('*', '%2A') \
        #           .replace('/', '%2F') \
        #           .replace(':', '%3A') \
        #           .replace(';', '%3B') \
        #           .replace('<', '%3C') \
        #           .replace('>', '%3E') \
        #           .replace('?', '%3F') \
        #           .replace('\\', '%5C') \
        #           .replace('|', '%7C')
        photo_id = self.escape_for_filesystem(photo.id)
        fname = str(path.parent / Path(str(path.stem) + "." + photo_id + str(path.suffix)))
        if not show_only:
            timestamp = self.localtime(photo.created)
            if Path(fname).exists():
                print('File exists  : ({}/{}) {}: "{}" ({}) {} as "{}"'.format(
                        i + 1, album_size, photo.id, dest_fname, photo.size,
                        timestamp.strftime("%Y-%m-%d %H:%M:%S %z %Z"),
                        fname
                    )
                )
            else:
                timestamp = self.localtime(photo.created)
                response = photo.download()
                photo_data = response.raw.read()
                self.save_to_file(photo_data, photo.created.timestamp(), fname)
                print('Download done: ({}/{}) {}: "{}" ({}) {} as "{}"'.format(
                        i + 1, album_size, photo.id, dest_fname, photo.size,
                        timestamp.strftime("%Y-%m-%d %H:%M:%S %z %Z"),
                        fname
                    )
                )
            sys.stdout.flush()

    def show_photo_info(self, i, photo):
        width  = photo.dimensions[0]
        height = photo.dimensions[1]
        ctime_str = self.localtime(photo.created).strftime("%Y-%m-%d %H:%M:%S")
        added_date_str = self.localtime(photo.added_date).strftime("%Y-%m-%d %H:%M:%S")
        print("ID          : {}".format(photo.id))
        print("{:13s} ({:>7}) {:>4}x{:>4}".format(photo.filename, photo.size, height, width))
        print("    作成日時: {}".format(ctime_str))
        print("    追加日時: {}".format(added_date_str))
        #print("URL         : {}".format(photo.versions['original']['url']))
        sys.stdout.flush()

    # Download the photos in albim_title.
    def download_single_album(self, album_title, show_only):
        try:
            print("ダウンロードを開始します。")
            album = self.api.photos.albums[album_title]
            album_size = self.get_album_size(album_title)
            print("アルバム: {}, ファイル数: {}".format(album.title, album_size))
            sys.stdout.flush()

            dl_directory = str(Path('albums').joinpath(self.escape_for_filesystem(album_title)))

            if album_size > 0 and not show_only:
                self.mkdir_if_not_exist(dl_directory)

            for i, photo in enumerate(album):
                dl_photo_path = str(Path(dl_directory).joinpath(photo.filename))
                album_size = self.get_album_size(album_title)
                if show_only:
                    self.download_and_save_a_photo(i, photo, album_size, dl_photo_path, show_only)
                    self.show_photo_info(i, photo)
                else:
                    self.download_and_save_a_photo(i, photo, album_size, dl_photo_path, show_only)

        except Exception as e:
            print("Exception: {}: {}".format(type(e), e), file=sys.stderr)
            #sys.stderr.print("PyiCloudAPIResponseError: {}".format(e.message))

    #def enumerate_album_titles(self.api):
    #    return api.photos.albums

    def download_all_albums(self, show_only):
        #for title in self.enumerate_album_titles():
        for title in self.api.photos.albums:
            print(title)
            if title != 'All Photos':
                self.download_single_album(title, show_only)

    def usage(self):
        print("Usage:", file=sys.stderr)
        print("    {} --titles".format(sys.argv[0]), file=sys.stderr)
        print("    {} --all".format(sys.argv[0]), file=sys.stderr)
        print("    {} --single album-title".format(sys.argv[0]), file=sys.stderr)
        print("    {} --all-no-download".format(sys.argv[0]), file=sys.stderr)
        print("    {} --single-no-download album-title".format(sys.argv[0]), file=sys.stderr)
        print("")
        print("Copyright (c) 2019 shimaden. All right reserved.")
        print("    https://github.com/shimaden/icloud-photo-dl")


#----- Main -----

# Exception: <class 'pyicloud.exceptions.PyiCloudAPIResponseError'>: private db access disabled for this account.  Please wait a few minutes then try again.  The remote servers might be trying to throttle requests. (ACCESS_DENIED)

# Exception: <class 'pyicloud.exceptions.PyiCloudAPIResponseError'>: Invalid global session

# Exception: <class 'pyicloud.exceptions.PyiCloudAPIResponseError'>: Service Unavailable (503)

# Exception: <class 'pyicloud.exceptions.PyiCloudAPIResponseError'>: Gone (410)

#/usr/lib/python3/dist-packages/requests/__init__.py:91: RequestsDependencyWarning: urllib3 (1.25.3) or chardet (3.0.4) doesn't match a supported version!
#  RequestsDependencyWarning)


# /usr/lib/python3/dist-packages/requests/__init__.py:91: RequestsDependencyWarning: urllib3 (1.25.3) or chardet (3.0.4) doesn't match a supported version!
#   RequestsDependencyWarning)
# Exception: <class 'requests.exceptions.SSLError'>: HTTPSConnectionPool(host='cvws.icloud-content.com', port=443): Max retries exceeded with url: /B/ATd0YzytzfOWIIcHo4QN1344IbKHAd1ltomZNoTvFVRagJGqH7V09Lsn/$%7Bf%7D?o=AmxpdgbsyMD881KioPuWcJ5vAqGMZdvw6n9J6VLdApqR&v=1&x=3&a=CAog6Vc7NdQiz5I7tRvmJl4ZVaPHjunp32Ynd7S0uIxd_KMSHRCY86uJii4YmNCHi4ouIgEAUgQ4IbKHWgR09Lsn&e=1583255513&k=e-wQ2z2s6XCLN-3dQI4VUA&fl=&r=12411780-9529-4b9a-a3c3-49691abfaa5e-1&ckc=com.apple.photos.cloud&ckz=PrimarySync&y=1&p=25&s=0KYXZ0O9vH8IPzMUxzz6N_4wqtU (Caused by SSLError(SSLError("bad handshake: SysCallError(-1, 'Unexpected EOF')")))


# ダウンロード正常終了時
# Download done: (13328/13330) Ab9EOfgzSzLY0FzuVWC4rCKYj1R1: "albums/All Photos/IMG_0059.PNG" (1177352) 2017-05-07 07:16:48 +0900 JST as "albums/All Photos/IMG_0059.Ab9EOfgzSzLY0FzuVWC4rCKYj1R1.PNG"
# Download done: (13329/13330) AbfH5Zd+fj8BqWAwJnpmTDlCjOFR: "albums/All Photos/IMG_0057.PNG" (1351363) 2017-05-05 22:29:47 +0900 JST as "albums/All Photos/IMG_0057.AbfH5Zd+fj8BqWAwJnpmTDlCjOFR.PNG"
# File exists  : (13330/13330) AbfH5Zd+fj8BqWAwJnpmTDlCjOFR: "albums/All Photos/IMG_0057.PNG" (1351363) 2017-05-05 22:29:47 +0900 JST as "albums/All Photos/IMG_0057.AbfH5Zd+fj8BqWAwJnpmTDlCjOFR.PNG"
# /usr/lib/python3/dist-packages/requests/__init__.py:91: RequestsDependencyWarning: urllib3 (1.25.3) or chardet (3.0.4) doesn't match a supported version!
#   RequestsDependencyWarning)


show_only = False
#show_only = True
album_title = ""

passwd_path = Path(ETC_DIR).joinpath('password')
if not passwd_path.is_file():
    print("File not found: \"{}\".".format(passwd_path), file=sys.stderr)
    sys.exit(1)

downloader = PhotoDownloader()

account = downloader.read_account_info(str(passwd_path))

if len(sys.argv) == 1:
    downloader.usage()
    sys.exit(1)

if len(sys.argv) == 2:

    if sys.argv[1] == '--all':
        downloader.auth(account['user'], account['password'])
        print('Download all albums except for "All Photos"')
        downloader.download_all_albums(show_only)

    elif sys.argv[1] == '--all-no-download':
        downloader.auth(account['user'], account['password'])
        show_only = True
        print('Download all albums except for "All Photos"')
        downloader.download_all_albums(show_only)

    elif sys.argv[1] == '--titles':
        downloader.auth(account['user'], account['password'])
        print("Show album titles:")
        downloader.enumerate_and_print_albums()

    else:
        usage()
        sys.exit(1)

elif len(sys.argv) == 3:

    if sys.argv[1] == '--single':
        downloader.auth(account['user'], account['password'])
        album_title = sys.argv[2]
        print("Download album '{}'.".format(album_title))
        downloader.download_single_album(album_title, show_only)

    elif sys.argv[1] == '--single-no-download':
        downloader.auth(account['user'], account['password'])
        album_title = sys.argv[2]
        print("Download album '{}'.".format(album_title))
        show_only = True
        downloader.download_single_album(album_title, show_only)

    else:
        usage()
        sys.exit(1)

else:
    usage()
    sys.exit(1)
