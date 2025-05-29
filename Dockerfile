# Utilise une image Ubuntu récente
FROM ubuntu:22.04

# Installe les dépendances (curl pour installer Ollama)
RUN apt-get update && apt-get install -y curl

# Installe Ollama
RUN curl -fsSL https://ollama.com/install.sh | sh

# Expose le port de l'API Ollama (11434 par défaut)
EXPOSE 11434

# Lance Ollama au démarrage
CMD ["ollama", "serve"]