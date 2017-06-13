import json
import requests
import time
import urllib
import logging

TOKEN = "386823692:AAFGIZvCUw7AVXIhxLICHIjeLNetgeO3mfw"
URL = "https://api.telegram.org/bot{}/".format(TOKEN)
global professors
global students
global break_requests

professors = [164399314]
students = []
break_requests = []

logger = logging.getLogger('myapp')
hdlr = logging.FileHandler('/Users/Julia/Documents/HHZ/Semester 2/Internet of Things/Hackathon/Python_Skript/logs/TelegramBot.log')
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr)
logger.setLevel(logging.INFO)

def get_url(url):
    response = requests.get(url)
    content = response.content.decode("utf8")
    return content

def get_json_from_url(url):
    content = get_url(url)
    js = json.loads(content)
    return js

def get_updates(offset=None):
    url = URL + "getUpdates?timeout=10"
    if offset:
        url += "&offset={}".format(offset)
    js = get_json_from_url(url)
    return js

def get_last_update_id(updates):
    update_ids = []
    for update in updates["result"]:
        update_ids.append(int(update["update_id"]))
    return max(update_ids)
         
def get_last_chat_id_and_text(updates):
    num_updates = len(updates["result"])
    last_update = num_updates - 1
    text = updates["result"][last_update]["message"]["text"]
    chat_id = updates["result"][last_update]["message"]["chat"]["id"]
    return (text, chat_id)

def register(user_id):
    global students
    students.append(user_id)

def unregister(user_id):
    global students
    students.remove(user_id)

def send_message(text, chat_id, reply_markup=None):
    text = urllib.parse.quote_plus(text)
    url = URL + "sendMessage?text={}&chat_id={}&parse_mode=Markdown".format(text, chat_id)
    if reply_markup:
        url += "&reply_markup={}".format(reply_markup)
    get_url(url)

def send_message_to_all(text, reply_markup=None):
    global professors, students
    text = urllib.parse.quote_plus(text)
    chat_ids = professors + students
    for i in chat_ids:
        url = URL + "sendMessage?text={}&chat_id={}&parse_mode=Markdown".format(text, i)
        if reply_markup:
            url += "&reply_markup={}".format(reply_markup)
        get_url(url)
        
def set_state(entityID, value):
    url = "http://192.168.1.135:8123/api/states/" + entityID
    r = requests.post(url, json=value)
    
def toggle_button(info):
    r = requests.post("http://192.168.1.135:8123/api/services/input_boolean/toggle", json=info)
    
def lectureButtontoggled():
    resp = requests.get("http://192.168.1.135:8123/api/states/input_boolean.stopwatch")
    response = json.loads(resp.text)
    if response['state'] == "on":
        send_message_to_all("the lecture has been stopped")
        break_requests.clear()
    else:
        send_message_to_all("the lecture has started")
    
def build_keyboard():
    #keyboard = [[item] for item in items]
    keyboard = ['breakrequest']
    #reply_markup = {"keyboard":keyboard, "one_time_keyboard": True}
    reply_markup = {"keyboard":keyboard, "one_time_keyboard": False}
    return json.dumps(reply_markup)

def handle_updates(updates):
    global professors, students, break_requests
    for update in updates["result"]:
        try:
            text = update["message"]["text"]
            chat = update["message"]["chat"]["id"]
            user = update["message"]["from"]["id"]
            chat_ids = professors + students
            if text == "/break":
                if user in break_requests:
                    send_message("already requested break earlier", chat)
                    logger.info("A user tried to request a break. Request was denied due to existing request.")
                elif user in chat_ids:
                    info = {"entity_id": "input_boolean.breakrequest"}
                    toggle_button(info)
                    send_message("break requested", chat)
                    break_requests.append(user)
                    logger.info("A user tried to request a break.")
                else:
                    send_message("please register as a student via /register in order to be able to request a break", chat)
            elif text == "/start_lecture":
                if user in professors:
                    value = {"attributes": {"friendly_name": "Lecture"}, "state": "on"}
                    set_state("input_boolean.stopwatch", value)
                    #send_message_to_all("the lecture has started")
                    #logger.info("A professor started the lecture.")
                else:
                    send_message("only professors are allowed to use this function", chat)
                    logger.info("A student tried to start the lecture. Request was denied.")
            elif text == "/stop_lecture":
                if user in professors:
                    value = {"attributes": {"friendly_name": "Lecture"}, "state": "off"}
                    set_state("input_boolean.stopwatch", value)
                    break_requests.clear()
                    #send_message_to_all("the lecture has stopped")
                    #logger.info("A professor stopped the lecture.")
                else:
                    send_message("only professors are allowed to use this function", chat)
                    logger.info("A student tried to stop the lecture. Request was denied.")
            elif text == "/register":
                if user in students:
                    send_message("you are already registered as a student", chat)
                    logger.info("A student tried to register a second time. Request was denied.")
                #elif user in professors:
                    #send_message("you are already registered as a professor", chat)
                    #logger.info("A professor tried to register as a student. Request was denied.")
                else:
                    send_message("you are now registered as a student", chat)
                    logger.info("A new student registered.")
                    register(user)
            elif text == "/unregister":
                if user in students:
                    unregister(user)
                    send_message("you are no longer registered as a student. you will not receive further notifications", chat)
                    logger.info("A student unregistered.")
                elif user in professors:
                    send_message("you are registered as a professor. you cannot unregister via this button", chat)
                    logger.info("A professor tried to unregister as a student. Request was denied.")
                else:
                    send_message("you were not registered in the first place", chat)
                    logger.info("Someone not registered tried to unregister. Request was denied.")
            elif text == "/buttontoggled":
                resp = requests.get("http://192.168.1.135:8123/api/states/input_boolean.stopwatch")
                response = json.loads(resp.text)
                if response['state'] == "on":
                    send_message_to_all("the lecture was started")
                    logger.info("the lecture button was started")
                if response['state'] == "off":
                    send_message_to_all("the lecture was ended")
                    logger.info("the lecture button was ended")
            else:
                send_message("invalid input. please use one of the commands found under /", chat)
                logger.info("Invalid input.")
        except Exception as e:
                print(e)
    
    
def main():
    last_update_id = None
    response1 = None
    keyboard = build_keyboard()
    while True:
        updates = get_updates(last_update_id)
        if len(updates["result"]) > 0:
            last_update_id = get_last_update_id(updates) + 1
            handle_updates(updates)
            time.sleep(1)
        resp = requests.get("http://192.168.1.135:8123/api/states/input_boolean.stopwatch")
        response = json.loads(resp.text)
        if response['state'] == response1: 
            pass
        else:
            response1 = response['state']
            update = {'ok': True, 'result': [{'update_id': 0, 'message': {'message_id': 765, 'from': {'id': 0, 'first_name': 'J', 'language_code': 'de-DE'}, 'text': '/buttontoggled', 'chat': {'type': 'private', 'id': 0, 'first_name': 'J'}, 'date': 1497357549, 'entities': [{'offset': 0, 'type': 'bot_command', 'length': 6}]}}]}
            handle_updates(update)
            
    
if __name__ == '__main__':
        main()