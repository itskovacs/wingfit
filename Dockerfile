# Node builder
FROM node:22 AS build
WORKDIR /app
COPY src/package*.json ./
RUN npm install
COPY src .
RUN npm run build

# Server
FROM python:3.12-slim
LABEL maintainer="github.com/itskovacs"
LABEL description="Minimalist fitness app to plan your workouts and track your personal records"
WORKDIR /app
COPY backend .
RUN pip install --no-cache-dir -r wingfit/requirements.txt
COPY --from=build /app/dist/wingfit/browser ./frontend
EXPOSE 8000
CMD ["fastapi", "run", "/app/wingfit/main.py", "--host", "0.0.0.0", "--port", "8000"]