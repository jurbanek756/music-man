import argparse
import os
import subprocess
import json
import math
import shutil
import ffmpeg
import eyed3

def copy_verbose(src,dst):
    print('Copying {0}'.format(src))
    shutil.copy2(src,dst)

def reformat_external_usb_flash_drive():
    if os.path.isdir("/Volumes/MUSIC"):
        print("Erasing External USB Flash Drive")
        subprocess.run(["diskutil", "reformat", "/Volumes/MUSIC"])
   
def add_id3v2_tags(file, art, metadata):
    ALBUM = metadata['format']['tags'].get('ALBUM', '').split('(')[0].strip()
    TRACK = metadata['format']['tags'].get('track', '')
    ARTIST = metadata['format']['tags'].get('ARTIST', '')
    TITLE = metadata['format']['tags'].get('TITLE', '').split('(')[0].strip()
    YEAR = metadata['format']['tags'].get('YEAR', '')
    TRACKTOTAL = metadata['format']['tags'].get('TRACKTOTAL', '')
    GENRE = metadata['format']['tags'].get('GENRE', '').split(', ')
    GENRE.sort(reverse=True)
    if YEAR:
      DECADE = str(int(YEAR) // 10 * 10)
    else:
      DECADE = '0'
    COMPOSER = f"{DECADE}'s Music"
    
    file_load = eyed3.load(file)
    
   
    ARTIST = file_load.tag.album_artist
    if not ARTIST:
      ARTIST = file_load.tag.artist.split('(')[0].strip()
    
    file_load.tag.album = ALBUM
    file_load.tag.album_artist = ARTIST
    file_load.tag.title = TITLE
    file_load.tag.artist = ARTIST
    file_load.tag.composer = COMPOSER
    file_load.tag.year=YEAR
    file_load.tag.genre=GENRE[0].strip()
    if file.endswith(".mp3"):
      imagedata = open(art,"rb").read()
      del file_load.tag.frame_set[b'TXXX'] 
      file_load.tag.images.set(3, imagedata, "image/jpeg")
      if TRACK:
        if TRACKTOTAL:
          file_load.tag.track_num = (TRACK,TRACKTOTAL)
        else:
          file_load.tag.track_num = TRACK
    file_load.tag.save()

def convert_to_mp3_and_move(file, metadata, RESET):
    SAMPLE_RATE_STRING = metadata['streams'][0]['sample_rate']
    if SAMPLE_RATE_STRING != 'null':
      SAMPLE_RATE = int(SAMPLE_RATE_STRING)
    else:
      SAMPLE_RATE = 44100
    NEW_SAMPLE_RATE = 48000 if math.modf(SAMPLE_RATE / 48000)[0] == 0 else 44100

    print(f"Converting {file} to {NEW_SAMPLE_RATE}Hz mp3 at 320kbps")
    TRACK=metadata['format']['tags'].get('track', '')
    if not TRACK:
      TRACK = 0
    MP3_FILENAME = f"{TRACK} {os.path.splitext(file)[0]}.mp3"
    ART_FILENAME = "stage.jpg"
    
    (
      ffmpeg
      .input(file)
      .audio
      .output('stage.mp3', **{'ar': NEW_SAMPLE_RATE,'acodec':'libmp3lame','audio_bitrate':'320k','qscale:a':'0'})
      .overwrite_output()
      .run(capture_stdout=True, capture_stderr=True)
    )
    
    file_load = eyed3.load("stage.mp3")
    ALBUM = file_load.tag.album.split('(')[0].strip().replace(r'/','')
    ALBUM_ARTIST = file_load.tag.album_artist
    if not ALBUM_ARTIST:
      ALBUM_ARTIST = file_load.tag.artist
    ALBUM_ARTIST = ALBUM_ARTIST.split('(')[0].strip().replace(r'/','')

    add_id3v2_tags("stage.mp3", ART_FILENAME, metadata)
 
    destination_dir = f"../mp3/{ALBUM_ARTIST}/{ALBUM}"
    destination_path = os.path.join(destination_dir, MP3_FILENAME)
    print(f"Adding {file} to Music Drive at ${destination_path}")
    os.makedirs(destination_dir, exist_ok=True)
    shutil.copy2("stage.mp3", destination_path)
   
    if os.path.isdir("/Volumes/MUSIC"):
      if not RESET:
        destination_dir = f"/Volumes/MUSIC/{ALBUM_ARTIST}/{ALBUM}"
        destination_path = os.path.join(destination_dir, MP3_FILENAME)
        print(f"Adding {file} to Music Drive at ${destination_path}")
        os.makedirs(destination_dir, exist_ok=True)
        shutil.move("stage.mp3", os.path.join(destination_dir, MP3_FILENAME))
    else:
        os.remove("stage.mp3")

def convert_to_m4a_and_move(file, metadata):
    file_load = eyed3.load(file)
    ALBUM_ARTIST = metadata['format']['tags'].get('album_artist', '').split('(')[0].strip().replace(r'/',' ')
    ART_FILENAME = "stage.jpg"
    ALBUM = metadata['format']['tags'].get('ALBUM', '').split('(')[0].strip().replace(r'/',' ')
    if not ALBUM_ARTIST:
      ALBUM_ARTIST = metadata['format']['tags'].get('ARTIST', '').split('(')[0].strip().replace(r'/',' ')
 
    TRACK = metadata['format']['tags'].get('track', '')
    M4A_FILENAME = f"{TRACK} {os.path.splitext(file)[0]}.m4a"
    destination_dir = f"{os.path.expanduser('~')}/Music/iTunes/iTunes Media/Music/{ALBUM_ARTIST}/{ALBUM}"
    destination_path = os.path.join(destination_dir, M4A_FILENAME)

    if not os.path.exists(destination_path):
        print(f"Converting {file} to {M4A_FILENAME} and moving to {destination_path}")
      
        (
          ffmpeg
          .input(file)
          .audio
          .output(M4A_FILENAME, **{'acodec':'alac','vcodec':'copy'})
          .overwrite_output()
          .run(capture_stdout=True, capture_stderr=True)
        ) 
        add_id3v2_tags(M4A_FILENAME, ART_FILENAME, metadata)
        os.makedirs(destination_dir, exist_ok=True)
        shutil.move(M4A_FILENAME, destination_path)
         

def link_to_music_directory_for_plex(file, ALBUM, ALBUM_ARTIST):
    print(f"Linking {file} to Music Directory for Plex")
    destination_dir = f"{os.path.expanduser('~')}/Music/Plex/{ALBUM_ARTIST}/{ALBUM}"
    os.makedirs(destination_dir, exist_ok=True)
    if os.path.islink(os.path.join(destination_dir, os.path.basename(file))):
      os.unlink(os.path.join(destination_dir, os.path.basename(file)))
    os.symlink(os.path.abspath(file), os.path.join(destination_dir, os.path.basename(file)))

def main():
    os.chdir("./flac")
    parser = argparse.ArgumentParser()
    parser.add_argument("-r", action="store_true")
    parser.add_argument("-l", action="store_true")
    parser.add_argument("-u", action="store_true")
    parser.add_argument("-T", action="store_true")
    parser.add_argument("-m", action="store_true")
    args = parser.parse_args()

    if args.r:
        print("Removing Plex folder in Music")
        if os.path.exists(os.path.expanduser("~/Music/Plex")) and os.path.isdir(os.path.expanduser("~/Music/Plex")):
          shutil.rmtree(os.path.expanduser("~/Music/Plex"))
        reformat_external_usb_flash_drive()
        current_dir = os.getcwd()
    
        for root, dirs, files in os.walk(current_dir, topdown=False):
            for file in files:
                if file.endswith(".flac"):
                    src_path = os.path.join(root, file)
                    shutil.move(src_path, os.path.join(current_dir, file))

            for dir_name in dirs:
                dir_path = os.path.join(root, dir_name)
                try:
                    os.rmdir(dir_path)
                except OSError as e:
                    pass

    if args.T:
        reformat_external_usb_flash_drive()
        os.chdir("jay")
        print("Removing Test Metadata")
        for old_metadata in os.listdir("."):
          if old_metadata.endswith("_metadata.json"):
            os.remove(os.path.join( '.', old_metadata))
    if args.u:
        reformat_external_usb_flash_drive()

    LINK = args.l
    UNMOUNT = args.u
    
    extension=""
    if args.m:
        extension=".mp3"
    else:
        extension=".flac"
    i = 0
    for file in os.listdir("."):
        if file.endswith(extension):
                metadata = (
                    ffmpeg
                    .probe(file)
                )
                ALBUM = metadata['format']['tags'].get('ALBUM', '').split('(')[0].strip()
                ALBUM_ARTIST = metadata['format']['tags'].get('ARTIST', '')
                #file_load = eyed3.load(file)
                #ALBUM = file_load.tag.album.split('(')[0].strip().replace(r'/','')
                #ALBUM_ARTIST = file_load.tag.album_artist.split('(')[0].strip().replace(r'/','')
                if ALBUM_ARTIST == 'null':
                  ALBUM_ARTIST = file_load.tag.artist.split('(')[0].strip().replace(r'/','')
                ART_FILENAME = "stage.jpg"
                if ALBUM.endswith("."):
                    ALBUM_FP = ALBUM[:-1] + "_"
                else:
                    ALBUM_FP = ALBUM
                if ALBUM_ARTIST.endswith("."):
                    ALBUM_ARTISTFP = ALBUM_ARTIST[:-1] + "_"
                else:
                    ALBUM_ARTISTFP = ALBUM_ARTIST
                (
                  ffmpeg
                  .input(file)
                  .output(ART_FILENAME)
                  .overwrite_output()
                 .run(capture_stdout=True, capture_stderr=True)
                )
                convert_to_mp3_and_move(file, metadata, UNMOUNT)
#                convert_to_m4a_and_move(file, metadata)
                print(f"Moving {file}")
                destination_dir = f"./{ALBUM_ARTIST}/{ALBUM}"
                destination_path = os.path.join(destination_dir, os.path.basename(file))
                os.makedirs(destination_dir, exist_ok=True)
                shutil.move(os.path.abspath(file), destination_path)

                link_to_music_directory_for_plex(destination_path,ALBUM_FP,ALBUM_ARTISTFP)
                i += 1
    os.chdir('..')
    if i == 0:
        print("Error: No new files to convert.")
    if LINK:
        print("Refreshing Plex library")
        subprocess.run(["curl", "http://127.0.0.1:32400/library/sections/2/refresh?X-Plex-Token=shZ72bbxHgErQ-6daUd5"])
    
    if UNMOUNT:
        if os.path.isdir("/Volumes/MUSIC"):
          shutil.copytree('./mp3/','/Volumes/MUSIC/', dirs_exist_ok = True, copy_function=copy_verbose, ignore=shutil.ignore_patterns('*.DS_STORE'))
          print("Unmounting /Volumes/Music")
          subprocess.run(["diskutil", "umount", "/Volumes/Music"])

if __name__ == "__main__":
    main()

