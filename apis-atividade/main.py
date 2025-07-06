# main.py
import os
import logging
from typing import Optional

import httpx  # Biblioteca para fazer chamadas a APIs externas de forma assíncrona
from fastapi import FastAPI, APIRouter, Request, HTTPException, Query
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

# --- Configuração Inicial ---
# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# Configuração básica de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Variáveis Globais de Configuração ---
# Pega a chave da API do arquivo .env
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")

# --- Instância do FastAPI e Configuração de Templates ---
app = FastAPI(
    title="API Demo Hub",
    description="Um back-end para servir um site de demonstração de várias APIs.",
    version="1.0.0"
)

# Configura o diretório para servir arquivos estáticos (CSS, JS do front-end)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Configura o diretório de templates HTML
templates = Jinja2Templates(directory="templates")

# Cria um router para organizar os endpoints da nossa API proxy
api_router = APIRouter(prefix="/api")


# --- Evento de Startup ---
@app.on_event("startup")
async def on_startup():
    logger.info("Aplicação iniciando...")
    if not OPENWEATHER_API_KEY:
        logger.critical("ALERTA CRÍTICO: A variável OPENWEATHER_API_KEY não foi definida no arquivo .env!")
        logger.critical("A API de clima não irá funcionar.")
    else:
        logger.info("Chave da API de Clima carregada com sucesso.")
    logger.info("Servidor pronto para receber requisições.")


# === Endpoints para Servir as Páginas HTML (Views) ===

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Serve a página inicial com as 4 opções de API."""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/weather", response_class=HTMLResponse)
async def get_weather_page(request: Request):
    """Serve a página de demonstração da API de Clima."""
    return templates.TemplateResponse("weather.html", {"request": request})

@app.get("/cat", response_class=HTMLResponse)
async def get_cat_page(request: Request):
    """Serve a página de demonstração da API de Gatos."""
    return templates.TemplateResponse("cat.html", {"request": request})

@app.get("/translate", response_class=HTMLResponse)
async def get_translate_page(request: Request):
    """Serve a página de demonstração da API de Tradução."""
    return templates.TemplateResponse("translate.html", {"request": request})

@app.get("/crypto", response_class=HTMLResponse)
async def get_crypto_page(request: Request):
    """Serve a página de demonstração da API de Criptomoedas."""
    return templates.TemplateResponse("crypto.html", {"request": request})

# === Endpoints da API Proxy (Controllers) ===

# 1. API de Clima (com chave)
@api_router.get("/weather")
async def get_weather_data(city: str = Query(..., description="Nome da cidade para buscar o clima")):
    """Endpoint proxy para a API OpenWeatherMap. Esconde a chave de API."""
    if not OPENWEATHER_API_KEY:
        raise HTTPException(status_code=500, detail="A chave da API de clima não está configurada no servidor.")

    # URL da API externa
    url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={OPENWEATHER_API_KEY}&units=metric&lang=pt_br"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url)
            # Se a cidade não for encontrada, a API retorna 404
            if response.status_code == 404:
                raise HTTPException(status_code=404, detail="Cidade não encontrada.")
            
            # Garante que outros erros também sejam tratados
            response.raise_for_status()
            
            return JSONResponse(content=response.json())
        except httpx.RequestError as e:
            logger.error(f"Erro ao contatar a API de clima: {e}")
            raise HTTPException(status_code=503, detail="Serviço de clima indisponível no momento.")


# 2. API de Gato Aleatório (sem chave)
@api_router.get("/cat")
async def get_random_cat():
    """Endpoint proxy para a TheCatApi."""
    url = "https://api.thecatapi.com/v1/images/search?limit=1"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url)
            response.raise_for_status()
            return JSONResponse(content=response.json())
        except httpx.RequestError as e:
            logger.error(f"Erro ao contatar a API de gatos: {e}")
            raise HTTPException(status_code=503, detail="Serviço de gatos indisponível no momento.")


@api_router.get("/translate")
async def get_translation(
    text: str = Query(..., description="Texto a ser traduzido"),
    source_lang: str = Query("pt-br", description="Idioma de origem (ex: pt-br, en)"),
    target_lang: str = Query("en", description="Idioma de destino (ex: en, es, fr)")
):
    """Endpoint proxy para a API MyMemory para tradução bidirecional."""
    # A URL agora usa os dois parâmetros de idioma de forma dinâmica
    url = f"https://api.mymemory.translated.net/get?q={text}&langpair={source_lang}|{target_lang}"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url)
            response.raise_for_status()
            return JSONResponse(content=response.json())
        except httpx.RequestError as e:
            logger.error(f"Erro ao contatar a API de tradução: {e}")
            raise HTTPException(status_code=503, detail="Serviço de tradução indisponível no momento.")


# Lista com os IDs da CoinGecko para o TOP 10
# Nota: Os IDs podem ser diferentes dos símbolos (ex: BNB -> binancecoin, USDC -> usd-coin)
TOP_10_CRYPTO_IDS = [
    "bitcoin", "ethereum", "tether", "binancecoin", "solana", 
    "ripple", "usd-coin", "dogecoin", "cardano", "tron"
]

# 4. API de Criptomoedas (sem chave)
# Em main.py, substitua a função get_crypto_data por esta:

@api_router.get("/crypto")
async def get_crypto_data():
    """Endpoint proxy para a API CoinGecko com tratamento de erro de rate limit."""
    ids_string = ",".join(TOP_10_CRYPTO_IDS)
    url = f"https://api.coingecko.com/api/v3/coins/markets?vs_currency=brl&ids={ids_string}"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url)

            # --- TRATAMENTO DE ERRO ADICIONADO AQUI ---
            # Se a resposta da CoinGecko for 429 (Too Many Requests)...
            if response.status_code == 429:
                logger.warning("Rate limit excedido na API CoinGecko.")
                # ...nós levantamos uma exceção controlada do FastAPI...
                raise HTTPException(
                    status_code=429, # ...repassando o status 429 para o nosso front-end...
                    # ...e enviando uma mensagem clara no 'detail'.
                    detail="Muitas requisições. A API de criptomoedas pede para você aguardar cerca de 1 minuto."
                )
            
            # Se não for 429, verificamos outros erros possíveis (404, 500, etc.)
            response.raise_for_status()
            
            data = response.json()
            coin_map = {coin['id']: coin for coin in data}
            sorted_data = [coin_map[coin_id] for coin_id in TOP_10_CRYPTO_IDS if coin_id in coin_map]
            
            return JSONResponse(content=sorted_data)
            
        except httpx.RequestError as e:
            logger.error(f"Erro ao contatar a API CoinGecko: {e}")
            raise HTTPException(status_code=503, detail="Serviço de criptomoedas indisponível no momento.")
        
        # Opcional, mas bom: captura outros erros HTTP que não sejam o 429
        except httpx.HTTPStatusError as e:
            logger.error(f"Erro HTTP da API CoinGecko: {e}")
            raise HTTPException(status_code=e.response.status_code, detail="Erro de comunicação com a API de cripto.")

# Adiciona o router de API à aplicação principal
app.include_router(api_router)

# --- Para rodar o servidor localmente ---
if __name__ == "__main__":
    import uvicorn
    # uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
    uvicorn.run(app, host="127.0.0.1", port=8000)