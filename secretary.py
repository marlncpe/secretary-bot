#!/usr/bin/env python
import os
import sys
import time
import telepot
import storage
import configuration
from Queue import Queue
from urlparse import urlparse
from datetime import datetime
from video_downloader import VideoDownloader
from secretary_exceptions import *
from meditation import *
from classifier import MessageClassifier
from representations import write_html

def handle(msg):
    global storage
    global bot
    global video_hostings
    global video_download_queue
    global video_downloader_thread
    content_type, chat_type, chat_id = telepot.glance(msg)
    print content_type, chat_type, chat_id

    if content_type != 'text': return
    msg_lowercase = msg['text'].strip().lower()
    words = msg_lowercase.split()

    if msg_lowercase == '/digest':
        classes = storage.digest(chat_id, MessageClassifier())
        filename = configuration.get("digest_dir") + "/" + "-".join(str(datetime.utcnow()).split()) + ".html"
        write_html(classes, filename)
        bot.sendChatAction(chat_id, 'upload_document')
        bot.sendDocument(chat_id, open(filename, 'rb'))
    elif msg_lowercase == '/pause':
        video_downloader_thread.pause()
    elif msg_lowercase == '/resume':
        video_downloader_thread.resume()
    elif len(words) > 0 and words[0] == "/meditate":
        try:
            meditation_manager.meditate(*words[1:2])
        except MeditationException as e:
            bot.sendMessage(chat_id, str(e))
        except Exception as e:
            print str(e)
    elif urlparse(msg['text']).netloc.lower().replace("www.", "") in video_hostings:
        # TODO: We want to store the url to the DB as well, because the download
        # process can be interrupted and we'll need to re-download.
        # One design is Downloader asking the Storage.
        video_download_queue.put(msg['text'])
    else:
        storage.store_message(msg)

video_hostings = [line[:-1] for line in open("./video-hostings.config")]
video_download_queue = Queue()
video_downloader_thread = VideoDownloader(video_download_queue)
video_downloader_thread.start()

meditation_manager = MeditationManager()

if len(sys.argv) > 1:
    configuration.add_file(sys.argv[1])

storage = storage.Storage("messages.sqlite")

digest_dir = configuration.get("digest_dir")
if not os.path.exists(digest_dir):
    os.mkdir(digest_dir)
else:
    if not os.path.isdir(digest_dir):
        raise DigestDirNotWritable(digest_dir)

token = configuration.get("token")
bot = telepot.Bot(token)
bot.message_loop(handle)

print 'Listening ...'

# Keep the program running.
while 1:
    time.sleep(10)

storage.finalize() # FIXME: unreacheable
