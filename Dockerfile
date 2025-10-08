# Use official Python image
FROM python:3.11-slim

# Set working directory inside the container
WORKDIR /app

# Copy dependency list
COPY requirements.txt .

#upgrade pip first
RUN pip install --upgrade pip

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the whole project
COPY . .

# Set environment variable to prevent buffering
ENV PYTHONUNBUFFERED=1

# Expose port 8000
EXPOSE 8000

# Run Django development server by default
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
