import subprocess
from typing import Optional
import requests
import re
import os
import time
import zipfile
import platform

def download_file(url, filename):
    if os.path.isfile(filename):
        return
    print(f"Download del file: {filename}")
    r = requests.get(url, allow_redirects=True)
    with open(filename, 'wb') as f:
        f.write(r.content)
    r.close()

def run_lavalink(
    lavalink_file_url: Optional[str] = None,
    lavalink_initial_ram: int = 30,
    lavalink_ram_limit: int = 100,
    lavalink_additional_sleep: int = 0,
    lavalink_cpu_cores: int = 1,
):

    download_java = False

    if os.path.isdir("./.java"):
        java_path = "./.java/jdk-13/bin/"
    else:
        java_path = os.environ.get('JAVA_HOME', '')
        if java_path:
            java_path = java_path.replace("\\", "/") + "/bin/"

    try:
        javaInfo = subprocess.check_output(f'"{java_path}java"' + ' -version', shell=True, stderr=subprocess.STDOUT)
        javaVersion = re.search(r'"[0-9._]*"', javaInfo.decode().split("\r")[0]).group().replace('"', '')
        if (ver := int(javaVersion.split('.')[0])) < 11:
            print(f"La versione di java/jdk installata/configurata non è compatibile: {ver} (Versione richiesta: 11+)")
            download_java = True
    except Exception as e:
        print(f"Errore durante l'ottenimento della versione java: {repr(e)}")
        download_java = True

    downloads = {
        "Lavalink.jar": lavalink_file_url,
        "application.yml": "https://github.com/zRitsu/LL-binaries/releases/download/0.0.1/application.yml"
    }

    if download_java:

        if platform.architecture()[0] != "64bit":
            raise Exception("Devi avere installato JDK 11 o superiore!")

        if os.name == "nt":
            jdk_url, jdk_filename = ["https://download.java.net/openjdk/jdk13/ri/openjdk-13+33_windows-x64_bin.zip",
                                     "java.zip"]
            download_file(jdk_url, jdk_filename)
            with zipfile.ZipFile(jdk_filename, 'r') as zip_ref:
                zip_ref.extractall("./.java")

            os.remove(jdk_filename)

        else:
            jdk_url, jdk_filename = ["https://download.java.net/openjdk/jdk13/ri/openjdk-13+33_linux-x64_bin.tar.gz",
                                     "java.tar.gz"]
            download_file(jdk_url, jdk_filename)
            os.makedirs("./.java")
            p = subprocess.Popen(["tar", "-zxvf", "java.tar.gz", "-C", "./.java"])
            p.wait()
            os.remove(f"./{jdk_filename}")

        java_path = "./.java/jdk-13/bin/"

    for filename, url in downloads.items():
        download_file(url, filename)

    cmd = f'{java_path}java'

    if lavalink_cpu_cores >= 1:
        cmd += f" -XX:ActiveProcessorCount={lavalink_cpu_cores}"

    if lavalink_ram_limit > 10:
        cmd += f" -Xmx{lavalink_ram_limit}m"

    if lavalink_initial_ram > 0 and lavalink_initial_ram < lavalink_ram_limit:
        cmd += f" -Xms{lavalink_ram_limit}m"

    cmd += " -jar Lavalink.jar"

    print(f"Avvio del server Lavalink (a seconda dell'hosting, l'avvio di lavalink potrebbe richiedere del tempo, "
          f"potrebbero volerci diversi tentativi prima che si avvii completamente).\n{'-'*30}")

    subprocess.Popen(cmd.split(), stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)

    if lavalink_additional_sleep:
        print(f"Aspetta {lavalink_additional_sleep} secondi...\n{'-'*30}")
        time.sleep(lavalink_additional_sleep)
