from pyAudioAnalysis.audioSegmentation import mid_term_file_classification, evaluate_speaker_diarization, speaker_diarization,hmm_segmentation
from pydub import AudioSegment    
from scipy.io import wavfile
import os
import time
from IPython.display import clear_output, Audio
import speech_recognition as sr


def audio_crop_and_slowdown(start, end, old_file, new_file, mag, fmt='wav'):
    '''
    Function to crop out audio file based on given start and end segments. It also slows down the audio file by the given magnitude.
        
    Parameters:
    -------------
    start: Starting position of the audio file that needs to be cropped.
    
    end: Ending position of the audio file that needs to be cropped.
    
    old_file: The audio file from which a segment will be cropped. 
    
    new_file: Destination path to save cropped out audio segment.
    
    mag = Percentage of the actual speed required.
    
    fmt: default: 'wav'. Audio file type or format.
    
    
    Returns:
    -------------
    None. Only stores the audio file into the target destination/
    '''
    try:
        wav_file = AudioSegment.from_file(old_file)   #takes in audio input
        crop_file = wav_file[start:end]  #crops out audio segment from input audio
        slow_sound = speed_change(crop_file, mag)
        slow_sound.export(new_file, format=fmt) #stores it into destination folder
    except Exception as e:
        print('Could not crop audio file ' + old_file) #error possibly due to incorrect paths and/or invalid start or end egments
        
        
        
def speed_change(sound, speed=1.0):
    
    '''
    Function to override the frame_rate. This tells the computer how many samples to play per second. Basically, slows down the input audio file by the given hyperparameter.
    
    Parameters:
    ---------------
    sound: pydub.Audiosegment file that needs change in speed.
    speed: change in speed. Default:1.0
    
    Returns:
    ---------------
    Speed-altered audiosegment
    '''
    
    sound_with_altered_frame_rate = sound._spawn(sound.raw_data, overrides={
        "frame_rate": int(sound.frame_rate * speed)
    })

    # convert the sound with altered frame rate to a standard frame rate
    # so that regular playback programs will work right. They often only
    # know how to play audio at standard frame rate (like 44.1k)
    return sound_with_altered_frame_rate.set_frame_rate(sound.frame_rate)


    
def non_speech_removal(a):
    
    """
    Function to remove non-speech segments like music, silence, etc. from audio.
    
    Parameters:
    -----------------
    a: Input audio file path
    
    Returns:
    -----------------
    Audiosegment with only speech.
    """
    
    
    #Uses a knn model to identify is there is speech or a music/silence in the audio file at every second.
    #Extracts timestamps for those segments where there is music/silence.
    #Using that extracts segments where there is only speech.
    #Joins all speech segments together to form a new audio file ith only speech
    #Return the new audio.
    
    
    [flagsInd, classesAll, acc, CM] = mid_term_file_classification(a, "knn_sm", "knn")
    t = []
    for sec, flag in enumerate(flagsInd):
        if flag == 1:
            t.append(sec)   

    sound = AudioSegment.from_mp3(a)
    print(len(sound))
    multiplier = (len(sound)/len(flagsInd))
    start = 0
    end = 0
    diff = 5
    times = []
    for i in range(1,len(t)):
        #print(t[i]-t[i-1])
        if t[i]-t[i-1]>diff:
            if end>0 and end-start>10:
                times.append([start*multiplier, (end)*multiplier])           
            start = t[i-1]
            end = t[i-1]
        else:
            end = t[i]

    new_times=[]
    for i in range(1, len(times)):
        if i==1 and times[i-1][0]>0:
            new_times.append([0, times[i-1][0]])
        new_times.append([times[i-1][1],times[i][0]])
        if times[i][1]<len(sound) and i == len(times)-1:
            new_times.append([times[i][1],len(sound)])
    if len(new_times)==0:
        newsound=sound
    else:
        newsound = sound[0:0]
        for t in new_times:
            newsound+=sound[t[0]:t[1]]
        
    return newsound


def diarization(audio, mid_step, label_c, p_thresh, delay):
    """
    Function to identify who the current speaker is at any given time.
    Creates a list where 0 is customer and 1 is executive.
    
    Parameters:
    -----------------
    
    audio: Input audio path
    
    mid-step: Number of Seconds when identification is happening. Default = 0.4. It basically means, every 0.4 seconds speaker is identified.
    
    
    Returns:
    -----------------
    
    A list of timestamps which has the time recorded for every major change in speaker monologues.
    
    A dictionary consisting of two keys: executive and customer. The value of each key is a list of order sequence in which the speaker is speaking. 
    
    """
    op = speaker_diarization(audio, 2, mid_step=mid_step, lda_dim=0)
    sound = AudioSegment.from_wav(audio)
    label_e = int(not(label_c))
    op = op.astype('int')
    multiplier = (len(sound)/len(op))
    order = {'Executive': list(), 'Customer': list()}
    timestamp = [0]
    c = 0
    p=0
    for sec,i in enumerate(op):
        p+=1
        if op[sec]!=op[sec-1]:
            if p>p_thresh:
                timestamp.append((sec+delay)*multiplier)
                if op[sec-1] == label_c:
                    order['Customer'].append(c)
                elif op[sec-1] == int(not(label_c)):
                    order['Executive'].append(c)
                c+=1
            p=0
    return timestamp, order   
    
    
    
def crop_and_slowdown(timestamp, destination, mag):
    """
    A fucntion that segments and slows down an audio file into multiple audio files .
    
    Parameters:
    ----------------
    
    timestamp: the list of timestamps where every major change in speaker monologue is recorded.
    
    destination: Input audio file path.
    
    mag: slowing down magnitude parameter.
    
    
    Returns:
    ----------------
    None. Only stores the segmented files into the output file path.
    
    """
    
    
    for i in range(1, len(timestamp)):
        outfile = f"cropped/seg{i}.wav"
        audio_crop_and_slowdown(timestamp[i-1], timestamp[i], destination, outfile, mag)
    

def convert_speech_to_audio(num_files, order, lang):

    
    """
    Speech to Text and Script Conversion Function.
    
    Parameters:
    ---------------
    
    num_files: number of speaker changes. (length of the timestamps list)
    
    order: dictionary of order sequence of each speaker.
    
    
    
    Returns:
    Generated Script
    
    """
    person=''
    script=''
    language = ''
    if lang=='hindi':
        language = 'hi-IN'
#         hin = True
    elif lang=='english':
        language = 'en-IN'
    for i in range(1,num_files):
        if any(pos==i-1 for pos in order['Executive']):
            person = 'Executive: '
        else:
            person= 'Customer: '
        AUDIO_FILE=f"cropped/seg{i}.wav"
        r = sr.Recognizer()
        with sr.AudioFile(AUDIO_FILE) as source:
            r.adjust_for_ambient_noise(source)
            #r.energy_threshold(50)
            audio = r.record(source)  # read the entire audio file

        # recognize speech using Google recoginzer
        try:
#             if hin == True:
#                 hindi_text = r.recognize_google(audio, language=language)
#                 tr = Translator()
#                 t = tr.translate(hindi_text,src = 'hi')
#                 eng_text = t.text
#             else:
#                 eng_text = r.recognize_google(audio, language=language)
#             script += person + eng_text + '\n\n'
            script +=  person + r.recognize_google(audio, language=language) + '\n\n'
        except sr.UnknownValueError:
            pass
            #print(color.BOLD + "Recignizer could not understand audio" + color.END, "\n")
        except sr.RequestError as e:
            print("Recognizer error; {0}".format(e), '\n')
        if os.path.exists(AUDIO_FILE):
            os.remove(AUDIO_FILE)            
    return script

def generate_script_from_audio(filepath, mid_step=0.37, p_thresh=5, mag = 0.825, delay=0 , label_c=0, lang = 'english'):
    
    """
    Main Function where all helper functions are amalgamated.
    
    For parameter explanation, refer to helper functions above.
    
    Returns:
    --------------
    Script
    
    
    NOTE:
    To view the script:
    print(generate_script_from_audio(audio_path))
    
    """
    
    destination = "cropped/converted.wav"
    sound = non_speech_removal(filepath)
    sound.export(destination, format="wav")
    timestamp, order = diarization(destination, mid_step, label_c, p_thresh, delay)
    num_files=len(timestamp)
    crop_and_slowdown(timestamp, destination, mag)
    if os.path.exists(destination):
        os.remove(destination)  
    return convert_speech_to_audio(num_files, order, lang)


def store_into_txt(script, audio_path):
    text_file = open(f"Hindi_scripts/{audio_path[35:-4]}.txt", "w")
    n = text_file.write(script)
    text_file.close()
    print('File saved!')