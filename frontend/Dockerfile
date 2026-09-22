# Frontend do Radar Leilão — React + Vite (build estático servido pelo preview do Vite)
FROM node:22-slim

WORKDIR /app

# URL da API embutida no build (Vite injeta VITE_* em tempo de build)
ARG VITE_API_URL=http://localhost:8000
ENV VITE_API_URL=${VITE_API_URL}

# Instala dependências primeiro (cache de camada)
COPY frontend/package.json frontend/package-lock.json* /app/
RUN npm install

# Código do frontend e build de produção
COPY frontend /app
RUN npm run build

EXPOSE 5173

# Serve o build; --host expõe fora do container; porta 5173 para bater com a doc
CMD ["npx", "vite", "preview", "--host", "0.0.0.0", "--port", "5173"]
