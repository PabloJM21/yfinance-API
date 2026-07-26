# yfinance API

A FastAPI backend exposing stock market data through the `yfinance` library. The service includes Redis-backed response caching, request rate limiting, request latency instrumentation, Docker-based deployment, and GitHub Actions workflows for automated testing and deployment.

The repository is organized into independent modules for application logic, middleware, testing, diagnostics, and deployment, allowing these components to evolve independently.

---

## Features

- FastAPI REST API
- Company metadata endpoint
- Market quote endpoint
- Historical OHLCV endpoint
- Redis-backed response caching
- Request rate limiting
- Per-request latency instrumentation
- Docker and Docker Compose support
- Automated CI testing
- Prototype deployment workflow for AWS ECR/ECS

---


---

# Project Structure

```text
.
├── app/
│   ├── endpoints/
│   │   └── stocks.py          # API endpoint implementations
│   ├── config.py              # Application configuration
│   ├── main.py                # FastAPI application entry point
│   └── middleware.py          # Request middleware
│
├── tests/
│   └── test_stability.py      # API stability tests
│
├── plot_scripts/
│   └── plot_traffic.py        # Diagnostic plot generation
│
├── .github/workflows/
│   ├── test.yml               # Continuous Integration workflow
│   └── deploy.yml             # Prototype deployment workflow
│
├── Dockerfile
├── docker-compose.yml
├── docker-compose-nginx.yml
├── nginx.conf
└── requirements.txt
```

---

# Architecture

## Application Layer

The FastAPI application is contained in the `app/` package.

### `app/main.py`

`main.py` serves as the application entry point.

Its responsibilities are:

- creating the FastAPI application instance,
- registering the middleware stack,
- loading and registering the API routers,
- configuring the request processing pipeline.

The application logic itself remains isolated from cross-cutting concerns such as caching or rate limiting, which are implemented by the middleware layer.

---

### `app/endpoints/`

The `endpoints` package contains the implementation of the REST API.

Currently, `stocks.py` exposes three endpoints:

- `/company`
- `/quote`
- `/stats`

Each endpoint retrieves market data through the `yfinance` library and converts it into a structured JSON response before returning it to the client.

---

### `app/config.py`

Application configuration is centralized in `config.py`.

The configuration module contains parameters controlling application-wide behavior, including:

- Redis connection settings
- cache enable/disable behavior
- cache TTL
- request rate limits
- logging configuration
- yfinance-specific configuration
- environment-dependent settings

Centralizing these parameters allows runtime behavior to be modified without changing endpoint implementations.

---

### `app/middleware.py`

The middleware implements functionality executed before and after every request.

Current responsibilities include:

- response caching using Redis,
- request rate limiting,
- request latency measurement,
- attachment of latency information to responses,
- request/response processing.

Because these concerns are implemented independently of the endpoint handlers, new functionality can be introduced without modifying the API implementation itself.

The current middleware structure is intended to support future extensions such as:

- API key authentication,
- structured request logging,
- Prometheus metrics export,
- OpenTelemetry instrumentation,
- integration with monitoring platforms such as Grafana.

---


# API Endpoints

All endpoints are exposed under the `/api` prefix.

## `GET /api/company`

Returns company metadata for a stock ticker.

The endpoint queries the `Ticker.info` object provided by `yfinance` and extracts commonly used company attributes.

### Query Parameters

| Parameter | Description |
|-----------|-------------|
| `ticker` | Stock ticker symbol |

### Response

```json
{
    "ticker": "AAPL",
    "name": "...",
    "sector": "...",
    "industry": "...",
    "exchange": "...",
    "country": "...",
    "website": "...",
    "employees": 164000,
    "description": "..."
}
```

Returned information includes

- company name
- business sector
- industry
- exchange
- country
- company website
- employee count
- business summary

---

## `GET /api/quote`

Returns the latest market snapshot for a ticker without downloading historical market data.

The endpoint uses the `Ticker.fast_info` interface from `yfinance`, making it suitable for low-latency requests that only require current market information.

### Query Parameters

| Parameter | Description |
|-----------|-------------|
| `ticker` | Stock ticker symbol |

### Response

```json
{
    "ticker": "AAPL",
    "price": 215.42,
    "previousClose": 214.17,
    "change": 1.25,
    "changePercent": 0.58,
    "dayHigh": 216.10,
    "dayLow": 213.95,
    "volume": 43251871,
    "marketCap": 3200000000000,
    "currency": "USD"
}
```

The endpoint returns

- latest traded price
- previous close
- absolute price change
- percentage price change
- daily high
- daily low
- latest traded volume
- market capitalization
- trading currency

---

## `GET /api/stats`

Returns historical OHLCV market data over a specified date range.

Historical data is retrieved through `Ticker.history()` and converted into a JSON representation where each trading day contains its corresponding market statistics.

### Query Parameters

| Parameter | Description |
|-----------|-------------|
| `ticker` | Stock ticker symbol |
| `start` | Start date |
| `end` | End date |

### Response

```json
{
    "ticker": "AAPL",
    "start": "2024-01-01",
    "end": "2024-01-31",
    "results": [
        {
            "date": "2024-01-02",
            "open": ...,
            "high": ...,
            "low": ...,
            "close": ...,
            "volume": ...,
            "average": ...
        }
    ]
}
```

For each trading day, the endpoint returns

- date
- opening price
- daily high
- daily low
- closing price
- traded volume
- arithmetic average of the OHLC values

The returned data structure is intended to provide a compact representation suitable for downstream visualization or statistical analysis without requiring additional processing by the client.



# Testing

The automated test suite is located in the `tests/` directory.

Currently, the repository contains a stability test targeting the `/stats` endpoint:

```
tests/test_stability.py
```

The `/stats` endpoint was selected because it exercises the largest data retrieval path in the application, requiring historical market data to be downloaded, transformed into JSON, and returned to the client.

The current stability test consists of three stages.

## Large historical request

The test first executes a request covering approximately four years of historical data:

```
Ticker : AAPL
Start  : 2020-01-01
End    : 2024-01-01
```

This evaluates the endpoint under a comparatively large response payload and records the corresponding request latency.

---

## Concurrent requests

The test then executes ten concurrent requests against a smaller historical dataset:

```
Ticker : AAPL
Start  : 2024-05-01
End    : 2024-05-10
```

Each request is executed in a separate Python thread.

The concurrent execution verifies that:

- multiple requests can be processed simultaneously,
- Redis-backed caching behaves correctly under concurrent access,
- request latency remains bounded during parallel execution,
- no unexpected failures occur while multiple clients access the same endpoint.

---

## Diagnostic data collection

Latency information collected during every request is stored throughout the test execution.

After all requests complete, the collected metrics are passed to the plotting utilities in `plot_scripts/` to generate a diagnostic visualization of request latency.

Although the current implementation focuses on the `/stats` endpoint, the testing framework can be extended to include additional endpoints, larger workloads, or more complex request patterns.

---

# Diagnostic Plot Scripts

The `plot_scripts/` directory contains helper scripts used by the automated tests.

Currently, the repository provides

```
plot_scripts/plot_traffic.py
```

which generates a traffic and latency visualization from the metrics collected during stability testing.

The resulting plot is uploaded as a GitHub Actions artifact, allowing request timing to be inspected after every CI run.

Separating visualization from the test implementation allows additional diagnostic plots to be introduced without modifying the testing logic.

---

# Continuous Integration

Continuous Integration workflows are located in

```
.github/workflows/
```

## `test.yml`

The testing workflow is executed whenever a pull request targets the `main` branch.

The workflow is divided into two independent jobs.

### Build

The build job performs the following steps:

1. checks out the repository,
2. builds the backend Docker image using `docker compose build`,
3. starts the Docker Compose stack.

Building the image separately ensures that the application can be successfully containerized before any tests are executed.

---

### Test

The test job performs the following steps:

1. checks out the repository,
2. starts the Docker Compose stack,
3. executes `tests/test_stability.py` inside the dedicated test container,
4. generates the latency visualization,
5. uploads the generated traffic plot as a GitHub Actions artifact,
6. tears down the Docker Compose stack.

The Docker Compose configuration starts three services:

- the FastAPI backend,
- a Redis container,
- a dedicated test container.

The test container executes

```bash
pytest tests/test_stability.py
```

against the running backend.

Since the workflow builds the application locally and executes all tests within the GitHub Actions runner, no external infrastructure is required.

The workflow does not reference GitHub Secrets and can therefore safely execute for pull requests submitted by contributors without write access to the repository.

---

# Continuous Deployment (Prototype)

Deployment is implemented in

```
.github/workflows/deploy.yml
```

and is triggered whenever changes are pushed to the `main` branch after a pull request has been merged.

The deployment pipeline currently consists of three jobs.

## Build

The build stage

1. checks out the repository,
2. authenticates to AWS using GitHub's OIDC integration,
3. logs into Amazon ECR,
4. builds the backend Docker image,
5. tags the image using the current Git commit SHA.

The generated image tag is exported for the subsequent workflow stages.

---

## Push

The push stage authenticates to Amazon ECR and uploads the tagged backend image to the configured Elastic Container Registry repository.

---

## Deploy

The deployment stage updates the ECS service using the new container image.

The ECS task definition references:

- the backend image stored in Amazon ECR,
- the official Redis image from Docker Hub.

Updating the ECS task definition causes the service to deploy the newly built backend while preserving the remainder of the deployment configuration.

The deployment workflow currently serves as a prototype and provides the basis for a future production deployment pipeline.

---

# Containerization

## Dockerfile

The backend image is defined in the project's `Dockerfile`.

The image:

- uses the official Python 3.13 base image,
- installs the project dependencies,
- copies the application source,
- creates a dedicated non-root application user,
- exposes port `8080`,
- starts the FastAPI application using Uvicorn.

Running the application as a non-root user follows standard container security practices.

---

## Docker Compose

The local development environment is defined in `docker-compose.yml`.

The Compose stack consists of three services.

### Backend

Builds the application image from the repository source and exposes the API on port `8080`.

The backend connects to Redis using environment variables provided through Docker Compose.

### Redis

Runs the official Redis image.

Redis is used by the middleware for:

- response caching,
- request rate limiting.

### Test

Builds the same application image but executes

```bash
pytest tests/test_stability.py
```

instead of launching the API server.

This service is used both during local development and by the GitHub Actions testing workflow to execute the stability tests in an identical containerized environment.

---

# Local Development

## Prerequisites

- Docker
- Docker Compose

or

- Python 3.13+

---

## Run with Docker

```bash
docker compose up --build
```

This starts:

- the FastAPI backend,
- the Redis service.

The API is then available at

```
http://localhost:8080
```

---

## Run without Docker

Install the dependencies

```bash
pip install -r requirements.txt
```

Start the application

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8080
```

---

# Running Tests

To execute the stability tests locally:

```bash
docker compose run --rm test
```

This uses the same containerized environment as the GitHub Actions CI workflow, ensuring consistent execution between local development and automated testing.

---

# Future Extensions

The current project structure separates endpoint implementations, middleware, testing, diagnostics, and deployment into independent modules, making it straightforward to extend individual components.

Potential future additions include:

- additional market data endpoints,
- endpoint-specific integration and stability tests,
- API key authentication,
- structured logging,
- Prometheus metrics export,
- OpenTelemetry instrumentation,
- additional diagnostic visualizations,
- extended load and stress testing,
- automated ECS infrastructure provisioning.