FROM node:20

WORKDIR /app

# העתקת קבצי dependencies תחילה (ל-cache טוב יותר)
COPY package.json package-lock.json ./

# התקנת dependencies
RUN npm ci --only=production=false

# העתקת שאר הקבצים
COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev"]
