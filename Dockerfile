# This is the "recipe" the host uses to build and run your server.
# You do not need to change anything here for a basic FastMCP project.

# 1. Start from a small, official Python image.
FROM python:3.12-slim

# 2. Work inside a folder called /app on the host.
WORKDIR /app

# 3. Copy the dependency list in first and install it.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copy the rest of your code in.
COPY . .

# 5. Open the network port so the server can be reached.
EXPOSE 8000

# 6. Start the server.
CMD ["python", "main.py"]
