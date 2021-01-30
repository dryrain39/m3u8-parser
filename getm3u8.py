import time

import requests
import logging
from pathlib import Path
import os
import subprocess
from config import *

logging.getLogger().setLevel(logging.INFO)

url = input("PUT TRACK URL: ")
url = url.strip()

logging.info("Logging in...")
s = requests.Session()

s.headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) ' \
                          'Chrome/74.0.3729.169 Safari/537.36'

r = s.post(URL.auth, data={
    "email": Account.id,
    "password": Account.pw,
    "remember": True
})

s.get(URL.main)

logging.info("Reading URL")

music_id = url.split("/")[4]

m = s.get(f"{music_id}", headers={"accept": "application/json, text/plain, */*"})
music_data = m.json()

logging.info(f"Found {music_data['track']['name']}.")

file_name = music_id
base_url = URL.base + "/".join(music_data["track"]["url"].split("/")[:-1]) + "/"
logging.info(f"File name: {file_name}, Base_url: {base_url}")
Path(f"./output/{file_name}").mkdir(parents=True, exist_ok=True)

m3u8_data = s.get(URL.base + music_data["track"]["url"]).text

if not m3u8_data.startswith("#EXTM3U"):
    logging.error("Parsing failed! Response is not M3U8 file!")
    logging.error(m3u8_data)

m3u8_data_lines = m3u8_data.strip().split("\n")

key_files = []
tm3a_files = []

data_p_mode = False

for idx, line in enumerate(m3u8_data_lines):
    p_text = f"[{int((1 if idx is 0 else idx) / len(m3u8_data_lines) * 100)}%]"
    if data_p_mode:
        success = False
        while not success:
            data = s.get(f"{base_url}{line}")
            logging.info(f"{p_text} Downloading line {idx}, tm3a file.")
            if data.text.startswith('{"'):
                logging.info(f"{p_text} Downloading error. Retry. {base_url}{line}")
                time.sleep(1)
                continue
            open(f"./output/{file_name}/{str(len(tm3a_files))}.tm3a", "wb").write(data.content)
            success = True
            data_p_mode = False
            tm3a_files.append(line)

    if line.startswith("#EXT-X-KEY"):
        key = line.split("URI=\"")[1].split("\"")[0]

        if key not in key_files:
            key_response = s.get(key)
            logging.info(f"{p_text} Downloading line {idx}, key file.")
            open(f"./output/{file_name}/{str(len(key_files))}.key", "wb").write(key_response.content)
            key_files.append(key)

    if line.startswith("#EXTINF"):
        data_p_mode = True

logging.info("Replacing to local files...")

new_m3u8_data = "\n".join(m3u8_data_lines)

for idx, key in enumerate(key_files):
    logging.info(f"{key} --> {str(idx)}.key")
    new_m3u8_data = new_m3u8_data.replace(key, f"{str(idx)}.key")

for idx, tm3a in enumerate(tm3a_files):
    logging.info(f"{tm3a} --> {str(idx)}.tm3a")
    new_m3u8_data = new_m3u8_data.replace(tm3a, f"{str(idx)}.tm3a")

open(f"./output/{file_name}/{file_name}.m3u8", "w").write(new_m3u8_data)

logging.info("Execute ffmpeg...")
time.sleep(1)
os.chdir('ffmpeg')
subprocess.call(['ffmpeg', '-allowed_extensions', 'ALL', '-i', f"../output/{file_name}/{file_name}.m3u8", "-c", "copy",
                 f"../output/{file_name}/{file_name}.aac"])

logging.info(f"Done! ./output/{file_name}/{file_name}.aac")
