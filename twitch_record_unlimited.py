import os
import signal
import sys
import argparse
import shutil
import time
import datetime
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
        
    def get_proxies(self):
        if os.path.exists(self.file_proxy):
            self.hprint("green",f"Le fichier {self.file_proxy} existe déjà.")
            with open(self.file_proxy, 'r') as fichier:
                contenu = fichier.read()
                # print(contenu)
        else:
            self.hprint("yellow",f"Le fichier {self.file_proxy} n'existe pas. Récupération du contenu depuis l'URL...")
            # URL à partir de laquelle récupérer le contenu
            url = "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all"
            # Effectue la requête GET
            response = requests.get(url)
            
            # Vérifie si la requête a réussi
            if response.status_code == 200:
                # Écrit le contenu dans le fichier
                with open(self.file_proxy, 'w') as fichier:
                    fichier.write(response.text)
                print(f"Contenu récupéré et écrit dans {self.file_proxy}.")
            else:
                print("Erreur lors de la récupération du contenu.")

    def get_url(self):
        url = ""
        try:
            streams = session.streams(self.channel_url)
            url = streams['audio_only'].url if 'audio_only' in streams else streams['worst'].url
        except Exception as e:
            pass
        return url


    def record_audio(self):
        output_directory = "record"
        in_record_directory = "in_record"
        os.makedirs(output_directory, exist_ok=True)
        os.makedirs(in_record_directory, exist_ok=True)

        stream_url = self.get_url()
        if not stream_url:
            console.print("[bold red]Impossible de récupérer l'URL du flux[/bold red]")
            return

        self.record_time += 13  # Ajouter un temps supplémentaire pour la publicité, si nécessaire

        segment_duration = 60  # Durée maximale d'un segment en secondes
        num_segments = (self.record_time + segment_duration - 1) // segment_duration  # Calcul du nombre de segments nécessaires


        for segment in range(num_segments):
            segment_start_time = segment * segment_duration
            segment_length = min(segment_duration, self.record_time - segment_start_time)

            # Formatage du nom de fichier avec l'heure actuelle et le numéro de segment
            timestamp_complet = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d")

            # output_file_path = os.path.join(in_record_directory, f"{timestamp}_{segment}.mp3")
            # final_output_file_path = os.path.join(output_directory, f"{timestamp}_{segment}.mp3")

            output_file_path = os.path.join(in_record_directory, f"{timestamp}_%03d.mp3")
            final_output_file_path = os.path.join(output_directory, f"{timestamp_complet}.mp3")



            self.hprint("green", f"start record  {segment + 1}/{num_segments}")

            command = [
                'ffmpeg', '-i', stream_url, '-ss', str(segment_start_time), 
                '-t', str(segment_length), '-vn', '-acodec', 'libmp3lame', 
                '-loglevel', 'error', output_file_path
            ]


            command = ['ffmpeg','-i', stream_url,'-vn','-acodec','libmp3lame','-ar','44100','-ac','2','-map','0:a','-f','segment','-segment_time','60','-segment_format','mp3',output_file_path,'-loglevel', 'error']
            

            # command = "ffmpeg -i "+stream_url+" -vn -acodec libmp3lame -ar 44100 -ac 2 -map 0:a -f segment -segment_time 60 -segment_format mp3 "+output_file_path+" -loglevel error"


            self.hprint('yellow',str(command))

            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            output, error = process.communicate()

            if process.returncode == 0:
                shutil.move(output_file_path, final_output_file_path)
                self.hprint("green", f"record finsih {segment + 1} saved : '{final_output_file_path}")
                
            else:
                self.hprint("red" ,f"Error on record_ segment {segment + 1}: {error}")





    def main(self):
        self.all_proxies = self.get_proxies()

        record_thread = Thread(target=self.record_audio)
        record_thread.start()
        record_thread.join()  # Wait for the recording to finish

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
