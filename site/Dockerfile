FROM node:22-slim
WORKDIR /site
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
EXPOSE 4321
CMD ["npm", "run", "dev"]
