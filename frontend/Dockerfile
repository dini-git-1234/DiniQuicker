# שלב 1: שלב הבנייה (Build Stage)
FROM node:20-alpine AS builder

WORKDIR /app

COPY package*.json ./

# התקנת הדרישות (Dependencies)
RUN npm ci

COPY . .

# בניית הקבצים הסטטיים של ראקט (יוצר תיקיית dist)
RUN npm run build

# שלב 2: שלב ההרצה (Production Stage) באמצעות Nginx
FROM nginx:alpine

# העתקת קובץ ההגדרות של Nginx שיצרת
COPY nginx.conf /etc/nginx/conf.d/default.conf

# העתקת קבצי האתר הסטטיים מתוך שלב הבנייה אל שרת ה-Nginx
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]