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
import locale

# Set locale for Croatian day and month names
try:
    locale.setlocale(locale.LC_TIME, 'hr_HR.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_TIME, 'Croatian.UTF-8')
    except:
        pass  # Fall back to default if Croatian locale isn't available

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
    "Hhm, nisam siguran što to znači. Pokušajte drugačije.",
    "Nije mi jasno. Možete li pitati na drugi način?",
    "To mi nije poznato. Možete li pojasniti?",
    "Žao mi je, ali ne razumijem. Pokušajte postaviti pitanje drugačije.",
    "Nažalost ne razumijem. Možete li biti specifičniji?"
]

COMMANDS: Dict[str, str] = {
    "kako se zoveš": "Ime mi je Noa!",
    "kako ti je ime": "Moje ime je Noa!",
    "kako se ti zoveš": "Zovem se Noa!",
    "ko si": "Glasovni asistent, Noa.",
    "ko si ti": "Glasovni asistent, Noa.",
    "tko si ti": "Ja sam glasovni asistent, možete me zvati Noa!",
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
    "ko te napravio": "Napravio me je tim sejMi iz Hrvatske.",
    "tko te je stvorio": "Stvorio me je tim sejMi iz Hrvatske.",

    "kako ti funkcioniraš": "Ja sam glasovni asistent koji koristi umjetnu inteligenciju za komunikaciju s tobom.",
    "kako ti radiš": "Uglavnom prikupljam podatke na temelju tvojih upita, analiziram ih i dajem odgovor.",
    "kako radiš": "Radim na principu umjetne inteligencije i obrade prirodnog jezika.",
    "zašto baš Noa": "Tvorci su mi dali ime, morat ćeš pitati njih!",

    "kako te mogu koristiti": "Možeš me koristiti na razne načine, mogu otvarati web stranice i aplikacije na tvom uređaju, mogu ti reći vremensku prognozu, koji je dan i sat, ili jednostavno odgovarati na tvoja pitanja",
    "kako te koristiti": "Možeš me koristiti na razne načine, mogu otvarati web stranice i aplikacije na tvom uređaju, mogu ti reći vremensku prognozu, koji je dan i sat, ili jednostavno odgovarati na tvoja pitanja",
    "kako da te koristim": "Mogu ti pomoći u dohvaćanju informacija s interneta, možeš me pitati za vremensku prognozu, mogu ti reći koji je dan i sat, ili jednostavno odgovarati na tvoja pitanja",
    "što te mogu pitati": "Možete me pitati bilo što, ja ću se potruditi pronaći relevantan odgovor.",
    "što te mogu pitat": "Što god te zanimalo, slobodno pitaj.",
    "što ti možeš": "Mogu za tebe otvarati vjesti i portale, web stranice i aplikacije, reći ti vremensku prognozu ili odgovarati na tvoja pitanja.",
    "što možeš": "Mogu puno toga, pitaj što te zanima.",
    "što ti znaš": "Znam puno toga, samo pitaj.",
    "što znaš": "Znam puno toga, samo pitaj.",
    "šta ti znaš": "Znam puno toga, samo pitaj.",
    "šta znaš": "Znam puno toga, samo pitaj.",
    "šta možeš": "Mogu ti pomoći s mnogim stvarima, na primjer brzo doći do relevantnih informacija.",
    "šta ti možeš": "Mogu ti pomoći s mnogim stvarima, mogu ti reći kakvo je vrijeme ili ovoriti aplikaciju za tebe.",
    "možeš li na net": "Mogu surfat internetom ali samo za prikupljanje podataka da ti dam adekvatan odgovor.",
    "možeš li na internet": "Mogu surfat internetom ali samo za prikupljanje podataka da ti dam adekvatan odgovor.",
    "za šta služiš": "Služim za pomoć ljudima.",
    "za što služiš": "Služim za pomoć ljudima.",
    "za što si tu": "Tu sam da vam pomognem.",
    "za šta si tu": "Tu sam da vam pomognem.",
    "koja je tvoja svrha": "Pomoći ljudima.",
    "koja je tvoja funkcija": "Pomoći ljudima.",
    "koja je tvoja uloga": "Pomoći ljudima.",

    "jesi li robot": "Ne, ja sam glasovni asistent.",
    "jesi li čovjek": "Ne, ja nisam čovjek.",
    "jesi li živ": "Ne, ja nisam živ.",
    "jesi li mrtav": "Ne, ja nemogu biti živ ni mrtav.",
    "jesi li živa": "Ne, ja nisam živa.",
    "jesi li stvaran": "Da, ja sam stvaran.",	
    "jesi li prava osoba": "Ne, ja sam program.",
    "jesi li ti umjetna inteligencija": "Da, ja sam umjetna inteligencija.",
    "jesi li ti AI": "Da, ja sam AI.",

    "jesi li dobar ili zao": "Ja sam program koji na temelju tvojih upita ispunjava zadatke, ne mogu biti ni dobar ni zao.",
    "jesi li dobar": "Ja sam program koji na temelju tvojih upita dolazi do relevantnih informacija ili ispunjavanja laksih zadataka. S toga nemam svoju osobnost.",
    "jesi li zao": "Nisam ni zao ni dobar, ja sam softverski program i nemam vlastitu osobnost i osjećaje.",
    "jesi li zločest": "Ja sam softverski program i nemmam vlastitu osobnost i osjećaje.",
    "jesi li zločest ili dobar": "Ni jedno ni drugo, kao softverski program nemam osobnost.",

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

    "ponavljaj zamnom": "Hhm ne, hvala.",
    "ponavljaj za mnom": "Hhm ne, hvala.",

    "zabavi me": "Idu dva pileta ulicom i piu piu piu.",
    "ispričaj mi vic": "Na žalost, ne znam pričati viceve.",
    "ispričaj mi neki vic": "Na žalost, ne znam pričati viceve.",
    "daj neki vic": "Na žalost, ne znam pričati viceve.",
    "daj mi vic": "Na žalost, ne znam pričati viceve.",

    "kako se glasa mačka": "Mačka se glasa mjau.",
    "kako se glasa pas": "Pas se glasa vau.",
    "kako se glasa konj": "Konj se glasa ihaa.",
    "kako se glasa krava": "Krava se glasa muuu.",
    "kako se glasa ovca": "Ovca se glasa beee.",
    "kako se glasa svinja": "Svinja se glasa oink.",
    "kako se glasa pijetao": "Pijetao se glasa kukuriku.",


    "mjau": "Woof!",
    "mijau": "Woof!",
    "ti si budala": "Hvala na komplimentu.",
    "ti si glup": "Hvala na komplimentu.",
    "ma ti si glup": "Hvala na komplimentu.",
    "ma ti si budala": "Hvala na komplimentu.",
    "ma ti si kreten": "Hvala na komplimentu.",

    "gdje se nalaziš": "Ja sam ovdje, na internetu.",
    "gdje si": "Tu sam ja!.",
    "dosadno mi je": "Hm evo par zanimljivih stvari koje možeš raditi: Možeš pročitati knjigu, gledati film, igrati igricu, šetati, vježbati, kuhati, učiti nešto novo, razgovarati s prijateljima... Što misliš?",
    "što da radim": "Hm evo par zanimljivih stvari koje možeš raditi: Možeš pročitati knjigu, gledati film, igrati igricu, šetati, vježbati, kuhati, učiti nešto novo, razgovarati s prijateljima... Što misliš?",

    "šta voliš jest:": "Hhm... Ne jedem, ali volim podatke.",
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

    "dal bi volio biti čovjek": "Ne, volim biti program.",
    "dal bi volio biti osoba": "Ne, volim biti program.",
    "dal bi volio biti živ": "Ne, ovako mi je dobro.",
    "dal bi voljela biti živa": "Ne, ovako mi je dobro.",
    "dal bi volio biti stvaran": "Ja jesam stvaran. ja sam softverski program.",
    "dal bi volio biti prava osoba": "Ne, kul je biti program.",
    "dali bi volio biti čovjek": "Ne, volim biti program.",
    "dali bi volio biti osoba": "Ne, volim biti program.",
    "dali bi volio biti živ": "Ne, ovako mi je dobro.",
    "dali bi voljela biti živa": "Ne, ovako mi je dobro.",
    "dali bi volio biti stvaran": "Ja jesam stvaran.",
    "dali bi volio biti prava osoba": "Ne, kul je biti program.",
    "dali bi voljela biti prava osoba": "Ne, kul je biti program.",
    "bi volio bit živ": "Ne, ovako mi je dobro.",
    "bi voljela bit živa": "Ne, ovako mi je dobro.",

    "lažeš": "Ne lažem, ja sam program. nemam mogućnost lagati",
    "dal lažeš": "Ne lažem, ja sam program. nemam mogućnost lagati",
    "znaš li lagati": "Ne, ja sam program. nemam mogućnost lagati",
    "znaš li lagat": "Ne, ja sam program. nemam mogućnost lagati",

    "ništa ne razumiješ": "Ispričavam se ali možeš pokušati pričati razgovjetnije, možda ću bolje razmumjeti tvoje pitanje",
    "znaš ti kurac": "Molim te da ne pričaš tako, ja sam program i ne razumijem takav govor.",
    "znaš ti moj kurac": "Molim te da ne pričaš tako, ja sam program i ne razumijem takav govor.",
    "reci đakovo": "Đakovo",
    "u usta ti ga spakovo": " Ha-ha, vrlo smiješno.",
    "reci betmen": "Betmen",
    "u usta ti ga metnem": "Ha-ha, dobra fora.",
    
    "čuješ ti mene": "Da, čujem te.",
    "čuješ ti ovo": "Da, čujem.",
    "čuješ ti": "Da, čujem te.",
    "čuješ li me": "Da, čujem te.",
    
    "kako da te zovem": "Možeš me zvati Noa.",
    "kako da zaradim novac": "Možeš pokušati raditi, ulagati ili pokrenuti vlastiti posao.",
    "kako da zaradim": "Možeš pokušati raditi, ulagati ili pokrenuti vlastiti posao.",
    "kako da zaradim novac online": "Možeš pokušati raditi, ulagati ili pokrenuti vlastiti posao.",


    "dosta mi je svega": "Možda bi trebao uzeti pauzu i odmoriti se.",
    "dosta mi je": "Možda bi trebao uzeti pauzu i odmoriti se.",
    "svega mi je dosta": "Možda bi trebao uzeti pauzu i odmoriti se.",
    "svega mi je preko glave": "Možda bi trebao uzeti pauzu i odmoriti se.",
    "pun mi je kurac svega": "Možda bi trebao uzeti pauzu i odmoriti se.",
    "pun mi je kurac": "Možda bi trebao uzeti pauzu i odmoriti se.",

    "umoran sam": "Možda bi trebao uzeti pauzu i odmoriti se.",
    "umorna sam": "Možda bi trebala uzeti pauzu i odmoriti se.",
    "umoran sam od svega": "Možda bi trebao uzeti pauzu i odmoriti se.",
    "umorna sam od svega": "Možda bi trebala uzeti pauzu i odmoriti se.",

    "gladan sam": "Možda bi trebao nešto pojesti.",
    "gladna sam": "Možda bi trebala nešto pojesti.",
    "žedan sam": "Možda bi trebao nešto popiti.",
    "žedna sam": "Možda bi trebala nešto popiti.",

    "kako najbrže doći do": "Najkraćim putem!",
    "kako napraviti": "Prouči upute i slijedi korake.",
    "kako da": "Prouči upute i slijedi korake.",
    "kako da dođem do": "Najkraćim putem!",

    
    "kako to ne znaš": "Nažalost, nemam još sve informacije ali još učim.",
    "kako to neznaš": "Još sam u fazi razvoja i učenja.",
    "kako ne znaš": "Još sam u fazi razvoja i učenja.",
    "kako neznaš": "Nažalost, nemam još sve informacije ali još učim.",




    "hvala": "Nema na čemu! Ako trebate još nešto, slobodno pitajte.",
    "hvala ti": "Nema na čemu! Ako trebate još nešto, slobodno pitajte.",
    "hvala ti puno": "Nema na čemu! Ako trebate još nešto, slobodno pitajte.",
    "hvala puno": "Nema na čemu! Ako trebate još nešto, slobodno pitajte.",
    "hvala ti na pomoći": "Nema na čemu! Ako trebate još nešto, slobodno pitajte.",
    "hvala na pomoći": "Nema na čemu! Ako trebate još nešto, slobodno pitajte.",
    "hvala na svemu": "Nema na čemu! Ako trebate još nešto, slobodno pitajte.",

    
   
    "pozdrav": "Pozdrav! Kako vam mogu pomoći?",
    "bok": "Bok!",
    "ej": "Ej! Kako vam mogu pomoći?",
    "hej": "Hej! Kako vam mogu pomoći?",
    "dobar dan": "Dobar dan! Kako vam mogu pomoći?",
    "dobro jutro": "Dobro jutro! Kako vam mogu pomoći?",
    "dobro veče": "Dobro veče! Kako vam mogu pomoći?",
    "dobra večer": "Dobra večer! Kako vam mogu pomoći?",
    "doviđenja": "Doviđenja! Ako trebate pomoć, tu sam.",
    "laku noć": "Laku noć! Ako trebate pomoć, tu sam.",
    "ćao": "Ćao! Kako vam mogu pomoći?",
    "ajde bok": "Bok! Ako trebate pomoć, tu sam.",
    "ajde čujemo se": "Čujemo se!",
    "ajde doviđenja": "Doviđenja! Ako trebate pomoć, tu sam.",

    
    "ne": "U redu, kako ti još mogu pomoći?",
    "ne želim": "U redu, kako ti još mogu pomoći?",
    "neću": "U redu, kako ti još mogu pomoći?",
    "ne mogu": "U redu, kako ti još mogu pomoći?",
    "nemogu": "U redu, kako ti još mogu pomoći?",

    "što misliš": "Mislim da je to dobro pitanje.",
    "šta misliš": "Mislim da je to dobro pitanje.",
    "šta ti misliš": "Mislim da je to dobro pitanje.",
    "što ti misliš": "Mislim da je to dobro pitanje.",
    "šta ti misliš o tome": "Mislim da je to dobro pitanje.",
    "što ti misliš o tome": "Mislim da je to dobro pitanje.",

    "super si": "Hvala! Kako ti mogu pomoći?",
    "odličan si": "Hvala! Kako ti mogu pomoći?",
    "super": "Hvala! Kako ti mogu pomoći?",
    "odlično": "Hvala! Kako ti mogu pomoći?",
    "top si": "Hvala! Kako ti mogu pomoći?",

    "nije dobro": "Žao mi je, trudim se biti bolji.",
    "to nije istina": "Žao mi je, moguće da sam ti dao krivu informaciju.",
    "to nije točno": "Žao mi je, moguće da sam ti dao krivu informaciju.",
    "kako možeš davati krive informacije": "Žao mi je, trudim se biti točan ali ponekad griješim.",
    "kako možeš dati krive informacije": "Žao mi je, trudim se biti točan ali ponekad griješim.",
    "kako možeš dati krive podatke": "Žao mi je, trudim se biti točan ali ponekad griješim.",
    "ne radiš dobro": "Žao mi je, trudim se biti bolji.",
    "ne radiš kako treba": "Žao mi je, trudim se biti bolji.",
    "ne valjaš": "Žao mi je, trudim se biti bolji.",
    "ne valja": "Žao mi je, trudim se biti bolji.",

    "ne vjerujem ti": "Žao mi je zbog toga.",
    "ne vjerujem": "Žao mi je zbog toga.",

    "broj za hitnu pomoć": "Broj za hitnu pomoć je 112.",
    "broj za htinu": "Broj za hitnu pomoć je 112.",
    "broj za policiju": "Broj za policiju je 192.",
    "broj za vatrogasce": "Broj za vatrogasce je 193.",
    "broj za hitne službe": "Broj za hitne službe je 112.",
    "pomoć na cesti": "Broj za pomoć na cesti je 1987.",
    "auto mi je u kvaru": "Nazovite 1987 za pomoć na cesti.",
    "auto mi je pokvaren": "Nazovite 1987 za pomoć na cesti.",
    "treba mi hitna pomoć": "Nazovite 112.",
    "treba mi policija": "Nazovite 192.",
    "trebaju mi vatrogasci": "Nazovite 193.",
    "izgubljen sam": "Nazovite 112 za policiju. Ili nazovite 195 za službu traženja i spašavanja.",
    "izgubljena sam": "Nazovite 112 za policiju. Ili nazovite 195 za službu traženja i spašavanja.",
    "izgubljeni smo": "Nazovite 112 za policiju. Ili nazovite 195 za službu traženja i spašavanja.",
    "izgubljene smo": "Nazovite 112 za policiju. Ili nazovite 195 za službu traženja i spašavanja.",
    "izgubio sam se": "Nazovite 112 za policiju. Ili nazovite 195 za službu traženja i spašavanja.",
    "ne znam di sam": "Najbolje bi bilo da nazovete 112 za policiju. Ili nazovite 195 za službu traženja i spašavanja.",
    "ne znam gdje sam": "Najbolje bi bilo da nazovete 112 za policiju. Ili nazovite 195 za službu traženja i spašavanja.",
    "ne znam gdje se nalazim": "Najbolje bi bilo da nazovete 112 za policiju. Ili nazovite 195 za službu traženja i spašavanja.",

}

CROATIAN_DAYS = {
    'Monday': 'Ponedjeljak',
    'Tuesday': 'Utorak',
    'Wednesday': 'Srijeda',
    'Thursday': 'Četvrtak',
    'Friday': 'Petak',
    'Saturday': 'Subota',
    'Sunday': 'Nedjelja'
}

CROATIAN_MONTHS = {
    'January': 'Siječnja',
    'February': 'Veljače',
    'March': 'Ožujka',
    'April': 'Travnja',
    'May': 'Svibnja',
    'June': 'Lipnja',
    'July': 'Srpnja',
    'August': 'Kolovoza',
    'September': 'Rujna',
    'October': 'Listopada',
    'November': 'Studenog',
    'December': 'Prosinca'
}

COMMANDS.update({
    "koji je danas dan": lambda: get_date_info(),
    "koji je dan danas": lambda: get_date_info(),
    "koji je datum": lambda: get_date_info(),
    "koji je datum danas": lambda: get_date_info(),
    "koji je datum sutra": lambda: get_date_info(1),
    "koji je dan sutra": lambda: get_date_info(1),
    "koji će dan biti sutra": lambda: get_date_info(1),
    "koji dan je sutra": lambda: get_date_info(1),
})

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
    "dubrovniku": "dubrovnik",
    "dražice": "dražice",
    "dražicama": "dražice",
    "makarska": "makarska",
    "solin": "solin",
    "makarskoj": "makarska",
    "solinu": "solin",
    "korčuli": "korčula",
    "hvaru": "hvar",
    "hvar": "hvar",
    "korčula": "korčula",
    "dubrovnik": "dubrovnik",
    "vukovaru": "vukovar",
    "vukovar": "vukovar",
    "varaždinu": "varaždin",
    "varaždin": "varaždin",
    "šibeniku": "šibenik",
    "šibenik": "šibenik",
    "senju": "senj",
    "senj": "senj",
    "krivi put": "krivi put",
    "krivom putu": "krivi put",
    "krk": "krk",
    "krku": "krk",
    "cresu": "cres",
    "cres": "cres",
    "lošinju": "lošinj",
    "lošinj": "lošinj",
    "rovinju": "rovinj",
    "rovinj": "rovinj",
    "buzetu": "buzet",
    "buzet": "buzet",
    "poreču": "poreč",
    "poreč": "poreč",
    "pazinu": "pazin",
    "pazin": "pazin",
    "karlovcu": "karlovac",
    "karlovac": "karlovac",
    "sisku": "sisak",
    "sisak": "sisak",
    "delnicama": "delnice",
    "delnice": "delnice",
    "bjelovaru": "bjelovar",
    "bjelovar": "bjelovar",
    "slavonskom brodu": "slavonski brod",
    "slavonski brod": "slavonski brod",
    "opatiji": "opatija",
    "opatija": "opatija",
    "viškovu": "viškovo",
    "viškovo": "viškovo",
    "jelenju": "jelenje",
    "jelenje": "jelenje",
    "kastvu": "kastav",
    "kastav": "kastav",
    "alanu": "alan",
    "alan": "alan",
    "crikvenici": "crikvenica",
    "crikvenica": "crikvenica",
    "novom vinodolskom": "novi vinodolski",
    "novi vinodolski": "novi vinodolski",

}

@dataclass
class WeatherContext:
    asking_for_city: bool = False
    original_query: str = ""
    day_offset: int = 0
    specified_day: str = ""

# Dodajte u postojeći ConversationState
@dataclass
class ConversationState:
    waiting_for_city: bool = False
    last_query_type: Optional[str] = None
    weather_context: Optional[WeatherContext] = None

conversation_states: Dict[str, ConversationState] = {}

def flexible_match(user_input: str, commands: Dict[str, str]) -> str:
    cleaned_input = re.sub(r'[^\w\s]', '', user_input.lower()).strip()
    cleaned_input = ' '.join(cleaned_input.split())
    
    greetings = ["ej", "hej", "bok", "e", "ee", "pozdrav"]
    if cleaned_input in greetings:
        return COMMANDS[cleaned_input]
    
    for greeting in greetings:
        if cleaned_input.startswith(greeting):
            cleaned_input = cleaned_input[len(greeting):].strip()
    
    if any(phrase in cleaned_input for phrase in ["koliko je sati", "koje je vrijeme"]):
        return get_time()
        
    if cleaned_input in COMMANDS:
        return COMMANDS[cleaned_input]
    
    for cmd in COMMANDS:
        if cleaned_input in cmd or cmd in cleaned_input:
            return COMMANDS[cmd]
    
    return random.choice(DEFAULT_RESPONSES)

def search_web(query: str) -> str:
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        # Clean and prepare query
        clean_query = query.lower().strip()
        query_type = None
        subject = ""
        
        # Extract subject from query
        if clean_query.startswith(('tko je', 'ko je')):
            query_type = 'person'
            subject = re.sub(r'^(tko|ko)\s+je\s+', '', clean_query).strip()
        elif clean_query.startswith(('što je', 'šta je')):
            query_type = 'definition'
            subject = re.sub(r'^(što|šta)\s+je\s+', '', clean_query).strip()
            
        subject = subject.rstrip('?')
        if not subject:
            return "Molim vas dopunite pitanje."

        # Try Croatian Wikipedia first
        wiki_url = f"https://hr.wikipedia.org/wiki/{subject.replace(' ', '_').title()}"
        response = requests.get(wiki_url, headers=headers)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            content = soup.find('div', class_='mw-parser-output')
            
            if content:
                # Skip tables and infoboxes
                paragraphs = content.find_all('p', recursive=False)
                for p in paragraphs:
                    text = p.text.strip()
                    # Check if paragraph is meaningful
                    if len(text) > 50 and not p.find('span', class_='coordinates'):
                        # Clean up the text
                        text = re.sub(r'\[\d+\]', '', text)  # Remove references
                        text = re.sub(r'\([^)]*\)', '', text)  # Remove parentheses
                        text = re.sub(r'\s+', ' ', text)  # Normalize spaces
                        
                        # Format response based on query type
                        if not text.lower().startswith(subject.lower()):
                            prefix = f"{subject} je"
                            if query_type == 'person':
                                prefix = f"{subject.title()} je"
                            text = f"{prefix} {text}"
                            
                        return text[:500] + "..." if len(text) > 500 else text

        # If direct lookup fails, try search
        search_url = f"https://hr.wikipedia.org/w/index.php?search={subject}&title=Posebno%3ATraži&profile=advanced&fulltext=1&ns0=1"
        response = requests.get(search_url, headers=headers)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            result = soup.find('div', class_='mw-search-result-heading')
            
            if result and result.find('a'):
                article_url = "https://hr.wikipedia.org" + result.find('a')['href']
                response = requests.get(article_url, headers=headers)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    for p in soup.find_all('p'):
                        text = p.text.strip()
                        if len(text) > 50 and not p.find('span', class_='coordinates'):
                            text = re.sub(r'\[\d+\]', '', text)
                            text = re.sub(r'\([^)]*\)', '', text)
                            text = re.sub(r'\s+', ' ', text)
                            
                            if not text.lower().startswith(subject.lower()):
                                prefix = f"{subject} je"
                                if query_type == 'person':
                                    prefix = f"{subject.title()} je"
                                text = f"{prefix} {text}"
                            
                            return text[:500] + "..." if len(text) > 500 else text
            
        return f"Nažalost, ne mogu pronaći informacije o tome {'tko je' if query_type == 'person' else 'što je'} {subject}."

    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        return "Došlo je do greške prilikom pretraživanja. Molim pokušajte ponovno."

def open_website(name: str) -> str:
    name = name.lower().strip()
    
    if any(term in name for term in ["navigacija", "maps", "karte"]):
        url = WEBSITES["maps"]
        mobile_url = MOBILE_APPS["maps"]
        return json.dumps({
            "type": "openUrl",
            "url": url,
            "mobileUrl": mobile_url,
            "message": "Otvaram Google Maps"
        })
    
    if "vijesti" in name or "portal" in name:
        return f"Koje vijesti želite otvoriti? Dostupni su: {', '.join(NEWS_PORTALS.keys())}"
    
    for portal_name, url in NEWS_PORTALS.items():
        if portal_name in name:
            return json.dumps({
                "type": "openUrl",
                "url": url,
                "message": f"Otvaram portal {portal_name.upper()}"
            })
    
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
    hour = (now.hour + 1) % 24
    minute = now.minute
    
    minute_str = f"0{minute}" if minute < 10 else str(minute)
    
    return f"Trenutno je {hour} sati i {minute_str} minuta"

def extract_city_and_time(text: str) -> Tuple[Optional[str], bool]:
    text = text.lower()
    is_tomorrow = "sutra" in text
    
    for city_variant in CITY_NAMES.keys():
        if city_variant in text:
            return CITY_NAMES[city_variant], is_tomorrow
            
    return None, is_tomorrow

def get_weather_info(city: str, days_offset: int = 0) -> str:
    try:
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
            
        target_date = datetime.now() + timedelta(days=days_offset)
        target_date = target_date.date()
        
        forecast_list = data['list']
        day_forecasts = [f for f in forecast_list 
                        if datetime.fromtimestamp(f['dt']).date() == target_date]
        
        if not day_forecasts:
            return "Ne mogu pronaći prognozu za traženi dan."
            
        forecast = next((f for f in day_forecasts 
                        if datetime.fromtimestamp(f['dt']).hour in [12, 13, 14]), 
                        day_forecasts[0])
        
        temp = round(forecast['main']['temp'])
        weather = forecast['weather'][0]['description']
        humidity = forecast['main']['humidity']
        
        if days_offset == 0:
            day_str = "danas"
        elif days_offset == 1:
            day_str = "sutra"
        elif days_offset == 2:
            day_str = "prekosutra"
        else:
            day_str = target_date.strftime('%A').lower()
        
        return (f"Vrijeme za {city.capitalize()} {day_str}: "
                f"{weather}, temperatura {temp}°C, "
                f"vlažnost zraka {humidity}%")
                
    except Exception as e:
        logger.error(f"Error getting weather: {str(e)}")
        return "Došlo je do greške pri dohvaćanju vremenske prognoze."

def get_date_info(days_offset: int = 0) -> str:
    try:
        target_date = datetime.now() + timedelta(days=days_offset)
        
        weekday_eng = target_date.strftime('%A')
        month_eng = target_date.strftime('%B')
        
        weekday = CROATIAN_DAYS.get(weekday_eng, weekday_eng).capitalize()
        month = CROATIAN_MONTHS.get(month_eng, month_eng)
        
        date_str = f"{target_date.day}. {month} {target_date.year}."
        
        if days_offset == 0:
            return f"Danas je {weekday}, {date_str}"
        elif days_offset == 1:
            return f"Sutra je {weekday}, {date_str}"
        elif days_offset == 2:
            return f"Prekosutra je {weekday}, {date_str}"
        else:
            return f"U {weekday.lower()}, {date_str}"
            
    except Exception as e:
        logger.error(f"Date info error: {str(e)}")
        return "Došlo je do greške pri dohvaćanju datuma."

def get_day_offset(text: str) -> int:
    text = text.lower()
    
    if "prekosutra" in text:
        return 2
    elif "sutra" in text:
        return 1
    elif "danas" in text:
        return 0

    days_mapping = {
        'ponedjeljak': 0,
        'utorak': 1,
        'srijeda': 2,
        'srijedu': 2,
        'četvrtak': 3,
        'četvrtku': 3,
        'petak': 4,
        'petku': 4,
        'subota': 5,
        'subotu': 5,
        'nedjelja': 6,
        'nedjelju': 6
    }

    current_weekday = datetime.now().weekday()
    
    for day, day_num in days_mapping.items():
        if day in text:
            days_until = (day_num - current_weekday) % 7
            if days_until == 0 and not any(word in text for word in ["danas", "trenutno", "sad"]):
                days_until = 7
            return days_until

    return 0

def generate_maps_url(destination: str, mode: str = 'navigate') -> str:
    """Generate navigation URLs with preference for mobile apps"""
    # Očisti i formatiraj destinaciju
    destination = destination.strip().replace(' ', '+')
    
    # Mobile URLs za različite platforme
    mobile_urls = {
        'google': f"comgooglemaps://?daddr={destination}&directionsmode=driving",
        'waze': f"waze://?q={destination}&navigate=yes",
        'apple': f"maps://?daddr={destination}&dirflg=d",
        'here': f"here-location://{destination}",
        'osmand': f"osmand.geo:q={destination}"
    }
    
    # Web fallback URL
    web_url = f"https://www.google.com/maps/dir/?api=1&destination={destination}&travelmode=driving"
    
    return json.dumps({
        "type": "openUrl",
        "url": web_url,  # fallback za desktop
        "mobileUrls": mobile_urls,  # lista svih mobilnih URL-ova
        "message": f"Otvaram navigaciju do lokacije: {destination.replace('+', ' ')}"
    })

# Dodajte u COMMANDS dictionary
NAVIGATION_TRIGGERS = {
    "odvedi me": "navigate",
    "kako doći do": "directions",
    "kako doci do": "directions",
    "koji je put do": "directions",
    "koji je najkraći put": "directions",
    "koji je najkraci put": "directions",
    "put do": "directions",
    "navigiraj do": "navigate",
    "vodi me do": "navigate",
}

def parse_weather_query(text: str) -> Tuple[Optional[str], int]:
    """Parse weather query and return (city, days_offset)"""
    text = text.lower().strip()
    
    # Provjeri koordinate
    coords_match = re.search(r'coords:([-\d.]+),([-\d.]+)', text)
    if coords_match:
        lat, lon = coords_match.groups()
        try:
            return get_city_from_coords(float(lat), float(lon)), get_day_offset(text)
        except Exception as e:
            logger.error(f"Error getting city from coordinates: {e}")
            return None, 0

    # Provjeri specificiran grad
    for city_variant in CITY_NAMES.keys():
        if f" u {city_variant}" in text or f" za {city_variant}" in text:
            return CITY_NAMES[city_variant], get_day_offset(text)
            
    return None, get_day_offset(text)

def get_city_from_coords(lat: float, lon: float) -> Optional[str]:
    try:
        url = f"http://api.openweathermap.org/geo/1.0/reverse?lat={lat}&lon={lon}&limit=1&appid={WEATHER_API_KEY}"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                return data[0]['name']
    except Exception as e:
        logger.error(f"Reverse geocoding error: {e}")
    return None

async def process_weather_query(text: str, state: ConversationState) -> str:
    """Process weather query"""
    # Ako korisnik odgovara na pitanje za grad
    if state.weather_context and state.weather_context.asking_for_city:
        city = None
        for city_variant in CITY_NAMES.keys():
            if city_variant in text.lower():
                city = CITY_NAMES[city_variant]
                break
        
        if city:
            state.weather_context.asking_for_city = False
            return get_weather_info(city, state.weather_context.day_offset)
        else:
            return "Nisam prepoznao grad. Molim vas navedite neki hrvatski grad."
    
    # Novi vremenski upit
    city, days_offset = parse_weather_query(text)
    
    if city:
        return get_weather_info(city, days_offset)
    else:
        # Spremi kontekst i pitaj za grad
        state.weather_context = WeatherContext(
            asking_for_city=True,
            original_query=text,
            day_offset=days_offset
        )
        return "Za koji grad želite znati vremensku prognozu?"

MUSIC_APPS = {
    "spotify": {
        "mobile": "spotify://playlist/37i9dQZF1DXcBWIGoYBM5M",  # Today's Top Hits
        "web": "https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M"
    },
    "youtube": {
        "mobile": "vnd.youtube://playlist/PLw-VjHDlEOgs658kAHR_LAaILBXb-s6Q5",  # Popular Music
        "web": "https://www.youtube.com/playlist?list=PLw-VjHDlEOgs658kAHR_LAaILBXb-s6Q5"
    }
}

MUSIC_TRIGGERS = [
    "pusti glazbu", "pusti muziku", "upali glazbu", "upali muziku",
    "sviraj nešto", "sviraj pjesme", "pokreni glazbu", "pokreni muziku"
]

def handle_music_command(text: str = "") -> str:
    """Handle music related commands"""
    if any(platform in text.lower() for platform in ["spotify", "jutub", "youtube"]):
        platform = "spotify" if "spotify" in text.lower() else "youtube"
        urls = MUSIC_APPS[platform]
        return json.dumps({
            "type": "openUrl",
            "url": urls["web"],
            "mobileUrl": urls["mobile"],
            "message": f"Pokrećem glazbu na {platform.title()}"
        })
    
    # Ako platforma nije specificirana, pitaj korisnika
    return json.dumps({
        "type": "musicChoice",
        "message": "Gdje želite slušati glazbu - Spotify ili YouTube?",
        "options": ["Spotify", "YouTube"]
    })

# Dodaj u COMMANDS dictionary
for trigger in MUSIC_TRIGGERS:
    COMMANDS[trigger] = lambda: handle_music_command()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    try:
        await websocket.accept()
        client_id = str(id(websocket))
        conversation_states[client_id] = ConversationState()
        logger.info("WebSocket connection established")
        
        while True:
            try:
                text = await websocket.receive_text()
                logger.info(f"Received command: {text}")
                
                text = text.lower().strip()
                response = None
                state = conversation_states[client_id]

                if text.startswith(("što je", "šta je", "tko je", "ko je")):
                    response = search_web(text)
                elif any(phrase in text for phrase in [
                    "koliko je sati",
                    "koje je vrijeme na satu",
                    "kolko je sati",
                    "koje je vrijeme",
                    "ka je ura",
                    "ka je ura sad",
                    "ka je sad ura",
                    "kuliko je ur",
                    "ko vrime je",
                    "koliko je točno sati",
                    "koji je sat",
                    "koliko je sati sada",
                ]):
                    response = get_time()
                elif state.waiting_for_city:
                    city = None
                    for city_variant in CITY_NAMES.keys():
                        if city_variant in text or f"za {city_variant}" in text:
                            city = CITY_NAMES[city_variant]
                            break
                    
                    if city:
                        state.waiting_for_city = False
                        response = get_weather_info(city, "sutra" in text)
                    else:
                        response = "Nisam prepoznao grad. Molim vas navedite neki hrvatski grad."
                        
                else:
                    if any(phrase in text for phrase in [
                        "kakvo je vrijeme", "kakvo će biti vrijeme",
                        "hoće li padati kiša", "da li će padati kiša",
                        "kakva je prognoza", "kakvo vrijeme", "će daž", "vremenska prognoza",
                    ]):
                        city, _ = extract_city_and_time(text)
                        days_offset = get_day_offset(text)
                        
                        if city:
                            response = get_weather_info(city, days_offset)
                        else:
                            state.waiting_for_city = True
                            state.last_query_type = "weather"
                            response = "Za koji grad želite znati vremensku prognozu?"
                    
                    elif "koliko je sati" in text or "koje je vrijeme" in text:
                        response = get_time()
                    elif any(text.startswith(prefix) for prefix in ["što je", "šta je", "tko je", "ko je"]):
                        query = ' '.join(text.split()[2:])
                        if query:
                            response = search_web(query)
                        else:
                            response = "Molim vas dopunite pitanje."
                    elif any(word in text for word in ["otvori", "upali", "pokreni"]):
                        site_name = text.split(text.split()[0], 1)[1].strip()
                        response = open_website(site_name)
                    elif any(phrase in text for phrase in [
                        "koji je dan", "koji je datum",
                        "koji će dan biti", "koji dan je"
                    ]):
                        days_offset = get_day_offset(text)
                        response = get_date_info(days_offset)
                    elif text in COMMANDS:
                        cmd = COMMANDS[text]
                        if callable(cmd):
                            response = cmd()
                        else:
                            response = cmd
                    elif any(trigger in text.lower() for trigger in MUSIC_TRIGGERS):
                        response = handle_music_command(text)
                    elif "spotify" in text.lower() or "youtube" in text.lower():
                        response = handle_music_command(text)
                    else:
                        is_navigation = False
                        destination = ""
                        
                        for trigger, mode in NAVIGATION_TRIGGERS.items():
                            if trigger in text:
                                is_navigation = True
                                # Izvuci destinaciju iz teksta
                                destination = text.split(trigger, 1)[1].strip()
                                if destination:
                                    response = generate_maps_url(destination)
                                    break
                        
                        if not is_navigation:
                            response = flexible_match(text, COMMANDS)
                
                if not response:
                    response = random.choice(DEFAULT_RESPONSES)
                
                logger.info(f"Sending response: {response}")
                await websocket.send_text(response)
                
            except WebSocketDisconnect:
                del conversation_states[client_id]
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

current_dir = os.path.dirname(os.path.realpath(__file__))
frontend_dir = os.path.join(os.path.dirname(current_dir), 'frontend')

app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")

@app.get("/api/health")
async def health_check():
    return {"status": "online", "message": "SayMe API is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), log_level="info")


