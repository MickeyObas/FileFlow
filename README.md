# FileFlow

**FileFlow** is an asynchronous document processing platform designed to explore how production-style backend systems handle file uploads, background processing, job tracking, and cloud infrastructure.

A user uploads a document, FileFlow stores it, creates a processing job, and handles that work asynchronously. The system keeps track of the file and job lifecycle so users can see whether processing is pending, in progress, completed, or failed.

## What I'm Building

The initial workflow is:

```text
Upload document
      ↓
Store file
      ↓
Create processing job
      ↓
Queue background work
      ↓
Process document
      ↓
Persist result + status
```

The system will eventually use cloud storage and managed AWS services for file storage, job queuing, observability, and deployment.

## Engineering Focus

FileFlow is primarily a learning and engineering project focused on:

* Backend architecture and API design
* Asynchronous processing and job queues
* Database design and data modeling
* Object storage and large file handling
* Docker and containerized development
* AWS infrastructure
* Reliability, error handling, and observability
* Designing systems that can scale beyond a single process

## Tech Stack

### Backend

* Python
* FastAPI
* PostgreSQL
* SQLAlchemy
* Alembic

### Frontend

* Next.js

### Infrastructure

* Docker
* AWS

## Project Structure

```text
FileFlow/
├── backend/     # FastAPI application
├── frontend/    # Next.js application
└── compose.yml  # Local development infrastructure
```

## Status

🚧 **In development**

The project is being built incrementally, starting with the backend and core data model before introducing asynchronous processing and AWS infrastructure.
