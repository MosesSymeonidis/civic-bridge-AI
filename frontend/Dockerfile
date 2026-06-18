FROM node:24-alpine AS build

WORKDIR /app

ARG VITE_API_BASE_URL=/api/v1
ARG VITE_RAG_API_BASE_URL=/rag-api
ARG VITE_CLASSIFIER_API_BASE_URL=/classifier-api
ARG VITE_SOCIAL_POST_PAGE_URL=http://localhost:3000/how-it-works
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ENV VITE_RAG_API_BASE_URL=$VITE_RAG_API_BASE_URL
ENV VITE_CLASSIFIER_API_BASE_URL=$VITE_CLASSIFIER_API_BASE_URL
ENV VITE_SOCIAL_POST_PAGE_URL=$VITE_SOCIAL_POST_PAGE_URL

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM nginx:alpine AS runtime

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
