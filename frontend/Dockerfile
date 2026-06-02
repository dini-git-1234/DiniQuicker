# שלב 1: שלב הבנייה (Build Stage)
FROM node:20-alpine AS builder

WORKDIR /app

COPY package*.json ./

# התקנת כל ה-dependencies
RUN npm ci

COPY . .

# יצירת תיקיית ה-dist הסטטית (עבור Vite)
RUN npm run build

# ש# שלב 1: בניית קבצי הראקט לתוך תיקיית dist קלה
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# שלב 2: הרמת שרת Nginx להגשת הקבצים
FROM nginx:alpine

# העתקת קונפיגורציית ה-Nginx שיצרת עכשיו אל תוך השרת בענן
COPY nginx.conf /etc/nginx/conf.d/default.conf

# העתקת הקבצים הסטטיים של הראקט
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]לב 2: שלב ההרצה (Production Stage) - שימוש ב-Nginx
FROM nginx:alpine

# תוקן: העתקת קבצי ה-dist (ולא build) לתיקייה של Nginx
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]