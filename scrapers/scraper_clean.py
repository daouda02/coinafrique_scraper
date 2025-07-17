import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re
from typing import List, Dict, Optional
from urllib.parse import urljoin
import streamlit as st
import os

class CoinAfriqueScraperCleaned:
    """Scraper avec nettoyage des données"""
    
    def __init__(self, base_url: str = "https://sn.coinafrique.com"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive'
        })
        
        self.category_urls = {
            'villas': f"{self.base_url}/categorie/villas",
            'terrains': f"{self.base_url}/categorie/terrains", 
            'appartements': f"{self.base_url}/categorie/appartements"
        }
    
    def clean_price(self, price_text: str) -> str:
        """Nettoie le prix et le standardise"""
        if not price_text:
            return ""
        
        # Supprime les espaces et caractères spéciaux
        price_clean = re.sub(r'[^\d\s]', '', price_text)
        price_clean = re.sub(r'\s+', ' ', price_clean).strip()
        
        if 'fcfa' in price_text.lower() or 'cfa' in price_text.lower():
            return f"{price_clean} FCFA"
        else:
            return price_clean
    
    def clean_address(self, address_text: str) -> str:
        """Nettoie l'adresse"""
        if not address_text:
            return ""
        
        # Supprime les espaces multiples et les caractères spéciaux
        address_clean = re.sub(r'\s+', ' ', address_text.strip())
        # Supprime les caractères de nouvelle ligne
        address_clean = address_clean.replace('\n', ' ').replace('\r', ' ')
        
        return address_clean
    
    def extract_number_from_text(self, text: str) -> str:
        """Extrait les nombres d'un texte"""
        if not text:
            return ""
        
        numbers = re.findall(r'\d+', text)
        return numbers[0] if numbers else ""
    
    def get_page_content(self, url: str, page_num: int = 1) -> Optional[BeautifulSoup]:
        """Récupère le contenu d'une page"""
        try:
            if page_num > 1:
                url = f"{url}?page={page_num}"
            
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return BeautifulSoup(response.content, 'html.parser')
        except Exception as e:
            st.error(f"Erreur lors du chargement de la page {page_num}: {str(e)}")
            return None
    
    def extract_listings_from_page(self, soup: BeautifulSoup) -> List[Dict]:
        """Extrait les annonces d'une page"""
        listings_data = []
        
        # Trouver les images d'annonces
        images = soup.find_all('img', src=re.compile(r'thumb_\d+'))
        
        for img in images:
            try:
                data = {}
                
                # Image
                data['image_lien'] = img.get('src', '')
                
                # Description depuis l'attribut alt
                data['description'] = img.get('alt', '')
                
                # Trouver le conteneur parent
                container = img.find_parent(['div', 'article', 'section'])
                
                if container:
                    # Lien vers l'annonce
                    link = container.find('a', href=re.compile(r'/annonce/'))
                    if link:
                        data['lien_annonce'] = urljoin(self.base_url, link.get('href', ''))
                        data['titre'] = link.get('title', '') or link.text.strip()
                    else:
                        data['lien_annonce'] = ""
                        data['titre'] = ""
                    
                    # Texte complet du conteneur
                    container_text = container.get_text()
                    
                    # Extraction de l'adresse (après location_on)
                    address = ""
                    if 'location_on' in container_text:
                        location_match = re.search(r'location_on\s*([^0-9]+?)(?=favorite_border|$|\n)', container_text)
                        if location_match:
                            address = location_match.group(1).strip()
                    
                    data['adresse'] = self.clean_address(address)
                    
                    # Extraction du prix
                    price_patterns = [
                        r'(\d+(?:\s\d+)*)\s*(?:CFA|F\s*CFA|FCFA)',
                        r'(\d+(?:\.\d+)?)\s*(?:millions?|M)',
                        r'(\d+[\d\s]*)'
                    ]
                    
                    prix_trouve = ""
                    for pattern in price_patterns:
                        price_match = re.search(pattern, container_text, re.IGNORECASE)
                        if price_match:
                            prix_trouve = price_match.group(0)
                            break
                    
                    data['prix'] = self.clean_price(prix_trouve)
                
                else:
                    data['lien_annonce'] = ""
                    data['titre'] = ""
                    data['adresse'] = ""
                    data['prix'] = ""
                
                # Analyser la description complète
                full_text = f"{data['description']} {data['titre']}"
                
                # Superficie
                superficie_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:m²|m2|ha|hectares?)', full_text, re.IGNORECASE)
                data['superficie'] = superficie_match.group(0) if superficie_match else ""
                
                # Nombre de pièces
                pieces_match = re.search(r'(\d+)\s*(?:pièces?|chambres?|P\b)', full_text, re.IGNORECASE)
                data['nombre_pieces'] = pieces_match.group(1) if pieces_match else ""
                
                # Type d'annonce
                if any(word in full_text.lower() for word in ['location', 'louer', 'à louer']):
                    data['type_annonce'] = "Location"
                else:
                    data['type_annonce'] = "Vente"
                
                listings_data.append(data)
                
            except Exception:
                continue
        
        return listings_data
    
    def scrape_category(self, category: str, num_pages: int = 1) -> List[Dict]:
        """Scrape une catégorie complète"""
        
        if category not in self.category_urls:
            st.error(f"Catégorie '{category}' non supportée")
            return []
        
        all_data = []
        url = self.category_urls[category]
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for page in range(1, num_pages + 1):
            status_text.text(f"Scraping page {page}/{num_pages} de {category}...")
            
            soup = self.get_page_content(url, page)
            if not soup:
                continue
            
            page_data = self.extract_listings_from_page(soup)
            
            if page_data:
                all_data.extend(page_data)
                status_text.text(f"Page {page}: {len(page_data)} annonces extraites")
            else:
                status_text.text(f"Page {page}: aucune annonce trouvée")
            
            progress_bar.progress(page / num_pages)
            time.sleep(1)
        
        status_text.text(f"Scraping terminé! {len(all_data)} annonces collectées.")
        return all_data
    
    def save_to_csv(self, data: List[Dict], filename: str) -> str:
        """Sauvegarde les données en CSV"""
        if not data:
            return ""
        
        df = pd.DataFrame(data)
        os.makedirs('data/cleaned', exist_ok=True)
        filepath = f"data/cleaned/{filename}"
        df.to_csv(filepath, index=False, encoding='utf-8')
        return filepath
