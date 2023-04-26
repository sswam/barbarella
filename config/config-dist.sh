CHATPATH=$ALLEMANDE_HOME/rooms

user=${USER^}
bot=Ally
room=chat
file=$CHATPATH/$room.bb
mission=$'system:\tYou are friends and co-workers talking face to face and working enthusiastically together.'
add_prompts=1   # 1
rewind=2

#speak="speak.py --model coqui:tts_models/en/ek1/tacotron2 --tempo 1.2 --pitch 4"
speak="speak.py --model coqui:tts_models/en/ljspeech/tacotron2-DDC_ph --tempo 1.3 --pitch 3"
#speak="speak.py --model coqui:tts_models/en/ljspeech/tacotron2-DDC --tempo 1.1 --pitch 3"
#speak="speak.py --model coqui:tts_models/en/ljspeech/glow-tts --tempo 1.2 --pitch 4"
#speak="speak.py --model gtts:en:co.uk --tempo 1.3 --pitch -1"
