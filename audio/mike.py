#!/usr/bin/env python3
""" Transcribe speech to text using microphone input and whisper """

import sys
import io
from threading import Thread, Event
from queue import Queue
import logging
from contextlib import contextmanager
from pathlib import Path
import argparse

import argh
from pydub import AudioSegment
import speech_recognition as sr
import yaml

import ucm
import allemande

logger = logging.getLogger(__name__)

server = "stt_whisper"
default_port = allemande.get_default_port(server)

opts = None


@contextmanager
def open_microphone_spamfree(*args, **kwargs):
	""" Open microphone without spamming stderr """
	try:
		with ucm.redirect_stderr_to_dev_null():
			source = sr.Microphone(*args, **kwargs).__enter__()  # pylint: disable=unnecessary-dunder-call
		yield source
	finally:
		source.__exit__(None, None, None)

def record_speech(run_event, q_audio, energy, pause, dynamic_energy, device_index, adjust_for_ambient_noise=False):
	""" Record audio from microphone and put it in the queue """
	r = sr.Recognizer()
	r.energy_threshold = energy
	r.pause_threshold = pause
	r.dynamic_energy_threshold = dynamic_energy
	i = 0

	if opts.log_level <= logging.DEBUG:
		open_microphone = sr.Microphone
	else:
		open_microphone = open_microphone_spamfree

	first = True

	with open_microphone(sample_rate=16000, device_index=device_index) as source:
		while run_event.is_set():
#			drop = os.path.isfile("/tmp/drop-the-mic")
			if adjust_for_ambient_noise:
				logger.debug("Adjusting for ambient noise")
				r.adjust_for_ambient_noise(source)
			if first:
				logger.info("Listening")
				first = False
			else:
				logger.debug("Listening")
			audio = r.listen(source)
			logger.debug("Got audio")
#			if not drop and not os.path.isfile("/tmp/drop-the-mic"):
			q_audio.put_nowait(audio)
			i += 1
	q_audio.put_nowait(None)


def client_request(port, audio, config=None):
	""" Call the core server and get a response. """

	req = allemande.prepare_request(port, config=config)

	req_audio = req/"request.aud"

	data = io.BytesIO(audio.get_wav_data())
	audio_clip = AudioSegment.from_file(data)
	audio_clip.export(str(req_audio), format="flac")

	allemande.send_request(port, req)

	resp, status = allemande.wait_for_response(port, req)

	if status == "error":
		allemande.response_error(resp)

	text = (resp/"text.txt").read_text()
	result = yaml.safe_load((resp/"result.yaml").read_text())

	logger.info("%r", result)

	allemande.remove_response(port, resp)

	return text, result


def speech_to_text(port, run_event, q_audio, q_text, lang):
	""" Transcribe from the audio queue to the text queue """

	config = {
		"language": lang,
	}

	while run_event.is_set():
		audio = q_audio.get()

		if audio is None:
			break

#		np_audio = np.frombuffer(audio.get_raw_data(), np.int16)
#		np_audio = np_audio.flatten().astype(np.float32) / 32768.0
#		torch_audio = torch.from_numpy(np_audio)

		text, result = client_request(port, audio, config=config)

#		result = whisp.transcribe(torch_audio, language=lang)

		logger.info(result)
		text = text.strip()
		segs = result["segments"]
		no_speech_prob = sum(x["no_speech_prob"] for x in segs) / (len(segs) or 1)
		if text and no_speech_prob < 0.5:
			q_text.put_nowait(text)

	q_text.put_nowait(None)


def do_list_devices():
	""" List available microphone devices """
	for index, name in enumerate(sr.Microphone.list_microphone_names()):
		print(f'{index}\t{name}')


def mike(lang="en", energy=1200, dynamic_energy=False, pause=0.8, device_index=None, list_devices=False, adjust_for_ambient_noise=False, port=default_port):
	""" Transcribe speech to text using microphone input """

	if list_devices:
		do_list_devices()
		sys.exit(0)

	port = Path(port)

	run_event = Event()
	run_event.set()

	try:
		q_audio = Queue()
		q_text = Queue()
		Thread(
			target=record_speech,
			args=(run_event, q_audio, energy, pause, dynamic_energy, device_index, adjust_for_ambient_noise)
			).start()
		Thread(
			target=speech_to_text,
			args=(port, run_event, q_audio, q_text, lang)
			).start()
		while True:
			text = q_text.get()
			if text is None:
				break
			print(text)
			sys.stdout.flush()
	except KeyboardInterrupt:
		logger.exception("Interrupted!")
	finally:
		run_event.clear()

# TODO factor out this main biolerplate stuff

if __name__ == '__main__':
	parser = argparse.ArgumentParser()
	argh.add_commands(parser, [mike])
	argh.set_default_command(parser, mike)
	ucm.add_logging_options(parser)
	opts = parser.parse_args()
	ucm.setup_logging(opts)
	argh.dispatch(parser)
