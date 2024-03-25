import os
import signal
import sys
import argparse
import time
import random
import requests
import datetime
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
        self.should_stop = False
        self.record_time = record_time

    def get_proxies(self):
        try:
            response = requests.get("https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all")
            if response.status_code == 200:
                lines = response.text.split("\n")
                lines = [line.strip() for line in lines if line.strip()]
                return lines
        except Exception as e:
            console.print("Error retrieving proxies: {}".format(e), style="bold red")
            return []

    def get_url(self):
        url = ""
        try:
            streams = session.streams(self.channel_url)
            url = streams['audio_only'].url if 'audio_only' in streams else streams['worst'].url
        except Exception as e:
            pass
        return url

    def stop(self):
        console.print("[bold red]record has been stopped[/bold red]")
        self.should_stop = True

    def record_audio(self):
        output_directory = "record"
        os.makedirs(output_directory, exist_ok=True)
        output_file_path = os.path.join(output_directory, "temp_output_audio.mp3")
        
        console.print("[bold green]Début de l'enregistrement audio[/bold green]")
        stream_url = self.get_url()
        if not stream_url:
            console.print("[bold red]Impossible de récupérer l'URL du flux[/bold red]")
            return

        self.record_time+=13

        #command = ['ffmpeg', '-i', stream_url, '-t', str(self.record_time), '-vn', '-acodec', 'libmp3lame', '-loglevel', 'error', output_file_path]
        #subprocess.run(command)
        #console.print(f"[bold green]Enregistrement audio terminé et sauvegardé en tant que '{output_file_path}'[/bold green]")
        # Progress counter
        
        command = ['ffmpeg', '-i', stream_url, '-t', str(self.record_time), '-vn', '-acodec', 'libmp3lame', '-loglevel', 'error', output_file_path]
        
        # Exécuter ffmpeg dans un processus séparé
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        # Compteur dynamique
        # Ici, on suppose que record_time est la durée totale d'enregistrement en secondes
        for remaining in range(self.record_time, 0, -1):
            if (remaining > self.record_time-13):
                console.print(f"[bold yellow]Enregistrement PUB... {remaining} secondes restantes[/bold yellow]", end="\r")
            else :
                console.print(f"[bold green]Enregistrement... {remaining} secondes restantes. ^^ [/bold green]", end="\r")
            time.sleep(1)
        
        # Attendre que le processus ffmpeg se termine
        output, error = process.communicate()

        if process.returncode == 0:
            console.print(f"\n[bold green]Enregistrement audio terminé et sauvegardé en tant que '{output_file_path}'[/bold green]")
        else:
            console.print(f"\n[bold red]Erreur lors de l'enregistrement : {error}[/bold red]")





        #compteur dynamique
        
        self.stop()  # Call stop method to clean up and exit after recording


    def edit_audio(self):
        output_directory = "record"
        os.makedirs(output_directory, exist_ok=True)
        
        temp_output_file_path = os.path.join(output_directory, "temp_output_audio.mp3")
        final_output_file_path = os.path.join(output_directory, "final_output_audio.mp3")
        
        # Suppression des 13 premières secondes
        console.print("[bold yellow]Suppression des 13 premières secondes de l'enregistrement[/bold yellow]")
        trim_command = ['ffmpeg', '-i', temp_output_file_path, '-ss', '13', '-acodec', 'copy', '-loglevel', 'error', final_output_file_path]
        subprocess.run(trim_command)
        
        # Suppression du fichier temporaire
        os.remove(temp_output_file_path)
        
        console.print(f"[bold green]Modification terminé et sauvegardé en tant que '{final_output_file_path}'[/bold green]")
        
        self.stop()  # Arrêter le script après l'enregistrement et le post-traitement




    def main(self):
        self.all_proxies = self.get_proxies()

        record_thread = Thread(target=self.record_audio)
        record_thread.start()
        record_thread.join()  # Wait for the recording to finish

        edit_thread = Thread(target=self.edit_audio)
        edit_thread.start()
        edit_thread.join()  # Wait for the recording to finish

        console.print("[bold green]Enregistrement terminé, le programme va se terminer.[/bold green]")
        self.stop()  # Ensure any cleanup is done

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
        bot.stop()
