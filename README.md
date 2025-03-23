# URL Shortener

This project is a simple URL shortener built with Flask and PostgreSQL. It provides the functionality to shorten URLs, track access counts, manage custom aliases, set expiration dates, and rate-limit requests to avoid abuse.

## Approach

The application is designed to provide a lightweight and efficient URL shortening service. It leverages Flask to build a REST API for URL shortening and PostgreSQL as the backend database to store URLs and their corresponding metadata.

The following are the key aspects of the approach:

1. **Flask API**:
   The application exposes a REST API with the following endpoints:
   - `POST /shorten`: Accepts a URL and optional custom alias, returns a shortened URL.
   - `GET /<short_code>`: Redirects to the original URL corresponding to the provided shortened code.
   - `GET /stats/<short_code>`: Returns statistics such as access count and expiration date for the shortened URL.
   - `GET /mappings`: Lists all shortened URLs with their statistics.

2. **Database**:
   The URLs are stored in a PostgreSQL database with the following table structure:
   - `long_url`: Stores the original URL.
   - `short_code`: Stores the unique shortened code (6 characters).
   - `custom_alias`: A boolean to indicate whether the shortened URL has a custom alias.
   - `access_count`: Tracks the number of times the shortened URL has been accessed.
   - `expires_at`: Defines the expiration date of the shortened URL, if applicable.

3. **Rate Limiting**:
   To prevent abuse, the application implements simple rate limiting. Each user (identified by their IP address) can make a maximum of 10 requests within a 60-second window. If the limit is exceeded, the user will receive a 429 error.

4. **URL Validation**:
   The application uses the `validators` library to ensure that the provided URL is in a valid format before processing.

5. **Custom Alias Handling**:
   Users can provide a custom alias for their shortened URL. The system checks if the alias is already in use before accepting it. If no alias is provided, a unique 6-character code is generated using the MD5 hash of the original URL.

6. **Expiration Logic**:
   Users can specify an expiration time for the shortened URL. If the expiration date is set and the URL has passed its expiration date, the system will return a 410 Gone error when attempting to access the URL.

7. **Database Connection Pooling**:
   The application uses a PostgreSQL connection pool to efficiently manage database connections, ensuring optimal performance under high load.

## Steps to Run the Project Locally

### Prerequisites:
- Python 3.8+
- PostgreSQL installed and running
- Install required Python libraries:
  ```bash
  pip install -r requirements.txt
  ```

### Set Up PostgreSQL:
1. Create a PostgreSQL database and user:
   ```bash
   sudo -u postgres psql
   CREATE DATABASE url_shortener;
   CREATE USER postgres WITH PASSWORD '1234';
   ALTER ROLE postgres SET client_encoding TO 'utf8';
   ALTER ROLE postgres SET default_transaction_isolation TO 'read committed';
   ALTER ROLE postgres SET timezone TO 'UTC';
   GRANT ALL PRIVILEGES ON DATABASE url_shortener TO postgres;
   \q
   ```

2. Initialize the database by running the following:
   ```bash
   python app.py
   ```

### Run the Flask Application:
```bash
python app.py
```

The application will be available at `http://127.0.0.1:5000/`.

## Example API Requests & Responses

### 1. Shorten a URL
**Request:**
```bash
POST /shorten
Content-Type: application/json

{
  "url": "https://example.com",
  "alias": "exmpl",
  "expires_in_days": 7
}
```

**Response:**
```json
{
  "original_url": "https://example.com",
  "short_url": "http://127.0.0.1:5000/exmpl",
  "short_code": "exmpl",
  "expires_at": "2025-03-31T00:00:00"
}
```

### 2. Redirect to Original URL
**Request:**
```bash
GET /exmpl
```

**Response:**
Redirects to `https://example.com`.

### 3. Get URL Stats
**Request:**
```bash
GET /stats/exmpl
```

**Response:**
```json
{
  "original_url": "https://example.com",
  "short_code": "exmpl",
  "access_count": 5,
  "expires_at": "2025-03-31T00:00:00"
}
```

### 4. View All Mappings
**Request:**
```bash
GET /mappings
```

**Response:**
```json
[
  {
    "long_url": "https://example.com",
    "short_code": "exmpl",
    "access_count": 5,
    "expires_at": "2025-03-31T00:00:00"
  }
]
```



