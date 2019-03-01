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

def auth(username, password):

    print("認証を受けます。")
    sys.stdout.flush()
    api = PyiCloudService(username, password)
    print("認証が終わりました。")
    sys.stdout.flush()

    if api.requires_2sa:
        import click
        print("Two-step authentication required. Your trusted devices are:")

        devices = api.trusted_devices
        for i, device in enumerate(devices):
            print("  %s: %s" % (i, device.get('deviceName',
                "SMS to %s" % device.get('phoneNumber'))))

        device = click.prompt('Which device would you like to use?', default=0)
        device = devices[device]
        if not api.send_verification_code(device):
            print("Failed to send verification code")
            sys.exit(1)

        code = click.prompt('Please enter validation code')
        if not api.validate_verification_code(device, code):
            print("Failed to verify verification code")
            sys.exit(1)

    return api

def read_account_info(filename):
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

def get_album_size(api, album_title):
    album = api.photos.albums[album_title]
    album_size = len(album)
    return album_size

def enumerate_and_print_albums(api):
    print("----- List of Albums -----")
    for album_title in api.photos.albums:
        album_size = get_album_size(api, album_title)
        print("[{}] {} photos".format(album_title, album_size))

def enumerate_album_titles(api):
    return api.photos.albums

def mkdir_if_not_exist(directory):
    path = Path(directory)
    if not path.is_dir():
        path.mkdir(parents=True)

# atime: 最終アクセス時刻
# mtime: 最終変更時刻
def overwrite_timestamp(path, photo):
    atime = photo.created.timestamp()
    mtime = photo.created.timestamp()
    os.utime(path, times=(atime, mtime))

def localtime(datetime):
    return datetime.astimezone()

def save_to_file(photo, fname):
    response = photo.download()
    with open(fname, 'wb') as f:
        f.write(response.raw.read())
        overwrite_timestamp(fname, photo)
    return response

def make_download_fname(filename):
    path = Path(filename)
    parent = path.parent
    stem   = path.stem
    suffix = path.suffix

    is_need_rename = False
    pattern = re.compile("_[0-9]{2,}$") 
    if pattern.match(stem):
        # リネームされたファイル名である
        is_need_rename = True
    else:
        # リネームされたファイル名ではない
        if not path.is_file():
            return filename
        else:
            is_need_rename = True

    fname = None
    i = 1
    is_continue = True
    while is_continue:
        basic_fname = '{}_{:03d}{}'.format((parent / stem), i, suffix)
        path = Path(basic_fname)
        if not path.is_file():
            fname = basic_fname
            is_continue = False
        i += 1

    return fname

def download_a_photo(i, photo, album_size, dest_fname, show_only):
    fname = make_download_fname(dest_fname)
    timestamp = localtime(photo.created)
    if fname == dest_fname:
        print('Downloading ({}/{}) {} ({}) "{}"...'.format(
                i + 1, album_size, fname, photo.size,
                timestamp.strftime("%Y-%m-%d %H:%M:%S %z %Z")
            )
        )
        sys.stdout.flush()
        if not show_only:
            response = save_to_file(photo, fname)
    else:
        print('Downloading file ({}/{}) {} ({}) {} as "{}"...'.format(
                i + 1, album_size, dest_fname, photo.size,
                timestamp.strftime("%Y-%m-%d %H:%M:%S %z %Z"),
                fname
            )
        )
        sys.stdout.flush()
        if not show_only:
            response = save_to_file(photo, fname)

def show_photo_info(i, photo):
    p = photo
    width  = p.dimensions[0]
    height = p.dimensions[1]
    ctime = localtime(p.created).strftime("%Y-%m-%d %H:%M:%S %z %Z")
    ctime2 = localtime(p.created).strftime("%Y-%m-%d %H:%M:%S")
    added_date = localtime(p.added_date).strftime("%Y-%m-%d %H:%M:%S")
    print("ID          : {}".format(p.id))
    print("{:13s} ({:>7}) {:>4}x{:>4}".format(p.filename, p.size, height, width))
    print("    作成日時: {}".format(ctime2))
    print("    追加日時: {}".format(added_date))
    sys.stdout.flush()

def download_single_album(api, album_title, show_only):
    try:
        print("ダウンロードを開始します。")
        album = api.photos.albums[album_title]
        album_size = get_album_size(api, album_title)
        print("アルバム: {}, ファイル数: {}".format(album.title, album_size))
        sys.stdout.flush()

        dl_directory = str(Path('albums').joinpath(album_title))
        if album_size > 0 and not show_only:
            mkdir_if_not_exist(dl_directory)
        for i, photo in enumerate(album):
            dl_photo_path = str(Path(dl_directory).joinpath(photo.filename))
            album_size = get_album_size(api, album_title)
            if show_only:
                download_a_photo(i, photo, album_size, dl_photo_path, show_only)
            else:
                download_a_photo(i, photo, album_size, dl_photo_path, show_only)
    except Exception as e:
        print("Exception: {}".format(e), file=sys.stderr)
        #sys.stderr.print("PyiCloudAPIResponseError: {}".format(e.message))

def download_all_albums(api, show_only):
    for title in enumerate_album_titles(api):
        print(title)
        if title != 'All Photos':
            download_single_album(api, title, show_only)

def usage():
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

show_only = False
album_title = ""

passwd_path = Path(ETC_DIR).joinpath('password')
if not passwd_path.is_file():
    print("File not found: \"{}\".".format(passwd_path), file=sys.stderr)
    sys.exit(1)

account = read_account_info(str(passwd_path))

if len(sys.argv) == 1:
    usage()
    sys.exit(1)

if len(sys.argv) == 2:
    if sys.argv[1] == '--all':
        api = auth(account['user'], account['password'])
        print('Download all albums except for "All Photos"')
        download_all_albums(api, show_only)
    elif sys.argv[1] == '--all-no-download':
        api = auth(account['user'], account['password'])
        show_only = True
        print('Download all albums except for "All Photos"')
        download_all_albums(api, show_only)
        print("Show 'All Photos'")
        show_only = True
    elif sys.argv[1] == '--titles':
        api = auth(account['user'], account['password'])
        print("Show album titles:")
        enumerate_and_print_albums(api)
    else:
        usage()
        sys.exit(1)

elif len(sys.argv) == 3:
    if sys.argv[1] == '--single':
        api = auth(account['user'], account['password'])
        album_title = sys.argv[2]
        print("Download album '{}'.".format(album_title))
        download_single_album(api, album_title, show_only)
    elif sys.argv[1] == '--single-no-download':
        api = auth(account['user'], account['password'])
        album_title = sys.argv[2]
        print("Download album '{}'.".format(album_title))
        show_only = True
        download_single_album(api, album_title, show_only)
    else:
        usage()
        sys.exit(1)

else:
    usage()
    sys.exit(1)
