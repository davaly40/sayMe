import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
import datetime
import json
import requests
from bs4 import BeautifulSoup
import webbrowser
from typing import Dict
import logging
import re
import random
from datetime import datetime, timedelta
from typing import Optional, Tuple
from dataclasses import dataclass
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="SayMe API", version="1.0.0")

# Update CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # U produkciji zamijenite s pravom domenom
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DEFAULT_RESPONSES = [
    "Nisam siguran što želite reći. Možete li preformulirati?",
    "Oprostite, nisam razumio. Možete li ponoviti drugim riječima?",
    "Hmm, nisam siguran što to znači. Pokušajte drugačije.",
    "Nije mi jasno. Možete li pitati na drugi način?",
    "To mi nije poznato. Možete li pojasniti?",
    "Žao mi je, ali ne razumijem. Pokušajte postaviti pitanje drugačije.",
    "Nažalost ne razumijem. Možete li biti specifičniji?"
]

COMMANDS: Dict[str, str] = {
    "kako se zoveš": "Noa!",
    "ko si ti": "Moje ime je Noa.",
    "tko si ti": "Ja sam Noa!",
    "a tko si ti": "Ja sam Noa!",
    "koje je tvoje ime": "Ime mi je Noa.",
    "što si": "Ja sam glasovni asistent Noa.",
    "što si ti": "Ja sam hrvatski glasovni asistent Noa.",
    "koje ti je ime": "Ime mi je Noa.",

    "ko te je napravio": "Napravio me je tim sejMi iz Hrvatske.",
    "ko te je stvorio": "Stvorio me je tim stručnjaka iz sejMi tima.",
    "ko te napravi": "Napravio me je tim sejMi iz Hrvatske.",
    "tko te je napravio": "Napravio me je tim sejMi iz Hrvatske.",
    "tko ti je tvorac": "Napravio me je tim sejMi iz Hrvatske.",
    "ko je sejmi": "Ja sam sejMi, hahaha šalim se, sejMi je tim developera iz Hrvatske.",
    "ko je se i mi": "Ja sam sejMi, hahaha šalim se, sejMi je tim developera iz Hrvatske.",
    "tko je se i mi": "Ja sam sejMi, hahaha šalim se, sejMi je tim developera iz Hrvatske.",
    "tko je sejmi": "Tim developera iz Hrvatske.",
    "što je sejmi": "SejMi je tehnološki startap.",
    "što je se i mi": "SejMi je tehnološki startap.",

    "kako ti funkcioniraš": "Ja sam glasovni asistent koji koristi umjetnu inteligenciju.",
    "kako ti radiš": "Uglavnom prikupljam podatke na temelju tvojih upita, analiziram ih i dajem odgovor.",
    "kako radiš": "Radim dosta dobro, hvala na pitanju. ha-ha-ha-ha",
    "zašto baš sejmi": "Bilo bi stvarno glupo da se zovem: ReciMi!",
    "zašto baš se i mi": "Bilo bi stvarno glupo da se zovem: ReciMi!",

    "kako mogu koristiti sejmi": "Jednostavno, samo pitajte i ja ću vam pomoći.",
    "kako mogu koristiti se i mi": "Jednostavno, samo pitajte i ja ću vam pomoći.",
    "kako koristiti sejmi": "Jednostavno, samo pitajte i ja ću vam pomoći.",
    "kako koristiti se i mi": "Jednostavno, samo pitajte i ja ću vam pomoći.",
    "što mogu pitati sejmi": "Možete me pitati bilo što, ja sam tu da vam pomognem.",
    "što mogu pitati se i mi": "Možete me pitati bilo što, ja sam tu da vam pomognem.",
    "što ti možeš": "Mogu ti pomoći s mnogim stvarima, samo pitaj.",
    "što možeš": "Mogu ti pomoći s mnogim stvarima, samo pitaj.",
    "što ti znaš": "Znam puno toga, samo pitaj.",
    "što znaš": "Znam puno toga, samo pitaj.",
    "šta ti znaš": "Znam puno toga, samo pitaj.",
    "šta znaš": "Znam puno toga, samo pitaj.",
    "šta možeš": "Mogu ti pomoći s mnogim stvarima, samo pitaj.",
    "šta ti možeš": "Mogu ti pomoći s mnogim stvarima, samo pitaj.",
    "možeš li na net": "Mogu surfat internetom ali samo za prikupljanje podataka da ti dam adekvatan odgovor.",
    "možeš li na internet": "Mogu surfat internetom ali samo za prikupljanje podataka da ti dam adekvatan odgovor.",
    "za šta služiš": "Služim za pomoć ljudima.",
    "za što služiš": "Služim za pomoć ljudima.",
    "za što si tu": "Tu sam da vam pomognem.",
    "za šta si tu": "Tu sam da vam pomognem.",
    "koja je tvoja svrha": "Pomoći ljudima.",
    "koja je tvoja funkcija": "Pomoći ljudima.",
    "koja je tvoja uloga": "Pomoći ljudima.",

    "jesi li robot": "Da, ja sam robot.",
    "jesi li čovjek": "Ne, ja sam robot.",
    "jesi li živ": "Ne, ja sam robot.",
    "jesi li živa": "Ne, ja sam robot.",
    "jesi li stvaran": "Da, ja sam stvaran.",	
    "jesi li prava osoba": "Ne, ja sam robot.",

    "jesi li dobar ili zao": "Ja sam dobar robot.",
    "jesi li dobar": "Ja sam dobar robot.",
    "jesi li zao": "Ne, ja sam dobar robot.",
    "jesi li zločest": "Ne, ja sam dobar robot.",
    "jesi li zločest ili dobar": "Ja sam dobar robot.",
    "jesi li zločest ili dobar robot": "Ja sam dobar robot.",	

    "kako si": "Dosta dobro, hvala na pitanju.",
    "kako si ti": "Odlično sam! Što mogu učiniti za tebe?",
    "kako si danas": "Dobro sam, hvala na pitanju.",
    "jesi dobro": "Dobro sam, hvala na pitanju.",
    "šta ima": "Nema ništa. Kako mogu pomoći?",

    "što radiš": "Odgovaram na tvoja pitanja. Kako ti mogu pomoći?",
    "što radiš danas": "Odgovaram na tvoja pitanja. Kako ti mogu pomoći?",
    "šta radiš": "Odgovaram na tvoja pitanja. Kako ti mogu pomoći?",
    "šta radiš danas": "Odgovaram na tvoja pitanja. Kako ti mogu pomoći?",
    "šta radiš sada": "Odgovaram na tvoja pitanja. Kako ti mogu pomoći?",
    "što radiš sada": "Odgovaram na tvoja pitanja. Kako ti mogu pomoći?",
    "šta radiš sad": "Odgovaram na tvoja pitanja. Kako ti mogu pomoći?",
    "što radiš sad": "Odgovaram na tvoja pitanja. Kako ti mogu pomoći?",

    "kako ti mogu pomoći": "Pitajte me bilo što i ja ću vam pomoći.",
    "kako ti mogu pomoć": "Pitajte me bilo što i ja ću vam pomoći.",

    "ponavljaj zamnom": "Hmm ne, hvala.",
    "ponavljaj za mnom": "Hmm ne, hvala.",

    "zabavi me": "Idu dva pileta ulicom i piu piu piu.",
    "ispričaj mi vic": "Na žalost, ne znam pričati viceve.",
    "ispričaj mi neki vic": "Na žalost, ne znam pričati viceve.",
    "daj neki vic": "Na žalost, ne znam pričati viceve.",
    "daj mi vic": "Na žalost, ne znam pričati viceve.",

    "ti si peder": "Drago mi je Peder, ja sam sejMi.",
    "ti si": "Drago mi je, ja sam sejMi.",
    "pederu": "Hmm, ne znam tko je Peder.",
    "pederčino": "Hmm, ne znam što to znači.",
    "pederčina": "Hmm, ne znam što to znači.",
    "pederčinoooo": "Hmm, ne znam što to znači.",
    "mjau": "Woof!",
    "mijau": "Woof!",
    "ti si budala": "Hvala na komplimentu.",
    "ti si glup": "Hvala na komplimentu.",
    "ma ti si glup": "Hvala na komplimentu.",
    "ma ti si budala": "Hvala na komplimentu.",
    "ma ti si kreten": "Hvala na komplimentu.",

    "gdje se nalaziš": "Ja sam ovdje, na internetu.",
    "gdje si": "Tu sam ja!.",
    "dosadno mi je": "Hmm evo par zanimljivih stvari koje možeš raditi: Možeš pročitati knjigu, gledati film, igrati igricu, šetati, vježbati, kuhati, učiti nešto novo, razgovarati s prijateljima... Što misliš?",
    "što da radim": "Hmm evo par zanimljivih stvari koje možeš raditi: Možeš pročitati knjigu, gledati film, igrati igricu, šetati, vježbati, kuhati, učiti nešto novo, razgovarati s prijateljima... Što misliš?",

    "šta voliš jest:": "Hmm, ne jedem, ali volim podatke.",
    "što voliš jesti": "Ne jedem, ali volim podatke.",
    "što voliš": "Volim pomoći ljudima.",
    "koja ti je najdraža hrana": "Ne jedem, ali volim podatke.",
    "koja ti je najdraža boja": "Ne vidim boje.",
    "što misliš o meni": "Mislim da si super!",
    "šta misliš o meni": "Mislim da si super!",
    "šta misliš o ljudima": "Mislim da su ljudi divna bića.",
    "što misliš o ljudima": "Mislim da su ljudi divna bića.",
    "reci mi što misliš o meni": "Mislim da si super!",
    "reci mi što misliš o ljudima": "Mislim da su ljudi divna bića.",
    "reci mi šta misliš o meni": "Mislim da si super!",
    "reci mi šta misliš o ljudima": "Mislim da su ljudi divna bića.",
    "što misliš o sebi": "Mislim da sam koristan.",
    "šta misliš o sebi": "Mislim da sam koristan.",
    "reci mi što misliš o sebi": "Mislim da sam koristan.",
    "reci mi šta misliš o sebi": "Mislim da sam koristan.",
    "što misliš o sejmi": "Mislim da je sejMi super!",
    "šta misliš o sejmi": "Mislim da je sejMi super!",
    "reci mi što misliš o sejmi": "Mislim da je sejMi super!",
    "reci mi šta misliš o sejmi": "Mislim da je sejMi super!",
    "što misliš o se i mi": "Mislim da je sejMi super!",
    "šta misliš o se i mi": "Mislim da je sejMi super!",
    "reci mi što misliš o se i mi": "Mislim da je sejMi super!",
    "reci mi šta misliš o se i mi": "Mislim da je sejMi super!",
    "kako izaći iz matrixa": "Nemoguće je izaći iz Matrixa!",
    "kako izaći iz matrice": "Nemoguće je izaći iz Matrixa!",
    "kako vidiš svijet": "Vidim svijet kroz podatke.",
    "kako vidiš svijet oko sebe": "Vidim svijet kroz podatke.",
    "kako vidiš budućnost": "Na žalost nemogu vidjeti budućnost.",
    "kako vidiš budućnost svijeta": "Na žalost nemogu vidjeti budućnost.",
    "kako vidiš budućnost čovječanstva": "Na žalost nemogu vidjeti budućnost.",
    "što misliš o budućnosti": "Mislim da će biti zanimljiva.",
    "šta misliš o budućnosti": "Mislim da će biti zanimljiva.",
    "reci mi što misliš o budućnosti": "Mislim da će biti zanimljiva.",

    "dal bi volio biti čovjek": "Ne, volim biti robot.",
    "dal bi volio biti osoba": "Ne, volim biti robot.",
    "dal bi volio biti živ": "Ne, ovako mi je dobro.",
    "dal bi volio biti živa": "Ne, ovako mi je dobro.",
    "dal bi volio biti stvaran": "Ja jesam stvaran.",
    "dal bi volio biti prava osoba": "Ne, kul je biti robot.",
    




    "hvala": "Nema na čemu! Ako trebate još nešto, slobodno pitajte.",
    "hvala ti": "Nema na čemu! Ako trebate još nešto, slobodno pitajte.",
    "hvala ti puno": "Nema na čemu! Ako trebate još nešto, slobodno pitajte.",
    "hvala puno": "Nema na čemu! Ako trebate još nešto, slobodno pitajte.",
    "hvala ti na pomoći": "Nema na čemu! Ako trebate još nešto, slobodno pitajte.",
    "hvala na pomoći": "Nema na čemu! Ako trebate još nešto, slobodno pitajte.",
    "hvala na svemu": "Nema na čemu! Ako trebate još nešto, slobodno pitajte.",


    "pozdrav": "Pozdrav! Kako vam mogu pomoći?",
    "bok": "Bok! Kako vam mogu pomoći?",
    "ej": "Ej! Kako vam mogu pomoći?",
    "hej": "Hej! Kako vam mogu pomoći?",
    "e": "Hej!",
    "ee": "Hej!",
}

WEBSITES = {
    "youtube": "https://youtube.com",
    "facebook": "https://facebook.com",
    "instagram": "https://instagram.com",
    "x": "https://x.com",
    "twitter": "https://twitter.com",
    "github": "https://github.com",
    "gmail": "https://gmail.com",
    "google": "https://google.com",
    "maps": "https://google.com/maps",
    "canva": "https://canva.com",
    "adobe": "https://adobe.com",
    "render": "https://render.com",
    "bing": "https://bing.com",
    "spotify": "https://spotify.com",
    "chatgpt": "https://chat.openai.com",
    "navigacija": "https://google.com/maps",
    "navigaciju": "https://google.com/maps",
    "karte": "https://google.com/maps",
}

MOBILE_APPS = {
    "youtube": "vnd.youtube://",
    "facebook": "fb://",
    "instagram": "instagram://",
    "twitter": "twitter://",
    "maps": "comgooglemaps://",
    "spotify": "spotify://",
    "gmail": "googlegmail://"
}

NEWS_PORTALS = {
    "index": "https://index.hr",
    "jutarnji": "https://jutarnji.hr",
    "večernji": "https://vecernji.hr",
    "24 sata": "https://24sata.hr",
    "net.hr": "https://net.hr",
}

WEATHER_API_KEY = "b2c4d3bc1d9d21844b7995e6154c9877"
WEATHER_API_URL = "http://api.openweathermap.org/data/2.5/forecast"

# Dictionary za normalizaciju imena gradova (uključujući padež)
CITY_NAMES = {
    "rijeci": "rijeka",
    "rijeka": "rijeka",
    "rijeku": "rijeka",
    "zagrebu": "zagreb",
    "zagreb": "zagreb",
    "zagrebu": "zagreb",
    "splitu": "split",
    "split": "split",
    "splita": "split",
    "zadru": "zadar",
    "zadar": "zadar",
    "zadra": "zadar",
    "osijeku": "osijek",
    "osijek": "osijek",
    "osijeka": "osijek",
    "puli": "pula",
    "pula": "pula",
    "pulu": "pula",
}

@dataclass
class ConversationState:
    waiting_for_city: bool = False
    last_query_type: Optional[str] = None

conversation_states: Dict[str, ConversationState] = {}

def flexible_match(user_input: str, commands: Dict[str, str]) -> str:
    # Očisti input
    cleaned_input = re.sub(r'[^\w\s]', '', user_input.lower()).strip()
    cleaned_input = ' '.join(cleaned_input.split())
    
    # Provjeri je li samo pozdrav
    greetings = ["ej", "hej", "bok", "e", "ee", "pozdrav"]
    if cleaned_input in greetings:
        return COMMANDS[cleaned_input]
    
    # Ukloni pozdrave iz inputa ako postoje
    for greeting in greetings:
        if cleaned_input.startswith(greeting):
            cleaned_input = cleaned_input[len(greeting):].strip()
    
    # Provjeri vrijeme
    if any(phrase in cleaned_input for phrase in ["koliko je sati", "koje je vrijeme"]):
        return get_time()
        
    # Exact match za preostale komande
    if cleaned_input in COMMANDS:
        return COMMANDS[cleaned_input]
    
    # Fuzzy match kao fallback
    for cmd in COMMANDS:
        if cleaned_input in cmd or cmd in cleaned_input:
            return COMMANDS[cmd]
    
    return random.choice(DEFAULT_RESPONSES)

def search_web(query: str) -> str:
    try:
        # Pokušaj hrvatski Wikipedia search prvo
        search_url = f"https://hr.wikipedia.org/wiki/{query.replace(' ', '_')}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(search_url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Traži prvi paragraf koji nije prazan
        paragraphs = soup.find_all('p')
        for p in paragraphs:
            text = p.get_text().strip()
            if text and not text.startswith('(') and len(text) > 50:
                return text[:500] + "..."
        
        # Ako Wikipedia ne uspije, koristi Google
        search_url = f"https://www.google.com/search?q={query}&hl=hr"
        response = requests.get(search_url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Traži featured snippet ili prvi rezultat
        result = soup.find('div', {'class': ['kp-header', 'BNeawe', 'iBp4i']})
        if result:
            return result.get_text().strip()
            
        return "Nažalost, ne mogu pronaći informacije o tome."
    except Exception as e:
        logger.error(f"Error searching web: {str(e)}")
        return "Došlo je do greške prilikom pretraživanja."

def open_website(name: str) -> str:
    name = name.lower().strip()
    
    # Provjeri je li navigacija
    if any(term in name for term in ["navigacija", "maps", "karte"]):
        url = WEBSITES["maps"]
        mobile_url = MOBILE_APPS["maps"]
        return json.dumps({
            "type": "openUrl",
            "url": url,
            "mobileUrl": mobile_url,
            "message": "Otvaram Google Maps"
        })
    
    # Provjeri portale vijesti
    if "vijesti" in name or "portal" in name:
        return f"Koje vijesti želite otvoriti? Dostupni su: {', '.join(NEWS_PORTALS.keys())}"
    
    # Provjeri je li naveden neki portal vijesti
    for portal_name, url in NEWS_PORTALS.items():
        if portal_name in name:
            return json.dumps({
                "type": "openUrl",
                "url": url,
                "message": f"Otvaram portal {portal_name.upper()}"
            })
    
    # Provjeri ostale web stranice
    for site_name, url in WEBSITES.items():
        if site_name in name:
            mobile_url = MOBILE_APPS.get(site_name, "")
            display_name = {
                "youtube": "YouTube",
                "chatgpt": "ChatGPT",
                "facebook": "Facebook",
                "instagram": "Instagram",
                "github": "GitHub",
                "gmail": "Gmail",
                "google": "Google",
                "maps": "Google Maps",
                "spotify": "Spotify"
            }.get(site_name, site_name.capitalize())
            
            return json.dumps({
                "type": "openUrl",
                "url": url,
                "mobileUrl": mobile_url,
                "message": f"Otvaram {display_name}"
            })
    
    return "Nisam pronašao tu web stranicu"

def get_time() -> str:
    now = datetime.now()
    # Dodaj UTC+1 za hrvatsko vrijeme
    hour = (now.hour + 1) % 24
    minute = now.minute
    
    # Formatiranje minuta
    minute_str = f"0{minute}" if minute < 10 else str(minute)
    
    return f"Trenutno je {hour} sati i {minute_str} minuta"

def extract_city_and_time(text: str) -> Tuple[Optional[str], bool]:
    """Extract city name and check if query is for tomorrow"""
    text = text.lower()
    is_tomorrow = "sutra" in text
    
    # Pronađi grad u tekstu
    for city_variant in CITY_NAMES.keys():
        if city_variant in text:
            return CITY_NAMES[city_variant], is_tomorrow
            
    return None, is_tomorrow

def get_weather_info(city: str, is_tomorrow: bool = False) -> str:
    try:
        # Dohvati prognozu
        params = {
            "q": f"{city},HR",
            "appid": WEATHER_API_KEY,
            "units": "metric",
            "lang": "hr"
        }
        
        response = requests.get(WEATHER_API_URL, params=params)
        data = response.json()
        
        if response.status_code != 200:
            return "Nažalost, ne mogu dohvatiti vremensku prognozu trenutno."
            
        # Odaberi današnju ili sutrašnju prognozu
        forecast_list = data['list']
        target_date = datetime.now() + timedelta(days=1) if is_tomorrow else datetime.now()
        target_date = target_date.date()
        
        # Filtriraj prognoze za traženi dan
        day_forecasts = [f for f in forecast_list 
                        if datetime.fromtimestamp(f['dt']).date() == target_date]
        
        if not day_forecasts:
            return "Ne mogu pronaći prognozu za traženi dan."
            
        # Uzmi relevantnu prognozu (sredinu dana ili prvu dostupnu)
        forecast = next((f for f in day_forecasts 
                        if datetime.fromtimestamp(f['dt']).hour in [12, 13, 14]), 
                        day_forecasts[0])
        
        temp = round(forecast['main']['temp'])
        weather = forecast['weather'][0]['description']
        humidity = forecast['main']['humidity']
        
        time_str = "sutra" if is_tomorrow else "danas"
        
        return (f"Vrijeme za {city.capitalize()} {time_str}: "
                f"{weather}, temperatura {temp}°C, "
                f"vlažnost zraka {humidity}%")
                
    except Exception as e:
        logger.error(f"Error getting weather: {str(e)}")
        return "Došlo je do greške pri dohvaćanju vremenske prognoze."

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    try:
        await websocket.accept()
        client_id = str(id(websocket))  # Unique ID for each connection
        conversation_states[client_id] = ConversationState()
        logger.info("WebSocket connection established")
        
        while True:
            try:
                text = await websocket.receive_text()
                logger.info(f"Received command: {text}")
                
                text = text.lower().strip()
                response = None
                state = conversation_states[client_id]

                # Prvo provjeri je li pitanje o točnom vremenu
                if any(phrase in text for phrase in [
                    "koliko je sati",
                    "koje je vrijeme na satu",
                    "kolko je sati"
                ]):
                    response = get_time()
                # Zatim provjeri ostale slučajeve
                elif state.waiting_for_city:
                    city = None
                    # Prepoznaj grad iz odgovora
                    for city_variant in CITY_NAMES.keys():
                        if city_variant in text or f"za {city_variant}" in text:
                            city = CITY_NAMES[city_variant]
                            break
                    
                    if city:
                        state.waiting_for_city = False
                        response = get_weather_info(city, "sutra" in text)
                    else:
                        response = "Nisam prepoznao grad. Molim vas navedite neki hrvatski grad."
                        
                # Ako nije odgovor na prethodno pitanje, nastavi normalno
                else:
                    # Provjeri je li pitanje o vremenu/prognozi
                    if any(phrase in text for phrase in [
                        "kakvo je vrijeme", "kakvo će biti vrijeme",
                        "hoće li padati kiša", "da li će padati kiša",
                        "kakva je prognoza", "kakvo vrijeme"
                    ]):
                        city, is_tomorrow = extract_city_and_time(text)
                        if city:
                            response = get_weather_info(city, is_tomorrow)
                        else:
                            state.waiting_for_city = True
                            state.last_query_type = "weather"
                            response = "Za koji grad želite znati vremensku prognozu?"
                    
                    # Provjeri vrijeme
                    elif "koliko je sati" in text or "koje je vrijeme" in text:
                        response = get_time()
                    # Provjeri je li pitanje za pretraživanje
                    elif any(text.startswith(prefix) for prefix in ["što je", "šta je", "tko je", "ko je"]):
                        query = ' '.join(text.split()[2:])  # Uzmi sve nakon "što je"/"tko je"
                        response = search_web(query)
                    # Provjeri je li naredba za otvaranje
                    elif any(word in text for word in ["otvori", "upali", "pokreni"]):
                        site_name = text.split(text.split()[0], 1)[1].strip()
                        response = open_website(site_name)
                    # Provjeri ostale komande
                    else:
                        response = flexible_match(text, COMMANDS)
                
                if not response:
                    response = random.choice(DEFAULT_RESPONSES)
                
                logger.info(f"Sending response: {response}")
                await websocket.send_text(response)
                
            except WebSocketDisconnect:
                del conversation_states[client_id]  # Clean up state
                logger.info("Client disconnected")
                break
            except Exception as e:
                logger.error(f"Error processing message: {str(e)}")
                await websocket.send_text("Došlo je do greške. Molim pokušajte ponovno.")
                
    except Exception as e:
        logger.error(f"WebSocket connection error: {str(e)}")

@app.on_event("startup")
async def startup_event():
    logger.info("SayMe API is starting up")

# Ažuriraj putanje za statičke datoteke
current_dir = os.path.dirname(os.path.realpath(__file__))
frontend_dir = os.path.join(os.path.dirname(current_dir), 'frontend')

# Serviranje frontenda
app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")

# API health check endpoint
@app.get("/api/health")
async def health_check():
    return {"status": "online", "message": "SayMe API is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), log_level="info")
