import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import os
import json

# Configuration de la page
st.set_page_config(
    page_title="CoinAfrique Scraper",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Import des scrapers
try:
    from scrapers.scraper_clean import CoinAfriqueScraperCleaned
    from scrapers.web_scraper import CoinAfriqueScraperRaw
except ImportError:
    st.error("Erreur: Scrapers non trouvés. Vérifiez les fichiers dans le dossier scrapers/")
    st.stop()

# Créer les dossiers
os.makedirs('data/cleaned', exist_ok=True)
os.makedirs('data/raw', exist_ok=True)
os.makedirs('data/evaluations', exist_ok=True)

def main():
    st.title("CoinAfrique Scraper")
    
    # Sidebar
    with st.sidebar:
        st.header("Navigation")
        page = st.selectbox(
            "Choisir une page",
            [
                "Scraper avec nettoyage", 
                "Web Scraper (sans nettoyage)", 
                "Dashboard", 
                "Téléchargements", 
                "Évaluation"
            ],
            index=0
        )
        
        st.markdown("---")
        display_stats()
    
    # Router
    if page == "Scraper avec nettoyage":
        page_scraping_cleaned()
    elif page == "Web Scraper (sans nettoyage)":
        page_scraping_raw()
    elif page == "Dashboard":
        page_dashboard()
    elif page == "Téléchargements":
        page_downloads()
    elif page == "Évaluation":
        page_evaluation()

def display_stats():
    """Afficher les statistiques dans la sidebar"""
    st.subheader("Statistiques")
    
    try:
        # Compter les fichiers nettoyés
        cleaned_files = 0
        raw_files = 0
        
        if os.path.exists('data/cleaned'):
            cleaned_files = len([f for f in os.listdir('data/cleaned') if f.endswith('.csv')])
        
        if os.path.exists('data/raw'):
            raw_files = len([f for f in os.listdir('data/raw') if f.endswith('.csv')])
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Données nettoyées", cleaned_files)
        with col2:
            st.metric("Données brutes", raw_files)
        
        # Dernière activité
        all_files = []
        if os.path.exists('data/cleaned'):
            cleaned_list = [f'data/cleaned/{f}' for f in os.listdir('data/cleaned') if f.endswith('.csv')]
            all_files.extend(cleaned_list)
        if os.path.exists('data/raw'):
            raw_list = [f'data/raw/{f}' for f in os.listdir('data/raw') if f.endswith('.csv')]
            all_files.extend(raw_list)
        
        if all_files:
            try:
                latest_file = max(all_files, key=lambda x: os.path.getctime(x))
                latest_time = datetime.fromtimestamp(os.path.getctime(latest_file))
                st.caption(f"Dernier scraping: {latest_time.strftime('%d/%m/%Y %H:%M')}")
            except (OSError, ValueError) as e:
                st.caption("Dernière activité: N/A")
        else:
            st.caption("Aucune activité récente")
            
    except Exception as e:
        st.error(f"Erreur stats: {str(e)}")
        st.metric("Fichiers totaux", 0)

def page_scraping_cleaned():
    """Page pour le scraping avec nettoyage"""
    st.header("Scraper avec nettoyage des données")
    st.markdown("Utilise BeautifulSoup pour extraire et nettoyer les données selon les variables spécifiées.")
    
    # Variables par catégorie
    variables_info = {
        'villas': "**Variables extraites:** type annonce, nombre pièces, prix, adresse, image_lien",
        'terrains': "**Variables extraites:** superficie, prix, adresse, image_lien", 
        'appartements': "**Variables extraites:** nombre pièces, prix, adresse, image_lien"
    }
    
    col1, col2 = st.columns(2)
    
    with col1:
        category = st.selectbox(
            "Choisir une catégorie",
            ["villas", "terrains", "appartements"],
            key="clean_category"
        )
    
    with col2:
        num_pages = st.number_input(
            "Nombre de pages à scraper",
            min_value=1,
            max_value=20,
            value=1,
            key="clean_pages"
        )
    
    # Affichage des variables
    st.info(variables_info[category])
    
    if st.button("Lancer le scraping avec nettoyage", type="primary", use_container_width=True):
        try:
            scraper = CoinAfriqueScraperCleaned()
            
            with st.spinner("Scraping en cours..."):
                data = scraper.scrape_category(category, num_pages)
            
            if data:
                # Sauvegarder dans session_state pour persister les données
                st.session_state.cleaned_scraped_data = data
                st.session_state.cleaned_scraped_category = category
                st.session_state.cleaned_scraper_instance = scraper
                
                st.success(f"{len(data)} annonces collectées avec succès!")
                
            else:
                st.error("Aucune donnée collectée. Vérifiez la connexion ou réessayez.")
        except Exception as e:
            st.error(f"Erreur lors du scraping: {str(e)}")
    
    if 'cleaned_scraped_data' in st.session_state and st.session_state.cleaned_scraped_data:
        data = st.session_state.cleaned_scraped_data
        df = pd.DataFrame(data)
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total annonces", len(data))
        
        with col2:
            prix_count = len([d for d in data if d.get('prix', '').strip()])
            st.metric("Avec prix", prix_count)
        
        with col3:
            adresse_count = len([d for d in data if d.get('adresse', '').strip()])
            st.metric("Avec adresse", adresse_count)
        
        with col4:
            if st.session_state.cleaned_scraped_category != 'terrains':
                pieces_count = len([d for d in data if d.get('nombre_pieces', '').strip()])
                st.metric("Avec pièces", pieces_count)
            else:
                superficie_count = len([d for d in data if d.get('superficie', '').strip()])
                st.metric("Avec superficie", superficie_count)
        
        # Aperçu des données
        st.subheader("Aperçu des données nettoyées")
        st.dataframe(df, use_container_width=True, height=300)
        
        # Sauvegarde
        st.markdown("---")
        col1, col2 = st.columns([1, 1])
        
        with col1:
            if st.button("Sauvegarder les données", type="secondary", use_container_width=True):
                try:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"{st.session_state.cleaned_scraped_category}_cleaned_{timestamp}.csv"
                    
                    # Créer le dossier s'il n'existe pas
                    os.makedirs('data/cleaned', exist_ok=True)
                    
                    # Sauvegarder directement
                    filepath = f"data/cleaned/{filename}"
                    df.to_csv(filepath, index=False, encoding='utf-8')
                    
                    if os.path.exists(filepath):
                        st.success(f"Données sauvegardées: {filename}")
                    else:
                        st.error("Erreur lors de la sauvegarde")
                        
                except Exception as e:
                    st.error(f"Erreur sauvegarde: {str(e)}")
        
        with col2:
            # Téléchargement export
            try:
                csv_data = df.to_csv(index=False, encoding='utf-8')
                st.download_button(
                    label="Télécharger CSV",
                    data=csv_data,
                    file_name=f"{st.session_state.cleaned_scraped_category}_cleaned_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"Erreur téléchargement: {str(e)}")
        
        # Effacer les données
        if st.button("Effacer les données", type="secondary"):
            if 'cleaned_scraped_data' in st.session_state:
                del st.session_state.cleaned_scraped_data
            if 'cleaned_scraped_category' in st.session_state:
                del st.session_state.cleaned_scraped_category
            if 'cleaned_scraper_instance' in st.session_state:
                del st.session_state.cleaned_scraper_instance
            st.rerun()

def page_scraping_raw():
    """Page pour le scraping sans nettoyage"""
    st.header("Web Scraper (sans nettoyage)")
    st.markdown("Collecte les données brutes sans traitement selon les variables spécifiées.")
    
    # Variables par catégorie
    variables_info = {
        'villas': "**Variables extraites:** nombre pièces, nombre salle bain, superficie, adresse",
        'terrains': "**Variables extraites:** superficie, prix, adresse, image_lien", 
        'appartements': "**Variables extraites:** nombre pièces, nombre salle bain, superficie, adresse"
    }
    
    col1, col2 = st.columns(2)
    
    with col1:
        category = st.selectbox(
            "Choisir une catégorie",
            ["villas", "terrains", "appartements"],
            key="raw_category"
        )
    
    with col2:
        num_pages = st.number_input(
            "Nombre de pages à scraper",
            min_value=1,
            max_value=20,
            value=1,
            key="raw_pages"
        )
    
    # Affichage des variables
    st.info(variables_info[category])
    
    if st.button("Lancer le web scraping (sans nettoyage)", type="primary", use_container_width=True):
        try:
            scraper = CoinAfriqueScraperRaw()
            
            with st.spinner("Web scraping en cours..."):
                data = scraper.scrape_category(category, num_pages)
            
            if data:
                # Sauvegarder dans session_state pour persister les données
                st.session_state.raw_scraped_data = data
                st.session_state.raw_scraped_category = category
                st.session_state.raw_scraper_instance = scraper
                
                st.success(f"{len(data)} annonces collectées (données brutes)!")
                
            else:
                st.error("Aucune donnée collectée.")
        except Exception as e:
            st.error(f"Erreur lors du scraping: {str(e)}")
    
    if 'raw_scraped_data' in st.session_state and st.session_state.raw_scraped_data:
        data = st.session_state.raw_scraped_data
        df = pd.DataFrame(data)
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total annonces", len(data))
        
        with col2:
            st.metric("Colonnes", len(df.columns))
        
        with col3:
            non_empty = df.notna().sum().sum()
            st.metric("Données non vides", non_empty)
        
        with col4:
            completude = (non_empty / (len(df) * len(df.columns)) * 100) if len(df) > 0 else 0
            st.metric("Complétude", f"{completude:.0f}%")
        
        # Aperçu des données
        st.subheader("Aperçu des données brutes")
        st.dataframe(df, use_container_width=True, height=300)
        
        # Sauvegarde
        st.markdown("---")
        col1, col2 = st.columns([1, 1])
        
        with col1:
            if st.button("Sauvegarder les données brutes", type="secondary", use_container_width=True):
                try:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"{st.session_state.raw_scraped_category}_raw_{timestamp}.csv"
                    
                    # Créer le dossier s'il n'existe pas
                    os.makedirs('data/raw', exist_ok=True)
                    
                    # Sauvegarder directement
                    filepath = f"data/raw/{filename}"
                    df.to_csv(filepath, index=False, encoding='utf-8')
                    
                    if os.path.exists(filepath):
                        st.success(f"Données sauvegardées: {filename}")
                    else:
                        st.error("Erreur lors de la sauvegarde")
                        
                except Exception as e:
                    st.error(f"Erreur sauvegarde: {str(e)}")
        
        with col2:
            # Téléchargement export
            try:
                csv_data = df.to_csv(index=False, encoding='utf-8')
                st.download_button(
                    label="Télécharger CSV",
                    data=csv_data,
                    file_name=f"{st.session_state.raw_scraped_category}_raw_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"Erreur téléchargement: {str(e)}")
        
        # Effacer les données
        if st.button("Effacer les données brutes", type="secondary"):
            if 'raw_scraped_data' in st.session_state:
                del st.session_state.raw_scraped_data
            if 'raw_scraped_category' in st.session_state:
                del st.session_state.raw_scraped_category
            if 'raw_scraper_instance' in st.session_state:
                del st.session_state.raw_scraper_instance
            st.rerun()

def page_dashboard():
    """Dashboard d'analyse des données nettoyées uniquement"""
    st.header("Dashboard des données")
    st.markdown("Visualisation et analyse des **données nettoyées** uniquement.")
    
    # Sélection du fichier
    try:
        cleaned_files = []
        if os.path.exists('data/cleaned'):
            cleaned_files = [f for f in os.listdir('data/cleaned') if f.endswith('.csv')]
        
        if not cleaned_files:
            st.warning("Aucun fichier de données nettoyées trouvé. Effectuez d'abord un scraping avec nettoyage.")
            return
        
        selected_file = st.selectbox(
            "Choisir un fichier de données nettoyées",
            cleaned_files,
            format_func=lambda x: f"{x} ({get_file_size(f'data/cleaned/{x}')})"
        )
        
        df = pd.read_csv(f"data/cleaned/{selected_file}")
        
        if df.empty:
            st.warning("Le fichier sélectionné est vide.")
            return
        
        # Informations générales
        st.subheader("Vue d'ensemble")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total annonces", len(df))
        with col2:
            st.metric("Variables", len(df.columns))
        with col3:
            completude = (df.notna().sum().sum() / (len(df) * len(df.columns)) * 100)
            st.metric("Complétude", f"{completude:.1f}%")
        with col4:
            if 'prix' in df.columns:
                prix_non_vides = df[df['prix'].astype(str).str.len() > 0].shape[0]
                st.metric("Avec prix", prix_non_vides)
        
        # Graphiques
        st.subheader("Analyses")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Analyse des localisations
            if 'adresse' in df.columns:
                st.write("**Top des localisations**")
                adresses = df['adresse'].value_counts().head(10)
                if not adresses.empty:
                    fig = px.bar(
                        x=adresses.values,
                        y=adresses.index,
                        orientation='h',
                        title="Répartition par localisation"
                    )
                    fig.update_layout(height=400, showlegend=False, margin=dict(l=0, r=0, t=40, b=0))
                    st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Analyse des types d'annonces
            if 'type_annonce' in df.columns:
                st.write("**Types d'annonces**")
                types = df['type_annonce'].value_counts()
                if not types.empty:
                    fig = px.pie(values=types.values, names=types.index, title="Répartition Vente/Location")
                    fig.update_layout(height=400, margin=dict(l=0, r=0, t=40, b=0))
                    st.plotly_chart(fig, use_container_width=True)
            elif 'nombre_pieces' in df.columns:
                st.write("**Répartition par pièces**")
                pieces = extract_numbers_from_column(df, 'nombre_pieces')
                if pieces:
                    pieces_count = pd.Series(pieces).value_counts().sort_index()
                    fig = px.bar(x=pieces_count.index, y=pieces_count.values, title="Nombre de pièces")
                    fig.update_layout(height=400, margin=dict(l=0, r=0, t=40, b=0))
                    st.plotly_chart(fig, use_container_width=True)
        
        # Analyse des prix
        if 'prix' in df.columns:
            st.subheader("Analyse des prix")
            prix_nums = extract_numbers_from_column(df, 'prix')
            if prix_nums:
                fig = px.histogram(x=prix_nums, nbins=20, title="Distribution des prix")
                fig.update_layout(
                    xaxis_title="Prix", 
                    yaxis_title="Nombre d'annonces",
                    height=400
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # Statistiques
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Prix moyen", f"{sum(prix_nums)/len(prix_nums):,.0f}")
                with col2:
                    st.metric("Prix médian", f"{sorted(prix_nums)[len(prix_nums)//2]:,.0f}")
                with col3:
                    st.metric("Prix max", f"{max(prix_nums):,.0f}")
        
        # Tableau des données
        st.subheader("Données détaillées")
        st.dataframe(df, use_container_width=True, height=400)
        
    except Exception as e:
        st.error(f"Erreur lors du chargement: {str(e)}")

def page_downloads():
    """Page de téléchargement des données"""
    st.header("Téléchargements")
    st.markdown("Téléchargez les données scrapées.")
    
    # Données nettoyées
    st.subheader("Données nettoyées")
    display_files_for_download('data/cleaned', "Aucun fichier de données nettoyées.")
    
    st.markdown("---")
    
    # Données brutes
    st.subheader("Données brutes (Web Scraper)")
    display_files_for_download('data/raw', "Aucun fichier de données brutes.")

def display_files_for_download(folder_path, empty_message):
    """Affiche les fichiers pour téléchargement"""
    if not os.path.exists(folder_path):
        st.info(empty_message)
        return
    
    files = [f for f in os.listdir(folder_path) if f.endswith('.csv')]
    
    if not files:
        st.info(empty_message)
        return
    
    for file in files:
        col1, col2, col3 = st.columns([3, 1, 1])
        
        with col1:
            st.write(f"**{file}**")
            try:
                file_date = datetime.fromtimestamp(os.path.getctime(f"{folder_path}/{file}"))
                st.caption(f"Créé le {file_date.strftime('%d/%m/%Y à %H:%M')}")
            except:
                st.caption("Date inconnue")
        
        with col2:
            st.write(get_file_size(f"{folder_path}/{file}"))
        
        with col3:
            try:
                with open(f"{folder_path}/{file}", 'rb') as f:
                    st.download_button(
                        label="Télécharger",
                        data=f.read(),
                        file_name=file,
                        mime='text/csv',
                        key=f"download_{file}",
                        use_container_width=True
                    )
            except Exception as e:
                st.error(f"Erreur: {str(e)}")

def page_evaluation():
    """Page d'évaluation avec Kobo """
    st.header("Évaluation CoinAfrique Scraping")
    st.markdown("Merci de donner votre avis pour m'aider à améliorer l'application !")
    
    with st.expander("Voir le formulaire", expanded=True):
        st.markdown("""
        <div style="text-align: center;">
            <iframe src="https://ee.kobotoolbox.org/i/icgDbNfi" 
                    width="100%" 
                    height="600" 
                    frameborder="0" 
                    marginheight="0" 
                    marginwidth="0">
                Chargement du formulaire...
            </iframe>
        </div>
        """, unsafe_allow_html=True)
    
    
# Fonctions utilitaires
def get_file_size(filepath):
    """Retourne la taille d'un fichier formatée"""
    try:
        size = os.path.getsize(filepath)
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size/1024:.1f} KB"
        else:
            return f"{size/(1024*1024):.1f} MB"
    except:
        return "N/A"

def extract_numbers_from_column(df, column):
    """Extrait les nombres d'une colonne"""
    numbers = []
    for value in df[column].dropna():
        import re
        nums = re.findall(r'\d+', str(value))
        if nums:
            try:
                numbers.append(int(''.join(nums)))
            except:
                continue
    return numbers

def save_evaluation(data):
    """Sauvegarde l'évaluation"""
    try:
        os.makedirs('data/evaluations', exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"data/evaluations/evaluation_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return filename
    except Exception as e:
        st.error(f"Erreur sauvegarde évaluation: {str(e)}")
        return None

if __name__ == "__main__":
    main()
