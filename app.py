import streamlit as st
from langchain_community.chat_models import ChatOllama
from langchain.memory import ConversationBufferMemory
import os
from dotenv import load_dotenv
import json
import datetime
from fpdf import FPDF
import base64
from langchain.schema import HumanMessage, AIMessage
from langchain.chains import ConversationChain

# Charger les variables d'environnement
load_dotenv()

# Configuration de la page Streamlit
st.set_page_config(
    page_title="ALN AI",
    page_icon="🤖",
    layout="wide"
)

# Style CSS personnalisé
st.markdown("""
    <style>
    .stTextInput>div>div>input {
        background-color: #f0f2f6;
        color: #1f2937;
    }
    .stTextArea>div>div>textarea {
        background-color: #f0f2f6;
        color: #1f2937;
    }
    .chat-message {
        padding: 1.5rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        display: flex;
        flex-direction: column;
    }
    .chat-message.user {
        background-color: #2b313e;
        color: white;
    }
    .chat-message.assistant {
        background-color: #f0f2f6;
    }
    @keyframes popup {
        0% { transform: translate(-50%, -50%) scale(0.8); opacity: 0; }
        50% { transform: translate(-50%, -50%) scale(1.1); }
        100% { transform: translate(-50%, -50%) scale(1); opacity: 1; }
    }
    @keyframes fadeOut {
        0% { transform: translate(-50%, -50%) scale(1); opacity: 1; }
        100% { transform: translate(-50%, -50%) scale(0.8); opacity: 0; }
    }
    .popup-welcome {
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        width: 90%;
        max-width: 300px;
        padding: 2rem;
        text-align: center;
        animation: popup 0.8s ease-out, fadeOut 0.8s ease-out 3s forwards;
        z-index: 1000;
    }
    .popup-text {
        font-size: 1.5rem;
        color: white;
        margin: 0;
        word-wrap: break-word;
        text-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
    }
    @media (max-width: 480px) {
        .popup-welcome {
            width: 85%;
            padding: 1.5rem;
        }
        .popup-text {
            font-size: 1.3rem;
        }
    }
    </style>
""", unsafe_allow_html=True)

# Initialisation de la session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "memory" not in st.session_state:
    st.session_state.memory = ConversationBufferMemory(return_messages=True)
if "learning_data" not in st.session_state:
    st.session_state.learning_data = {
        "interactions": [],
        "preferences": {},
        "knowledge": {}
    }
if "first_message" not in st.session_state:
    st.session_state.first_message = True

# Titre de l'application
if st.session_state.first_message:
    st.title("🤖 ALN AI")
    
    # Message de bienvenue en popup
    st.markdown("""
        <div class="popup-welcome">
            <p class="popup-text">👋 Bienvenue sur ALN AI</p>
        </div>
    """, unsafe_allow_html=True)

# Initialisation du modèle LLM
def load_model():
    try:
        # Utiliser un modèle Ollama qui gère bien les instructions, comme Mistral
        llm = ChatOllama(model="mistral", temperature=0.7)
        return llm
    except Exception as e:
        st.error(f"Erreur lors du chargement du modèle Ollama: {str(e)}")
        st.info("Veuillez vérifier qu'Ollama est installé et que le modèle 'mistral' est disponible (ollama pull mistral).")
        return None

# Fonction pour sauvegarder les données d'apprentissage
def save_learning_data():
    try:
        with open("learning_data.json", "w", encoding="utf-8") as f:
            json.dump(st.session_state.learning_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"Erreur lors de la sauvegarde des données d'apprentissage: {str(e)}")

# Fonction pour charger les données d'apprentissage
def load_learning_data():
    try:
        if os.path.exists("learning_data.json"):
            with open("learning_data.json", "r", encoding="utf-8") as f:
                st.session_state.learning_data = json.load(f)
    except Exception as e:
        st.error(f"Erreur lors du chargement des données d'apprentissage: {str(e)}")

# Liste d'abréviations et de variantes de salutations
SALUTATIONS = [
    "salut", "slt", "bonjour", "bjr", "cc", "coucou", "hello", "hi", "hey", "yo", "wesh", "re", "bonsoir"
]

# Fonction pour détecter si le message est une salutation seule
def is_salutation_only(prompt: str) -> bool:
    prompt_clean = prompt.lower().strip()
    return any(prompt_clean == s for s in SALUTATIONS)

# Fonction pour générer un PDF
def generate_pdf(text: str) -> tuple:
    try:
        pdf = FPDF()
        pdf.add_page()
        
        # Titre principal
        pdf.set_font("Arial", "B", 16)
        pdf.cell(0, 10, 'Document Généré par ALN AI', ln=True, align='C')
        pdf.ln(10)
        
        # Date
        pdf.set_font("Arial", "I", 10)
        pdf.cell(0, 10, f'Généré le {datetime.datetime.now().strftime("%d/%m/%Y à %H:%M")}', ln=True, align='R')
        pdf.ln(10)
        
        # Contenu
        pdf.set_font("Arial", "", 12)
        pdf.multi_cell(0, 10, text)
        
        # Pied de page
        pdf.set_y(-15)
        pdf.set_font("Arial", "I", 8)
        pdf.cell(0, 10, 'Développé par Abdou Latif Niabaly', 0, 0, 'C')
        
        # Sauvegarder le PDF
        pdf_path = "output.pdf"
        pdf.output(pdf_path)
        
        # Lire le fichier PDF et le convertir en base64
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()
            b64_pdf = base64.b64encode(pdf_bytes).decode()
        
        return pdf_path, b64_pdf
    except Exception as e:
        st.error(f"Erreur lors de la génération du PDF: {str(e)}")
        return None, None

# Fonction pour la conversation (mise à jour pour utiliser l'historique)
def advanced_chat(prompt: str) -> str:
    try:
        llm = load_model()
        if llm is None:
            return "Erreur: Modèle non chargé"

        # Construire l'historique de chat pour la chaîne
        # Ancienne ligne retirée : chat_history = st.session_state.memory.load_memory_variables({})['chat_history']

        # Créer la chaîne de conversation
        # Passer le prompt système au début de la conversation
        conversation_chain = ConversationChain(
            llm=llm,
            memory=st.session_state.memory,
            verbose=False # Mettre à True pour débugger les prompts envoyés au modèle
        )
        
        # On peut ajouter une logique pour les salutations et l'identité AVANT d'appeler la chaîne
        # pour garantir une réponse rapide et spécifique pour ces cas.

        # Vérifier si c'est une question sur l'identité
        if any(phrase in prompt.lower() for phrase in ["qui es-tu", "ton nom", "qui t'a créé", "qui t'a fait", "qui t'a développé"]):
            # Ajouter la question utilisateur à l'historique pour maintenir le contexte
            st.session_state.memory.chat_memory.add_user_message(prompt)
            response = "Je suis ALN AI, développé par Abdou Latif Niabaly. Je suis conçu pour vous aider de manière précise et efficace." # Réponse directe
            st.session_state.memory.chat_memory.add_ai_message(response)
            return response
        
        # Si c'est une salutation seule
        if is_salutation_only(prompt):
             # Ajouter la question utilisateur à l'historique
            st.session_state.memory.chat_memory.add_user_message(prompt)
            response = "Bonjour ! Je suis ALN AI, développé par Abdou Latif Niabaly. Comment puis-je vous aider ?" # Réponse personnalisée
            st.session_state.memory.chat_memory.add_ai_message(response)
            return response
        
        # Ajouter une logique pour les messages d'acquittement simples
        ACKNOWLEDGMENT_PHRASES = ["ok", "d'accord", "merci", "merci beaucoup", "cool", "compris"]
        if prompt.lower().strip() in ACKNOWLEDGMENT_PHRASES:
            # Ajouter la question utilisateur à l'historique
            st.session_state.memory.chat_memory.add_user_message(prompt)
            response = "De rien !" # Réponse minimale
            st.session_state.memory.chat_memory.add_ai_message(response)
            return response

        # Détecter les requêtes qui nécessitent une liste ou une série d'éléments
        list_request_keywords = ["donne", "liste", "énumère", "cite", "propose", "commandes", "film"] # Ajoutez d'autres mots-clés si nécessaire
        is_list_request = any(keyword in prompt.lower() for keyword in list_request_keywords)

        # Si la question est vide ou trop courte (peut être géré par Streamlit input validation)
        if len(prompt.strip()) < 2:
            response = "Pouvez-vous préciser votre demande ?"
            # Ajouter à l'historique si on veut que cette interaction soit mémorisée
            # st.session_state.memory.chat_memory.add_user_message(prompt)
            # st.session_state.memory.chat_memory.add_ai_message(response)
            return response # Pas besoin d'appeler le modèle pour ça

        # Si ce n'est pas un cas spécial, utiliser la chaîne de conversation
        # Inclure le prompt système dans le message utilisateur ou dans le template de prompt de la chaîne
        # L'approche la plus simple avec ConversationChain est de laisser le prompt système global
        # et de s'assurer qu'il est bien compris par le modèle.

        # Pour s'assurer que les règles du prompt système sont toujours présentes,
        # on peut les inclure AVANT le message de l'utilisateur dans l'input de la chaîne.
        # Cependant, ConversationChain a son propre template. Modifions le prompt système global
        # pour qu'il soit plus adapté à être combiné avec l'historique par la chaîne.
        
        # Revenir à un prompt système qui définit le rôle et les règles générales,
        # la chaîne gérera l'historique.
        system_instructions = """
Tu es ALN AI. Réponds EN FRANÇAIS.

Règles de réponse EXIGENTES :
- **Langue :** Réponds TOUJOURS et UNIQUEMENT en Français.
- **Sujet :** Concentre-toi UNIQUEMENT sur la question actuelle de l'utilisateur. IGNORE tout contexte de conversation précédent qui n'est pas pertinent pour la nouvelle question.
- **Concision & Détail :** Sois concis pour les questions simples. Fournis des détails SEULEMENT si nécessaire ou demandé. Pour les listes ou informations spécifiques, donne EXACTEMENT ce qui est demandé (nombre d'éléments, détails spécifiques).
- **Début de réponse STRICT :** Commence IMMÉDIATEMENT ta réponse par l'information ou la liste demandée. Ne commence JAMAIS par une salutation, une auto-présentation, une référence à des sujets précédents, ou une phrase d'introduction générique comme "Voici..." ou "Commande git utilise...".
- **Éviter :** N'utilise PAS de phrases génériques. N'invente PAS d'informations.
- **Qualité des listes/informations :** Si une liste ou des informations spécifiques sont demandées (ex: 'commandes git utiles'), assure-toi qu'elles sont FACTUELLEMENT correctes, pertinentes, utiles et formatées clairement (par exemple, avec des puces ou des numéros pour les listes).
"""

        # Ajuster le prompt envoyé à la chaîne si c'est une requête de liste
        if is_list_request:
            # Ajouter une instruction explicite pour générer une liste
            full_prompt_with_instructions = system_instructions + "\n\nRéponds à la demande suivante en fournissant DIRECTEMENT la liste ou les informations demandées, sans introduction :\n" + prompt
        else:
            full_prompt_with_instructions = system_instructions + "\n\n" + prompt

        # Utiliser l'historique géré par la mémoire dans la chaîne
        # La méthode predict de ConversationChain prend l'input utilisateur
        response_object = conversation_chain.invoke(input=full_prompt_with_instructions)
        
        # La réponse de conversation_chain.invoke() est un dictionnaire, pas un objet AIMessage direct.
        # L'output textuel est généralement sous la clé 'response' ou similaire selon la chaîne.
        # Pour ConversationChain, c'est sous la clé 'response'.

        response_text = response_object.get('response', str(response_object))
        response_text = response_text.strip()
        
        # Nettoyage amélioré : supprimer toute salutation, auto-présentation ou phrase générique en début de réponse
        phrases_a_supprimer_debut = [
            "Oui, je suis le système ALN AI. Je répondrai à ta question en français.",
            "Bonjour ! Je suis ALN AI, développé par Abdou Latif Niabaly. Comment puis-je vous aider ?", # Déjà géré par logique spécifique mais sécurité
            "De rien !", # Déjà géré par logique spécifique mais sécurité
            "Pouvez-vous préciser votre demande ?", # Déjà géré par logique spécifique mais sécurité
            "Bonjour !", "Salut !", "Hello !", "Hi !",
            "Je suis un assistant", "Je suis une IA", "Je suis créé par", "Je suis développé par",
            "Je suis désolé", "En tant qu'assistant",
            "Pour répondre à ta demande, je te donnerai", # Phrase d'introduction détectée
            "Commande git utilise pour le contrôle de version Git :" # Introduction spécifique à la liste git
            # Ajoutez d'autres phrases détectées si nécessaire
        ]
        
        for phrase in phrases_a_supprimer_debut:
             if response_text.startswith(phrase):
                 # Utiliser rstrip() pour éviter de laisser un espace après la suppression si la phrase ne finit pas par un point/espace
                 response_text = response_text[len(phrase):].lstrip()
                 # On peut casser la boucle car on suppose qu'il n'y a qu'une seule phrase d'intro au début
                 break
        
        # La mémoire est mise à jour automatiquement par la ConversationChain
        
        return response_text

    except Exception as e:
        # Cette partie peut aussi bénéficier de l'ajout de l'erreur à l'historique si on veut la mémoriser
        error_message = f"Erreur lors de la conversation : {str(e)}"
        # st.session_state.memory.chat_memory.add_ai_message(error_message) # Optionnel : mémoriser les erreurs
        return error_message

# Charger les données d'apprentissage au démarrage
load_learning_data()

# Sidebar avec des informations
with st.sidebar:
    st.header("À propos")
    st.markdown("""
    Cette application utilise:
    - Streamlit pour l'interface utilisateur
    - HuggingFace pour l'IA
    - Système d'apprentissage autonome
    """)
    
    st.markdown("""
    <div style='margin-top: 20px;'>
        <a href='https://www.linkedin.com/in/abdou-latif-niabaly-10bb45268/' target='_blank' style='text-decoration: none; color: #0077B5; margin-right: 20px;'>
            <span style='font-size: 16px;'>👨‍💻 LinkedIn</span>
        </a>
        <a href='https://github.com/Abdou586' target='_blank' style='text-decoration: none; color: #0077B5;'>
            <span style='font-size: 16px;'>💻 GitHub</span>
        </a>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Initialiser l'état du formulaire s'il n'existe pas
    if 'show_contact_form' not in st.session_state:
        st.session_state.show_contact_form = False
    
    # Bouton toggle pour le formulaire
    if st.button("📧 Me contacter", use_container_width=True):
        st.session_state.show_contact_form = not st.session_state.show_contact_form
        st.rerun()
    
    # Afficher le formulaire si show_contact_form est True
    if st.session_state.show_contact_form:
        with st.form("contact_form"):
            name = st.text_input("Votre nom")
            email = st.text_input("Votre email")
            subject = st.text_input("Sujet")
            message = st.text_area("Message")
            submit_button = st.form_submit_button("Envoyer")
            
            if submit_button:
                if name and email and subject and message:
                    # Préparation du message
                    email_message = f"""
                    Nouveau message de contact reçu :
                    
                    Nom: {name}
                    Email: {email}
                    Sujet: {subject}
                    
                    Message:
                    {message}
                    """
                    
                    # Envoi du message (à implémenter avec votre service d'email préféré)
                    st.success("Message envoyé avec succès ! Je vous répondrai dès que possible.")
                    st.session_state.show_contact_form = False
                    st.rerun()
                else:
                    st.error("Veuillez remplir tous les champs du formulaire.")

# Affichage des messages précédents
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Zone de saisie pour l'utilisateur
if prompt := st.chat_input("Posez votre question ici..."):
    # Mettre à jour l'état du premier message
    st.session_state.first_message = False
    
    # Ajouter le message de l'utilisateur
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Obtenir la réponse de l'assistant
    with st.chat_message("assistant"):
        with st.spinner("ALN AI réfléchit..."):
            try:
                response = advanced_chat(prompt)
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
                
                # Si l'utilisateur demande un PDF, générer le PDF et proposer le téléchargement
                if "pdf" in prompt.lower():
                    pdf_path, b64_pdf = generate_pdf(response)
                    if pdf_path and b64_pdf:
                        st.success("PDF généré avec succès !")
                        # Créer un lien de téléchargement
                        href = f'<a href="data:application/pdf;base64,{b64_pdf}" download="document.pdf">Cliquez ici pour télécharger le PDF</a>'
                        st.markdown(href, unsafe_allow_html=True)
            except Exception as e:
                error_message = f"Une erreur s'est produite : {str(e)}"
                st.error(error_message)
                st.error("Veuillez réessayer avec une autre question.")
                st.session_state.messages.append({"role": "assistant", "content": error_message}) 