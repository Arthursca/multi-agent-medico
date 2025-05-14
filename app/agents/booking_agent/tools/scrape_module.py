
import requests
from bs4 import BeautifulSoup
import re
import logging

# Configuração do logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


especialidades = ['nutrologo',
 'psiquiatra',
 'psicologo']
capitais = ['sao-paulo',
 'recife',
 'fortaleza']

def scrape_medicos( capital, especializacao):
    url = f'https://www.doctoralia.com.br/{especializacao}/{capital}/unimed'
    logger.info(f"Iniciando scrape em: {url}")
    response = requests.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')

    medicos = []
    resultados = soup.select('ul.search-list > li')
    logger.info(f"Encontrados {len(resultados)} resultados na página")

    for idx, item in enumerate(resultados, 1):
        nome_tag = item.select_one('span[data-tracking-id="result-card-name"]')
        nome = nome_tag.get_text(strip=True) if nome_tag else ''

        crm = ''
        rqe = ''
        for span in item.select('span.h5.font-weight-normal'):
            texto = span.get_text(separator=' ', strip=True)
            if 'CRM' in texto:
                m = re.search(r'CRM[:\s]*([A-Za-z0-9\-]+)', texto)
                if m: crm = m.group(1)
            if 'RQE' in texto:
                m = re.search(r'RQE[:\s]*N[oº]*\s*[:]?[\s]*([0-9]+)', texto)
                if m: rqe = m.group(1)

        endereco = ''
        addr_item = item.select_one('div[data-id="result-address-item"]')
        if addr_item:
            street = addr_item.select_one('meta[itemprop="streetAddress"]')
            city   = addr_item.select_one('meta[itemprop="addressLocality"]')
            region = addr_item.select_one('meta[itemprop="addressRegion"]')
            if street and city and region:
                endereco = f"{street['content']}, {city['content']} - {region['content']}"
            else:
                endereco = addr_item.get_text(separator=' ', strip=True)

        medico = {
            'nome': nome,
            'endereco': endereco,
            'crm': crm,
            'rqe': rqe,
            'capital': capital,
            'especializacao': especializacao
        }
        medicos.append(medico)

        logger.info(f"[{idx}/{len(resultados)}] {nome} | CRM: {crm or '—'} | RQE: {rqe or '—'} | Endereço: {endereco}")

    return medicos

