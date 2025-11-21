# Use the official Node.js image as the base image for building the React app
FROM node:20 AS build

# Set the working directory inside the container to /app
WORKDIR /app

COPY . .

# Install the application dependencies defined in package.json
RUN npm install

# Build the React application for production
RUN npm run build

# Use the official Nginx image as the base image for serving the built app
FROM nginx:alpine

# Change the source directory from /app/build to /app/dist
COPY --from=build /app/dist /usr/share/nginx/html

# Expose port 80 to allow external access to the application
EXPOSE 80

# Start Nginx in the foreground
CMD ["nginx", "-g", "daemon off;"]