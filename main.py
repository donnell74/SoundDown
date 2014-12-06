import soundcloud
import urllib
import wget
import os
import shutil
import subprocess
from mutagen import File
from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT2, APIC, TCON, TCOM, ID3NoHeaderError, error

class Downloader:
    """Wrapper class for all download logic"""
    def __init__(self):
        """Initalizeds the client and some global strings"""
        self.client = soundcloud.Client(client_id="e54975908f6d3073657a1a66b654f79a")
        self.client_str = "?client_id=e54975908f6d3073657a1a66b654f79a"
        self.past_songs_db = open("past_songs.db", 'r+')
        self.past_songs_db_data = [line.strip() for line in self.past_songs_db.readlines()]


    def get_track_filename(self, url = None):
        """Gets the filename of a track based off the headers of a url"""
        track_file = urllib.urlopen(url)
        headers = track_file.info()
        track_file.close()
        return wget.filename_from_headers(headers)


    def move_tracks_to_music_folder(self ):
        """Moves all tracks in the current folder to the ~/Music/ folder"""
        home = os.path.expanduser("~")
        dest = home + "/Music/"
        for each_file in self.past_songs_db_data:
            if os.path.isfile(each_file) and \
               not os.path.isfile(dest + each_file): 
                shutil.move(each_file, dest)


    def set_track_metadata(self, track = None, filename = None, url = None):
        """Find and set all metadata for a track"""
        if url == None or track == None:
            return None

        if filename == None:
            filename = get_track_filename(url)

        # id3 is only for mp3
        if not filename.endswith(".mp3"):
            if filename.endswith(".wav"):
                filename = self.convert_wav_to_mp3(filename)
            else:
                return None

            print filename

        # Set title
        try:
            meta = ID3(filename)
        except ID3NoHeaderError:
            meta = File(filename, easy=True)
            meta.add_tags()
            meta.save()
            meta = ID3(filename)

        meta.add(TIT2(encoding=3, text=track.title))
        meta.add(TCON(encoding=3, text=track.genre))
        meta.add(TCOM(encoding=3, text=track.user["username"]))
        meta.save()

        artwork_filename = wget.download(track.artwork_url)

        audio = MP3(filename, ID3=ID3)

        # add ID3 tag if it doesn't exist
        try:
            audio.add_tags()
        except error:
            pass

        audio.tags.add(
            APIC(
                encoding=3, # 3 is for utf-8
                mime='image/jpeg', # image/jpeg or image/png
                type=3, # 3 is for the cover image
                desc=u'Cover',
                data=open(artwork_filename).read()
            )
        )
        audio.save()


    def download_track(self, track = None, url = None):
        """Download a track pointed at by the url given"""
        # check that track doesn't exist
        if url == None or track == None:
            return

        print "Retrieving the name of the track."
        filename = self.get_track_filename(url)

        print "Filename found: " + filename
        
        if filename in self.past_songs_db_data and \
           not os.path.isfile(filename): 
            print "File exists"
        else:
            print "Downloading"
            filename = wget.download(url)
            self.set_track_metadata(track, filename, url)

            # Save filename for future reference
            self.past_songs_db.write(filename + "\n")
    
        print


    def download_free_tracks_by_search(self, query='trapstep', limit=10):
        """Downloads the first <limit> songs from tracks/q=<query>"""
        tracks = self.client.get('tracks/', q=query, limit=limit)
        for track in tracks:
            if track.downloadable:
                url = track.download_url + self.client_str

                # print out some useful data
                print track.title
                print url

                self.download_track(track, url)


    def convert_wav_to_mp3(self, filename):
        mp3_name = filename[:-4] + '.mp3' 

        if filename.endswith(".wav") and \
           os.path.isfile(filename) and \
           mp3_name not in self.past_songs_db_data: 
            cmd = 'lame --preset insane "%s"' % filename
            subprocess.call(cmd, shell=True)

            # add the mp3 to the db
            self.past_songs_db_data.append(mp3_name)
            self.past_songs_db.write(mp3_name + "\n")

        return mp3_name


    def all_wav_to_mp3(self):
        """Convert all .wav files to .mp3 files in the current folder"""
        for each_file in self.past_songs_db_data:
            self.convert_wav_to_mp3(each_file)


    def delete_leftovers(self):
        """Remove all leftover songs that could not be moved over
           because we already had a copy of it somehow"""
        for each_file in self.past_songs_db_data:
            if os.path.isfile(each_file): 
                os.remove(each_file)
                print "Deleted " + each_file

        for each_file in os.listdir("."):
            if each_file.endswith(".jpg"):
                os.remove(each_file)


    def cleanup(self):
        """Last minute cleaning up such as moving songs to ~/Music/"""
        self.all_wav_to_mp3()
        self.past_songs_db.close()
        self.move_tracks_to_music_folder( )
        self.delete_leftovers()
        print "Cleanup finished"

    def min_cleanup(self):
        """Do absolute mininum cleanup needed"""
        self.past_songs_db.close()

    def main(self):
        self.download_free_tracks_by_search(query='dubstep', limit=30)
        self.cleanup()


if __name__ == "__main__":
    Downloader().main()
