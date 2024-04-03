import os
import signal
import sys
import argparse
import shutil
import time
import datetime
import glob
import random
import requests
from threading import Thread, Semaphore
from streamlink import Streamlink
from fake_useragent import UserAgent
from rich.console import Console
from rich.live import Live
from rich.prompt import Prompt
from rich.spinner import Spinner
from rich.table import Table
from rich.text import Text
import subprocess

console = Console()

# Session creating for request
ua = UserAgent()
session = Streamlink()
session.set_option("http-headers", {
    "Accept-Language": "en-US,en;q=0.5",
    "Connection": "keep-alive",
    "DNT": "1",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": ua.random,
    "Client-ID": "your_client_id",  # Replace with your actual Client-ID
    "Referer": "https://www.google.com/"
})

class ViewerBot:
    def __init__(self, nb_of_threads, channel_name, record_time):
        self.nb_of_threads = int(nb_of_threads)
        self.channel_name = channel_name
        self.request_count = 0
        self.all_proxies = []
        self.channel_url = "https://www.twitch.tv/" + self.channel_name
        self.thread_semaphore = Semaphore(int(nb_of_threads))
        self.active_threads = 0
        self.record_time = record_time
        self.file_proxy = "proxy.conf"
        self.max_timerecordfile = 60

    def hprint(self,color, texte):
        timestamp = datetime.datetime.now().strftime("%Hh %Mm %Ss")
        console.print("[bold "+color+"] ["+timestamp+"] "+texte+" [/bold "+color+"]")



    # def get_proxies(self):
    #     try:
    #         response = requests.get("https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all")
    #         if response.status_code == 200:
    #             lines = response.text.split("\n")
    #             lines = [line.strip() for line in lines if line.strip()]
    #             return lines
    #     except Exception as e:
    #         console.print("Error retrieving proxies: {}".format(e), style="bold red")
    #         return []
        
    def del_mp3(self, dossier):
        motif = os.path.join(dossier, '*.mp3')
        for file in glob.glob(motif):
            os.remove(file)
            self.hprint("",f"file deleted : {file}")

    def clear_diretory(self, dir_inrecord="in_record", dir_record="record"):
        # self.hprint('green', 'clear_diretory start')
        if os.path.exists(dir_inrecord) and os.path.exists(dir_record):
            self.hprint('green', f"dir {dir_inrecord} and {dir_record} exist clearing")
            self.del_mp3(dir_inrecord)
            self.del_mp3(dir_record)
        
    def get_proxies(self):
        if os.path.exists(self.file_proxy):
            self.hprint("green",f"The {self.file_proxy} file already exists. ")
            with open(self.file_proxy, 'r') as fichier:
                data = fichier.read()
                # print(data)
        else:
            self.hprint("yellow",f"The {self.file_proxy} file does not exist. Content retrieval from URL...")
            url = "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all"
            response = requests.get(url)
            
            if response.status_code == 200:
                with open(self.file_proxy, 'w') as fichier:
                    fichier.write(response.text)
                print(f"Content retrieved and written in {self.file_proxy}.")
            else:
                print("Error when retrieving content.")

    def get_url(self):
        url = ""
        try:
            streams = session.streams(self.channel_url)
            url = streams['audio_only'].url if 'audio_only' in streams else streams['worst'].url
        except Exception as e:
            pass
        return url


    def loop_run(self, intervalle):

        try:
            while True:
                self.hprint("green","Start scan files............")
                self.verif_record_move()
                self.hprint("yellow",f"Attente de {intervalle} secondes avant le prochain traitement.")
                time.sleep(intervalle)  
        except KeyboardInterrupt:
            self.hprint("red","STOP LOOP.")


    def verif_record_move(self, dir_inrecord="in_record", dir_record="record"):
        if not os.path.exists(dir_record):
            os.makedirs(dir_record)
        
        fichiers = [f for f in os.listdir(dir_inrecord) if os.path.isfile(os.path.join(dir_inrecord, f))]
        if len(fichiers) > 1:
            # sort file
            sort_file = sorted(fichiers, key=lambda x: int(x.split('_')[-1].split('.')[0]))
            fileto_move = sort_file[0]
            
            chemin_source = os.path.join(dir_inrecord, fileto_move)
            chemin_destination = os.path.join(dir_record, fileto_move)
            
            # move file
            shutil.move(chemin_source, chemin_destination)
            self.hprint("green",f"File moved: {fileto_move}")
        else:
            self.hprint("yellow","Not enough files to compare.")

    def compteur(self, ):
        seconds = 0
        loop = 0
        while True:
            time.sleep(1)  # Attend une seconde
            seconds += 1
            print(f"Recording time: {seconds} s // file number : {loop} ", end='\r', flush=True)  # Réinitialise la ligne à chaque fois
            if seconds == self.max_timerecordfile:
                loop +=1
                seconds = 0  # Réinitialise le compteur après 60 seconds


    def record_audio(self):
        output_directory = "record"
        in_record_directory = "in_record"
        os.makedirs(output_directory, exist_ok=True)
        os.makedirs(in_record_directory, exist_ok=True)

        stream_url = self.get_url()
        if not stream_url:
            console.print("[bold red]Impossible de récupérer l'URL du flux[/bold red]")
            return

        timestamp_complet = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d")

        output_file_path = os.path.join(in_record_directory, f"{timestamp}_%03d.mp3")

        self.hprint("green", f"start record")
        thread_compteur = Thread(target=self.compteur)
        thread_compteur.start()

        command = ['ffmpeg','-i', stream_url,'-vn','-acodec','libmp3lame','-ar','44100','-ac','2','-map','0:a','-f','segment','-segment_time',str(self.max_timerecordfile),'-segment_format','mp3',output_file_path,'-loglevel', 'error']
        # self.hprint('yellow',str(command))
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        output, error = process.communicate()
        thread_compteur.do_run = False
        thread_compteur.join()


    def main(self):
        self.all_proxies = self.get_proxies()
        self.clear_diretory()

        record_thread = Thread(target=self.record_audio)
        record_thread.start()
        # record_thread.join()  # Wait for the recording to finish


        loop_run = Thread(target=self.loop_run(30))
        loop_run.start()
        loop_run.join()  # Wait for the recording to finish

        console.print("[bold magenta]Enregistrement terminé, le programme va se terminer.[/bold magenta]")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-threads', type=int, default=10, help='Number of threads')
    parser.add_argument('-recordtime', type=int, default=60, help='Time to record')
    parser.add_argument('-twitchname', type=str, required=True, help='Twitch channel name')
    args = parser.parse_args()

    bot = ViewerBot(nb_of_threads=args.threads, channel_name=args.twitchname, record_time=args.recordtime)
    try:
        bot.main()
    except KeyboardInterrupt:
        console.print("[bold red]ERREUR RECORDING[/bold red]")
