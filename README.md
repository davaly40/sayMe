# SayMe - Hrvatski Glasovni Asistent

## Postavljanje razvoje okoline

1. Kreiranje virtualnog okruženja:
```bash
python -m venv venv

# Za Windows
.\venv\Scripts\activate

# Za Linux/Mac
source venv/bin/activate
```

2. Instalacija potrebnih paketa:
```bash
cd backend
pip install -r requirements.txt
```

3. Pokretanje backend servera:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

4. Pokretanje frontend dijela:
- Instalirajte [Live Server](https://marketplace.visualstudio.com/items?itemName=ritwickdey.LiveServer) ekstenziju u VS Code
- Desni klik na `frontend/index.html` i odaberite "Open with Live Server"

## Testiranje aplikacije

1. Otvorite preglednik na `http://localhost:5500` (ili port koji Live Server koristi)
2. Kliknite na "Započni Slušanje" gumb
3. Izgovorite neku od podržanih naredbi:
   - "Kako se zoveš?"
   - "Koje ti je ime?"
   - "Tko te je napravio?"
   - "Tko ti je tvorac?"
   - "Koliko je sati?"
   - "Otvori YouTube"

## Napomene
- Provjerite da je mikrofon dozvoljen u pregledniku
- Backend mora biti pokrenut na portu 8000
- Ako koristite Chrome, dopustite pristup mikrofonu kada vas preglednik to zatraži

## Deployment

### GitHub

1. Kreirajte novi repository na GitHubu
2. Inicirajte Git i pushajte kod:
```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/sayMe.git
git push -u origin main
```

### Render

1. Idite na [Render Dashboard](https://dashboard.render.com)
2. Kliknite "New +" i odaberite "Web Service"
3. Povežite svoj GitHub repository
4. Postavite sljedeće:
   - Name: `sayme-backend` (ili željeno ime)
   - Environment: `Python`
   - Build Command: `pip install -r backend/requirements.txt`
   - Start Command: `cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Kliknite "Create Web Service"

### Frontend Deployment

1. U Render dashboardu, kliknite "New +" i odaberite "Static Site"
2. Povežite isti GitHub repository
3. Postavite:
   - Name: `sayme-frontend` (ili željeno ime)
   - Publish directory: `frontend`
4. U `frontend/script.js` ažurirajte WebSocket URL da pokazuje na vaš backend:
```javascript
const wsUrl = window.location.hostname === 'localhost' 
  ? 'ws://localhost:8000/ws'
  : 'wss://your-backend-url.onrender.com/ws';
socket = new WebSocket(wsUrl);
```

## Environment Variables

Na Render dashboardu postavite sljedeće environment varijable:
- `WEATHER_API_KEY`: Vaš OpenWeatherMap API ključ
- `PORT`: Ostavite prazno (Render će automatski postaviti)
